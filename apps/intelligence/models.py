"""
Django models for the intelligence app.

This module defines models for storing demand forecasts and model metadata.
"""

from django.db import models
from apps.core.models import Place
from apps.inventory.models import Item


class ForecastModel(models.Model):
    """
    Stores metadata about trained forecasting models.
    
    Each trained Prophet model is tracked with its performance metrics
    and training parameters for reproducibility and monitoring.
    """
    place = models.ForeignKey(
        Place, 
        on_delete=models.CASCADE, 
        related_name='forecast_models',
        help_text="The place/location this model was trained for"
    )
    item = models.ForeignKey(
        Item, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='forecast_models',
        help_text="Optional - specific item this model forecasts. Null means place-level model."
    )
    
    # Model performance metrics
    mape = models.FloatField(
        null=True, 
        blank=True,
        help_text="Mean Absolute Percentage Error (lower is better)"
    )
    rmse = models.FloatField(
        null=True, 
        blank=True,
        help_text="Root Mean Squared Error"
    )
    mae = models.FloatField(
        null=True, 
        blank=True,
        help_text="Mean Absolute Error"
    )
    
    # Training metadata
    training_date = models.DateTimeField(auto_now_add=True)
    training_start_date = models.DateField(
        help_text="Start of training data range"
    )
    training_end_date = models.DateField(
        help_text="End of training data range"
    )
    data_points_used = models.IntegerField(
        default=0,
        help_text="Number of data points used in training"
    )
    
    # Model configuration (stored as JSON)
    model_params = models.JSONField(
        default=dict,
        blank=True,
        help_text="Prophet model parameters used during training"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this model is currently in use for predictions"
    )
    
    class Meta:
        ordering = ['-training_date']
        verbose_name = "Forecast Model"
        verbose_name_plural = "Forecast Models"
    
    def __str__(self):
        if self.item:
            return f"Model for {self.item.title} at {self.place.title} ({self.training_date.date()})"
        return f"Model for {self.place.title} ({self.training_date.date()})"


class DemandForecast(models.Model):
    """
    Stores individual demand predictions.
    
    Each record represents a prediction for a specific item/place
    on a specific date, with confidence intervals.
    """
    forecast_model = models.ForeignKey(
        ForecastModel,
        on_delete=models.CASCADE,
        related_name='forecasts',
        help_text="The model that generated this forecast"
    )
    place = models.ForeignKey(
        Place, 
        on_delete=models.CASCADE, 
        related_name='demand_forecasts'
    )
    item = models.ForeignKey(
        Item, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='demand_forecasts'
    )
    
    # Forecast details
    forecast_date = models.DateField(
        help_text="The date being forecasted"
    )
    predicted_quantity = models.FloatField(
        help_text="Predicted demand quantity"
    )
    
    # Confidence intervals
    lower_bound_80 = models.FloatField(
        null=True,
        blank=True,
        help_text="Lower bound of 80% confidence interval"
    )
    upper_bound_80 = models.FloatField(
        null=True,
        blank=True,
        help_text="Upper bound of 80% confidence interval"
    )
    lower_bound_95 = models.FloatField(
        null=True,
        blank=True,
        help_text="Lower bound of 95% confidence interval"
    )
    upper_bound_95 = models.FloatField(
        null=True,
        blank=True,
        help_text="Upper bound of 95% confidence interval"
    )
    
    # Trend components (from Prophet decomposition)
    trend = models.FloatField(
        null=True,
        blank=True,
        help_text="Trend component from Prophet"
    )
    weekly_seasonality = models.FloatField(
        null=True,
        blank=True,
        help_text="Weekly seasonality component"
    )
    yearly_seasonality = models.FloatField(
        null=True,
        blank=True,
        help_text="Yearly seasonality component"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['forecast_date']
        unique_together = ['forecast_model', 'place', 'item', 'forecast_date']
        verbose_name = "Demand Forecast"
        verbose_name_plural = "Demand Forecasts"
    
    def __str__(self):
        item_name = self.item.title if self.item else "All Items"
        return f"Forecast for {item_name} on {self.forecast_date}: {self.predicted_quantity:.1f}"
    
    @property
    def confidence_interval_80(self):
        """Returns the 80% confidence interval as a tuple."""
        return (self.lower_bound_80, self.upper_bound_80)
    
    @property  
    def confidence_interval_95(self):
        """Returns the 95% confidence interval as a tuple."""
        return (self.lower_bound_95, self.upper_bound_95)
