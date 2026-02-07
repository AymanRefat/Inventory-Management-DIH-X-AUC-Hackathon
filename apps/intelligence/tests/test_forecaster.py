"""
Unit tests for the demand forecaster service.

Tests the DemandForecaster class and related functionality.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone

from apps.core.models import Place
from apps.inventory.models import Item, StockCategory
from apps.sales.models import Order, OrderItem
from apps.intelligence.forecaster import DemandForecaster
from apps.intelligence.models import ForecastModel, DemandForecast


class DemandForecasterTestCase(TestCase):
    """Tests for the DemandForecaster class."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests."""
        # Create a place
        cls.place = Place.objects.create(
            title="Test Restaurant",
            description="A test restaurant",
            active=True
        )
        
        # Create a stock category
        cls.category = StockCategory.objects.create(
            place=cls.place,
            title="Food"
        )
        
        # Create an item
        cls.item = Item.objects.create(
            place=cls.place,
            title="Test Burger",
            description="A test burger",
            price=Decimal("9.99"),
            category=cls.category
        )
        
        # Create historical orders (last 30 days)
        cls._create_test_orders(cls.place, cls.item, days=30)
    
    @classmethod
    def _create_test_orders(cls, place, item, days=30):
        """Create test order data."""
        base_date = timezone.now() - timedelta(days=days)
        
        for i in range(days):
            order_date = base_date + timedelta(days=i)
            
            # Create 2-5 orders per day with some variation
            num_orders = 2 + (i % 4)
            
            for j in range(num_orders):
                order = Order.objects.create(
                    place=place,
                    status='Complete',
                    total_amount=Decimal("10.00"),
                    created_at=order_date + timedelta(hours=10 + j)
                )
                
                # Add order items with varying quantities
                quantity = Decimal(str(1 + (i % 3) + (j % 2)))
                OrderItem.objects.create(
                    order=order,
                    item=item,
                    quantity=quantity,
                    price=item.price
                )
    
    def test_forecaster_initialization(self):
        """Test forecaster initializes correctly."""
        forecaster = DemandForecaster(place_id=self.place.id)
        
        self.assertEqual(forecaster.place_id, self.place.id)
        self.assertIsNone(forecaster.item_id)
        self.assertIsNone(forecaster.model)
    
    def test_forecaster_with_item(self):
        """Test forecaster initializes with item_id."""
        forecaster = DemandForecaster(
            place_id=self.place.id, 
            item_id=self.item.id
        )
        
        self.assertEqual(forecaster.item_id, self.item.id)
    
    def test_aggregate_sales_data(self):
        """Test sales data aggregation."""
        forecaster = DemandForecaster(place_id=self.place.id)
        
        df = forecaster.aggregate_sales_data()
        
        # Should have data
        self.assertGreater(len(df), 0)
        
        # Should have required columns
        self.assertIn('ds', df.columns)
        self.assertIn('y', df.columns)
        
        # Values should be positive
        self.assertTrue((df['y'] >= 0).all())
    
    def test_aggregate_sales_data_item_specific(self):
        """Test item-specific sales aggregation."""
        forecaster = DemandForecaster(
            place_id=self.place.id,
            item_id=self.item.id
        )
        
        df = forecaster.aggregate_sales_data()
        
        self.assertGreater(len(df), 0)
    
    def test_aggregate_sales_data_no_data(self):
        """Test aggregation with no orders."""
        # Create a new place with no orders
        empty_place = Place.objects.create(
            title="Empty Place",
            active=True
        )
        
        forecaster = DemandForecaster(place_id=empty_place.id)
        df = forecaster.aggregate_sales_data()
        
        # Should return empty DataFrame with correct columns
        self.assertIn('ds', df.columns)
        self.assertIn('y', df.columns)
    
    def test_add_features(self):
        """Test feature engineering."""
        forecaster = DemandForecaster(place_id=self.place.id)
        df = forecaster.aggregate_sales_data()
        
        df_with_features = forecaster.add_features(df)
        
        # Should have new columns
        self.assertIn('day_of_week', df_with_features.columns)
        self.assertIn('is_weekend', df_with_features.columns)
        self.assertIn('month', df_with_features.columns)
    
    def test_train_fallback(self):
        """Test training with fallback (no Prophet)."""
        forecaster = DemandForecaster(place_id=self.place.id)
        forecaster._prophet_available = False  # Force fallback
        
        result = forecaster.train()
        
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'success_fallback')
        self.assertIn('data_points', result)
    
    def test_predict_fallback(self):
        """Test prediction with fallback."""
        forecaster = DemandForecaster(place_id=self.place.id)
        forecaster._prophet_available = False
        forecaster.train()
        
        predictions = forecaster.predict(days_ahead=7)
        
        # Should have 7 predictions
        self.assertEqual(len(predictions), 7)
        
        # Should have required columns
        self.assertIn('ds', predictions.columns)
        self.assertIn('predicted_quantity', predictions.columns)
        self.assertIn('lower_bound_80', predictions.columns)
        self.assertIn('upper_bound_80', predictions.columns)
    
    def test_save_forecasts(self):
        """Test saving forecasts to database."""
        forecaster = DemandForecaster(place_id=self.place.id)
        forecaster._prophet_available = False
        forecaster.train()
        
        predictions = forecaster.predict(days_ahead=7)
        count = forecaster.save_forecasts(predictions)
        
        # Should save all predictions
        self.assertEqual(count, 7)
        
        # Check database
        self.assertEqual(DemandForecast.objects.count(), 7)
        self.assertEqual(ForecastModel.objects.count(), 1)
        
        # Check forecast model
        model = ForecastModel.objects.first()
        self.assertEqual(model.place, self.place)
        self.assertTrue(model.is_active)


class ForecastModelTestCase(TestCase):
    """Tests for the ForecastModel model."""
    
    def test_create_forecast_model(self):
        """Test creating a forecast model."""
        place = Place.objects.create(title="Test Place", active=True)
        
        model = ForecastModel.objects.create(
            place=place,
            mape=15.5,
            rmse=10.2,
            training_start_date=timezone.now().date() - timedelta(days=90),
            training_end_date=timezone.now().date(),
            data_points_used=90
        )
        
        self.assertIsNotNone(model.id)
        self.assertIsNotNone(model.training_date)
        self.assertTrue(model.is_active)
    
    def test_forecast_model_str(self):
        """Test ForecastModel string representation."""
        place = Place.objects.create(title="Test Restaurant", active=True)
        
        model = ForecastModel.objects.create(
            place=place,
            training_start_date=timezone.now().date(),
            training_end_date=timezone.now().date()
        )
        
        self.assertIn("Test Restaurant", str(model))


class DemandForecastTestCase(TestCase):
    """Tests for the DemandForecast model."""
    
    def test_create_demand_forecast(self):
        """Test creating a demand forecast."""
        place = Place.objects.create(title="Test Place", active=True)
        
        model = ForecastModel.objects.create(
            place=place,
            training_start_date=timezone.now().date(),
            training_end_date=timezone.now().date()
        )
        
        forecast = DemandForecast.objects.create(
            forecast_model=model,
            place=place,
            forecast_date=timezone.now().date() + timedelta(days=1),
            predicted_quantity=100.5,
            lower_bound_80=80.0,
            upper_bound_80=120.0
        )
        
        self.assertIsNotNone(forecast.id)
        self.assertEqual(forecast.predicted_quantity, 100.5)
    
    def test_confidence_interval_properties(self):
        """Test confidence interval properties."""
        place = Place.objects.create(title="Test Place", active=True)
        
        model = ForecastModel.objects.create(
            place=place,
            training_start_date=timezone.now().date(),
            training_end_date=timezone.now().date()
        )
        
        forecast = DemandForecast.objects.create(
            forecast_model=model,
            place=place,
            forecast_date=timezone.now().date(),
            predicted_quantity=100.0,
            lower_bound_80=80.0,
            upper_bound_80=120.0,
            lower_bound_95=70.0,
            upper_bound_95=130.0
        )
        
        self.assertEqual(forecast.confidence_interval_80, (80.0, 120.0))
        self.assertEqual(forecast.confidence_interval_95, (70.0, 130.0))
