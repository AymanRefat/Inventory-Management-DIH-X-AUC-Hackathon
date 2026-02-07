"""
Django REST Framework serializers for the intelligence app.
"""

from rest_framework import serializers
from apps.intelligence.models import DemandForecast, ForecastModel


class ForecastModelSerializer(serializers.ModelSerializer):
    """Serializer for ForecastModel metadata."""
    
    place_name = serializers.CharField(source='place.title', read_only=True)
    item_name = serializers.CharField(source='item.title', read_only=True, allow_null=True)
    
    class Meta:
        model = ForecastModel
        fields = [
            'id', 'place', 'place_name', 'item', 'item_name',
            'mape', 'rmse', 'mae',
            'training_date', 'training_start_date', 'training_end_date',
            'data_points_used', 'is_active'
        ]


class ForecastMetricsSerializer(serializers.Serializer):
    """Serializer for forecast model metrics."""
    
    mape = serializers.FloatField(allow_null=True)
    rmse = serializers.FloatField(allow_null=True)
    mae = serializers.FloatField(allow_null=True)
    training_date = serializers.DateTimeField(required=False, allow_null=True)


class DateRangeSerializer(serializers.Serializer):
    """Serializer for date range."""
    
    start = serializers.DateField()
    end = serializers.DateField()


class DemandForecastSerializer(serializers.ModelSerializer):
    """Serializer for individual demand forecasts."""
    
    item_name = serializers.CharField(source='item.title', read_only=True, allow_null=True)
    
    class Meta:
        model = DemandForecast
        fields = [
            'id', 'forecast_date', 'item', 'item_name',
            'predicted_quantity',
            'lower_bound_80', 'upper_bound_80',
            'lower_bound_95', 'upper_bound_95',
            'trend', 'weekly_seasonality',
            'created_at'
        ]


class ForecastSummarySerializer(serializers.Serializer):
    """Serializer for forecast summary responses."""
    
    place_id = serializers.IntegerField()
    place_name = serializers.CharField()
    item_id = serializers.IntegerField(allow_null=True)
    item_name = serializers.CharField(allow_null=True)
    forecast_count = serializers.IntegerField()
    date_range = DateRangeSerializer()
    metrics = ForecastMetricsSerializer()
    forecasts = DemandForecastSerializer(many=True)


class ForecastNotFoundSerializer(serializers.Serializer):
    """Serializer for 404 forecast not found responses."""
    
    status = serializers.CharField(default='no_forecast')
    message = serializers.CharField()
    place_id = serializers.IntegerField()
    place_name = serializers.CharField(required=False)
    item_id = serializers.IntegerField(required=False, allow_null=True)


class GenerateForecastRequestSerializer(serializers.Serializer):
    """Serializer for forecast generation request."""
    
    place_id = serializers.IntegerField(required=True, help_text="ID of the place to generate forecasts for")
    item_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        help_text="Optional list of item IDs for item-specific forecasts"
    )
    days_ahead = serializers.IntegerField(
        default=7, 
        min_value=1, 
        max_value=90,
        help_text="Number of days to forecast (1-90)"
    )
    
    def validate_place_id(self, value):
        from apps.core.models import Place
        if not Place.objects.filter(pk=value).exists():
            raise serializers.ValidationError(f"Place with id {value} does not exist")
        return value
    
    def validate_item_ids(self, value):
        if value:
            from apps.inventory.models import Item
            existing_ids = set(Item.objects.filter(pk__in=value).values_list('pk', flat=True))
            missing = set(value) - existing_ids
            if missing:
                raise serializers.ValidationError(f"Items with ids {missing} do not exist")
        return value


class GenerateForecastResponseSerializer(serializers.Serializer):
    """Serializer for forecast generation response."""
    
    status = serializers.CharField()
    place_id = serializers.IntegerField()
    forecasts_generated = serializers.IntegerField()
    metrics = ForecastMetricsSerializer()
    message = serializers.CharField()


class GenerateForecastErrorSerializer(serializers.Serializer):
    """Serializer for forecast generation error response."""
    
    status = serializers.CharField(default='error')
    message = serializers.CharField()
    place_id = serializers.IntegerField()


class ForecastModelsListSerializer(serializers.Serializer):
    """Serializer for forecast models list response."""
    
    count = serializers.IntegerField()
    models = ForecastModelSerializer(many=True)
