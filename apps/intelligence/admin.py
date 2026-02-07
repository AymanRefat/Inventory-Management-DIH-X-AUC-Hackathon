"""
Django Admin configuration for the intelligence app.
"""

from django.contrib import admin
from apps.intelligence.models import ForecastModel, DemandForecast


@admin.register(ForecastModel)
class ForecastModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'place', 'item', 'mape', 'rmse', 'training_date', 'is_active']
    list_filter = ['is_active', 'place', 'training_date']
    search_fields = ['place__title', 'item__title']
    readonly_fields = ['training_date']
    ordering = ['-training_date']
    
    fieldsets = (
        ('Location', {
            'fields': ('place', 'item')
        }),
        ('Performance Metrics', {
            'fields': ('mape', 'rmse', 'mae')
        }),
        ('Training Info', {
            'fields': ('training_date', 'training_start_date', 'training_end_date', 
                      'data_points_used', 'model_params')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(DemandForecast)
class DemandForecastAdmin(admin.ModelAdmin):
    list_display = ['id', 'place', 'item', 'forecast_date', 'predicted_quantity', 'created_at']
    list_filter = ['place', 'forecast_date']
    search_fields = ['place__title', 'item__title']
    ordering = ['-forecast_date']
    date_hierarchy = 'forecast_date'
    
    readonly_fields = ['created_at']
