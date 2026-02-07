"""
Demand Forecasting Service using Facebook Prophet.

This module provides the DemandForecaster class for predicting demand
at item-level or place-level using historical order data from the database.

Usage:
    from apps.intelligence.forecaster import DemandForecaster
    
    # Initialize forecaster for a specific place and item
    forecaster = DemandForecaster(place_id=1, item_id=101)
    
    # Train the model on historical data
    train_result = forecaster.train()
    
    # Generate predictions for the next 7 days
    if train_result['status'] == 'success':
        forecasts = forecaster.predict(days_ahead=7)
        forecaster.save_forecasts(forecasts)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

import numpy as np
import pandas as pd
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone

logger = logging.getLogger(__name__)


class DemandForecaster:
    """
    Prophet-based demand forecaster for inventory prediction.
    
    This class handles:
    1. Aggregating historical sales data from the database
    2. Training a Prophet time-series model
    3. Generating future demand predictions with confidence intervals
    4. Calculating accuracy metrics (MAPE, RMSE)
    
    Attributes:
        place_id (int): ID of the place/location to forecast for
        item_id (int, optional): ID for item-specific forecasting. If None, forecasts total place demand.
        model: The trained Prophet model instance
        training_data (pd.DataFrame): DataFrame used for training (ds, y)
    """
    
    def __init__(self, place_id: int, item_id: Optional[int] = None, use_csv: bool = False):
        """
        Initialize the forecaster.
        
        Args:
            place_id: The place/location ID to forecast for
            item_id: Optional item ID for item-specific forecasting
            use_csv: Deprecated. Kept for compatibility but ignored.
        """
        self.place_id = place_id
        self.item_id = item_id
        # use_csv is deprecated as we now strictly use the database
        self.model = None
        self.training_data = None
        self.metrics = {}
        self._prophet_available = self._check_prophet_available()
    
    def _check_prophet_available(self) -> bool:
        """Check if Prophet library is installed."""
        try:
            from prophet import Prophet
            return True
        except ImportError:
            logger.warning(
                "Prophet not installed. Using fallback average method. "
                "To install: pip install prophet"
            )
            return False
    
    def aggregate_sales_data(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Aggregate historical sales data from database orders.
        
        Args:
            start_date: Start of data range (auto-detected if None)
            end_date: End of data range (defaults to max date in data)
            
        Returns:
            DataFrame with columns 'ds' (date) and 'y' (quantity)
        """
        df = self._aggregate_from_db(start_date, end_date)
        self.training_data = df
        return df

    # CSV aggregation methods removed as we now use DB exclusively
    
    def _aggregate_from_db(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Aggregate sales data from database."""
        from apps.sales.models import OrderItem
        from django.db.models import Min, Max
        
        # Build base queryset
        base_queryset = OrderItem.objects.filter(
            order__place_id=self.place_id,
            order__status__icontains='Closed'
        )
        if self.item_id:
            base_queryset = base_queryset.filter(item_id=self.item_id)
        
        # Auto-detect date range from actual data if not specified
        if start_date is None or end_date is None:
            date_range = base_queryset.aggregate(
                min_date=Min('order__created_at'),
                max_date=Max('order__created_at')
            )
            
            if date_range['max_date'] is None:
                logger.warning(f"No sales data found in DB for place_id={self.place_id}")
                return pd.DataFrame(columns=['ds', 'y'])
            
            # Use actual data date range (last 365 days of data or all data if less)
            if end_date is None:
                end_date = date_range['max_date']
            if start_date is None:
                # Use last 365 days of data or all available
                start_date = max(
                    date_range['min_date'],
                    end_date - timedelta(days=365)
                )
        
        # Now filter by date range
        queryset = base_queryset.filter(
            order__created_at__gte=start_date,
            order__created_at__lte=end_date
        )
        # Aggregate by date
        daily_sales = queryset.annotate(
            date=TruncDate('order__created_at')
        ).values('date').annotate(
            total_quantity=Sum('quantity'),
            order_count=Count('order', distinct=True)
        ).order_by('date')
        
        # Convert to DataFrame
        data = list(daily_sales)
        if not data:
            logger.warning(f"No sales data found in DB for place_id={self.place_id}")
            return pd.DataFrame(columns=['ds', 'y'])
        
        df = pd.DataFrame(data)
        df = df.rename(columns={'date': 'ds', 'total_quantity': 'y'})
        df['ds'] = pd.to_datetime(df['ds'])
        df['y'] = df['y'].astype(float)
        
        # Fill missing dates with zeros
        df = self._fill_missing_dates(df, start_date, end_date)
        
        logger.info(f"Aggregated {len(df)} days of sales data from DB")
        
        return df
    
    def _fill_missing_dates(
        self, 
        df: pd.DataFrame, 
        start_date: datetime, 
        end_date: datetime
    ) -> pd.DataFrame:
        """Fill missing dates with zero sales."""
        if df.empty:
            return df
        
        # Convert to date objects
        start = start_date.date() if hasattr(start_date, 'date') else start_date
        end = end_date.date() if hasattr(end_date, 'date') else end_date
            
        # Create complete date range
        date_range = pd.date_range(start=start, end=end, freq='D')
        
        # Reindex to fill missing dates
        df = df.set_index('ds')
        df = df.reindex(date_range, fill_value=0)
        df = df.reset_index()
        df = df.rename(columns={'index': 'ds'})
        
        # Ensure y column exists and is numeric
        if 'y' not in df.columns:
            df['y'] = 0
        df['y'] = df['y'].fillna(0).astype(float)
        
        return df
    
    def add_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add temporal features to the data.
        
        Adds features like:
        - Day of week indicators
        - Holiday indicators
        - Month/quarter indicators
        
        Args:
            df: DataFrame with at least 'ds' column
            
        Returns:
            DataFrame with additional feature columns
        """
        df = df.copy()
        
        # Basic temporal features
        df['day_of_week'] = df['ds'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        df['month'] = df['ds'].dt.month
        df['quarter'] = df['ds'].dt.quarter
        df['day_of_month'] = df['ds'].dt.day
        df['week_of_year'] = df['ds'].dt.isocalendar().week
        
        # Lag features (if enough data)
        if len(df) > 7:
            df['lag_7'] = df['y'].shift(7)
            df['rolling_mean_7'] = df['y'].rolling(window=7, min_periods=1).mean()
            df['rolling_std_7'] = df['y'].rolling(window=7, min_periods=1).std()
        
        if len(df) > 30:
            df['lag_30'] = df['y'].shift(30)
            df['rolling_mean_30'] = df['y'].rolling(window=30, min_periods=1).mean()
        
        return df
    
    def train(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **prophet_kwargs
    ) -> Dict[str, Any]:
        """
        Train the Prophet model on historical data.
        
        Args:
            start_date: Start of training data range
            end_date: End of training data range
            **prophet_kwargs: Additional Prophet parameters
            
        Returns:
            Dict with training results and metrics
        """
        if not self._prophet_available:
            return self._train_fallback(start_date, end_date)
        
        from prophet import Prophet
        
        # Get training data
        df = self.aggregate_sales_data(start_date, end_date)
        
        if df.empty or len(df) < 14:
            logger.error(f"Insufficient data for training (need at least 14 days, got {len(df)})")
            return {'error': 'Insufficient data', 'data_points': len(df)}
        
        # Default Prophet configuration
        default_params = {
            'yearly_seasonality': len(df) > 365,
            'weekly_seasonality': True,
            'daily_seasonality': False,
            'changepoint_prior_scale': 0.05,
            'seasonality_prior_scale': 10,
        }
        default_params.update(prophet_kwargs)
        
        # Initialize and train Prophet
        self.model = Prophet(**default_params)
        
        # Fit model
        logger.info(f"Training Prophet model on {len(df)} data points")
        self.model.fit(df[['ds', 'y']])
        
        # Calculate cross-validation metrics
        self.metrics = self._calculate_metrics(df)
        
        return {
            'status': 'success',
            'data_points': len(df),
            'date_range': {
                'start': df['ds'].min().isoformat(),
                'end': df['ds'].max().isoformat()
            },
            'metrics': self.metrics,
            'model_params': default_params
        }
    
    def _train_fallback(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Fallback training when Prophet is not available.
        Uses simple moving average for predictions.
        """
        df = self.aggregate_sales_data(start_date, end_date)
        
        if df.empty:
            return {'error': 'No data available', 'data_points': 0}
        
        # Store simple statistics for fallback prediction
        self.metrics = {
            'mean': float(df['y'].mean()),
            'std': float(df['y'].std()) if len(df) > 1 else 0,
            'weekly_pattern': df.groupby(df['ds'].dt.dayofweek)['y'].mean().to_dict()
        }
        
        logger.info(f"Using fallback (moving average) forecaster with {len(df)} data points")
        
        return {
            'status': 'success_fallback',
            'data_points': len(df),
            'date_range': {
                'start': df['ds'].min().isoformat(),
                'end': df['ds'].max().isoformat()
            },
            'metrics': self.metrics,
            'note': 'Prophet not available, using moving average'
        }
    
    def predict(
        self, 
        days_ahead: int = 7,
        include_history: bool = False
    ) -> pd.DataFrame:
        """
        Generate demand predictions.
        
        Args:
            days_ahead: Number of days to forecast
            include_history: Whether to include historical predictions
            
        Returns:
            DataFrame with predictions and confidence intervals
        """
        if self.model is None and not self.metrics:
            raise ValueError("Model not trained. Call train() first.")
        
        if self._prophet_available and self.model is not None:
            return self._predict_prophet(days_ahead, include_history)
        else:
            return self._predict_fallback(days_ahead)
    
    def _predict_prophet(
        self, 
        days_ahead: int, 
        include_history: bool
    ) -> pd.DataFrame:
        """Generate predictions using Prophet."""
        # Create future dataframe
        future = self.model.make_future_dataframe(
            periods=days_ahead, 
            include_history=include_history
        )
        
        # Generate predictions
        forecast = self.model.predict(future)
        
        # Select relevant columns and rename
        cols_to_select = ['ds', 'yhat', 'yhat_lower', 'yhat_upper', 'trend']
        if 'weekly' in forecast.columns:
            cols_to_select.append('weekly')
        
        result = forecast[cols_to_select].copy()
        
        result = result.rename(columns={
            'yhat': 'predicted_quantity',
            'yhat_lower': 'lower_bound_80',
            'yhat_upper': 'upper_bound_80',
        })
        
        if 'weekly' in result.columns:
            result = result.rename(columns={'weekly': 'weekly_seasonality'})
        else:
            result['weekly_seasonality'] = 0
        
        # Add 95% confidence intervals (wider than default 80%)
        interval_width = result['upper_bound_80'] - result['predicted_quantity']
        result['lower_bound_95'] = result['predicted_quantity'] - (interval_width * 1.5)
        result['upper_bound_95'] = result['predicted_quantity'] + (interval_width * 1.5)
        
        # Ensure non-negative predictions
        for col in ['predicted_quantity', 'lower_bound_80', 'lower_bound_95']:
            result[col] = result[col].clip(lower=0)
        
        return result
    
    def _predict_fallback(self, days_ahead: int) -> pd.DataFrame:
        """Generate predictions using simple moving average."""
        base_date = timezone.now().date()
        dates = [base_date + timedelta(days=i) for i in range(days_ahead)]
        
        predictions = []
        for date in dates:
            day_of_week = date.weekday()
            
            # Use weekly pattern if available
            if 'weekly_pattern' in self.metrics:
                base_pred = self.metrics['weekly_pattern'].get(
                    day_of_week, 
                    self.metrics['mean']
                )
            else:
                base_pred = self.metrics['mean']
            
            std = self.metrics.get('std', base_pred * 0.2)
            
            predictions.append({
                'ds': date,
                'predicted_quantity': base_pred,
                'lower_bound_80': max(0, base_pred - std),
                'upper_bound_80': base_pred + std,
                'lower_bound_95': max(0, base_pred - 1.5 * std),
                'upper_bound_95': base_pred + 1.5 * std,
                'trend': base_pred,
                'weekly_seasonality': 0
            })
        
        return pd.DataFrame(predictions)
    
    def _calculate_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate accuracy metrics on training data.
        
        Uses simple train/test split for quick validation.
        """
        if len(df) < 21:
            return {'note': 'Insufficient data for metrics'}
        
        # Use last 7 days as test set
        train = df.iloc[:-7]
        test = df.iloc[-7:]
        
        # Fit temporary model on train set
        from prophet import Prophet
        temp_model = Prophet(
            yearly_seasonality=False,
            weekly_seasonality=True,
            daily_seasonality=False
        )
        temp_model.fit(train[['ds', 'y']])
        
        # Predict on test dates
        future = temp_model.make_future_dataframe(periods=7, include_history=False)
        forecast = temp_model.predict(future)
        
        # Calculate metrics
        y_true = test['y'].values
        y_pred = forecast['yhat'].values
        
        # MAPE (handling zeros)
        mask = y_true != 0
        if mask.sum() > 0:
            mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
        else:
            mape = None
        
        # RMSE
        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
        
        # MAE
        mae = np.mean(np.abs(y_true - y_pred))
        
        return {
            'mape': round(mape, 2) if mape else None,
            'rmse': round(rmse, 2),
            'mae': round(mae, 2)
        }
    
    def save_forecasts(self, forecasts: pd.DataFrame) -> int:
        """
        Save forecasts to database.
        
        Args:
            forecasts: DataFrame from predict() method
            
        Returns:
            Number of forecasts saved
        """
        from apps.intelligence.models import DemandForecast, ForecastModel
        from apps.core.models import Place
        from apps.inventory.models import Item
        
        # Get or create ForecastModel record
        place = Place.objects.get(pk=self.place_id)
        item = Item.objects.get(pk=self.item_id) if self.item_id else None
        
        training_data = self.training_data
        
        forecast_model = ForecastModel.objects.create(
            place=place,
            item=item,
            mape=self.metrics.get('mape'),
            rmse=self.metrics.get('rmse'),
            mae=self.metrics.get('mae'),
            training_start_date=training_data['ds'].min().date() if training_data is not None and not training_data.empty else timezone.now().date(),
            training_end_date=training_data['ds'].max().date() if training_data is not None and not training_data.empty else timezone.now().date(),
            data_points_used=len(training_data) if training_data is not None else 0,
            model_params={'type': 'prophet' if self._prophet_available else 'fallback'}
        )
        
        # Create forecast records
        forecast_objects = []
        for _, row in forecasts.iterrows():
            forecast_objects.append(DemandForecast(
                forecast_model=forecast_model,
                place=place,
                item=item,
                forecast_date=row['ds'].date() if hasattr(row['ds'], 'date') else row['ds'],
                predicted_quantity=row['predicted_quantity'],
                lower_bound_80=row.get('lower_bound_80'),
                upper_bound_80=row.get('upper_bound_80'),
                lower_bound_95=row.get('lower_bound_95'),
                upper_bound_95=row.get('upper_bound_95'),
                trend=row.get('trend'),
                weekly_seasonality=row.get('weekly_seasonality')
            ))
        
        DemandForecast.objects.bulk_create(forecast_objects)
        logger.info(f"Saved {len(forecast_objects)} forecasts to database")
        
        return len(forecast_objects)





def generate_forecasts_for_place(
    place_id: int, 
    days_ahead: int = 7,
    item_ids: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Convenience function to generate and save forecasts.
    
    Args:
        place_id: Place to forecast for
        days_ahead: Forecast horizon
        item_ids: Optional list of specific items to forecast
        
    Returns:
        Summary of generation results
    """
    results = {'place_id': place_id, 'forecasts': []}
    
    if item_ids:
        # Generate per-item forecasts
        for item_id in item_ids:
            forecaster = DemandForecaster(place_id, item_id, use_csv=False)
            train_result = forecaster.train()
            
            if 'error' not in train_result:
                predictions = forecaster.predict(days_ahead=days_ahead)
                count = forecaster.save_forecasts(predictions)
                results['forecasts'].append({
                    'item_id': item_id,
                    'count': count,
                    'metrics': train_result.get('metrics', {})
                })
            else:
                results['forecasts'].append({
                    'item_id': item_id,
                    'error': train_result.get('error')
                })
    else:
        # Generate place-level forecast
        forecaster = DemandForecaster(place_id, use_csv=False)
        train_result = forecaster.train()
        
        if 'error' not in train_result:
            predictions = forecaster.predict(days_ahead=days_ahead)
            count = forecaster.save_forecasts(predictions)
            results['forecasts'].append({
                'item_id': None,
                'count': count,
                'metrics': train_result.get('metrics', {})
            })
        else:
            results['error'] = train_result.get('error')
    
    return results
