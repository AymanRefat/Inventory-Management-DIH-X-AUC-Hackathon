"""
API views for the intelligence app.

Provides REST endpoints for demand forecasting:
- GET /api/forecast/{place_id}/ - Get forecasts for a place
- GET /api/forecast/{place_id}/item/{item_id}/ - Get item-specific forecast
- POST /api/forecast/generate/ - Trigger forecast generation
"""

from datetime import timedelta
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.core.models import Place
from apps.inventory.models import Item
from apps.intelligence.models import DemandForecast, ForecastModel
from apps.intelligence.serializers import (
    DemandForecastSerializer,
    ForecastModelSerializer,
    ForecastSummarySerializer,
    ForecastNotFoundSerializer,
    ForecastMetricsSerializer,
    DateRangeSerializer,
    ForecastModelsListSerializer,
    GenerateForecastRequestSerializer,
    GenerateForecastResponseSerializer,
    GenerateForecastErrorSerializer,
)
from apps.intelligence.forecaster import DemandForecaster, generate_forecasts_for_place


class ForecastListView(APIView):
    """
    Get demand forecasts for a place.
    
    Endpoint: GET /api/forecast/{place_id}/
    
    Query Parameters:
        days (int): Number of days to forecast (default: 7)
        include_history (bool): Whether to include past predictions (default: false)
    """
    
    def get(self, request, place_id):
        place = get_object_or_404(Place, pk=place_id)
        
        # Parse query parameters
        days = int(request.query_params.get('days', 7))
        include_history = request.query_params.get('include_history', 'false').lower() == 'true'
        
        # Get active forecast model for this place (no specific item)
        forecast_model = ForecastModel.objects.filter(
            place=place,
            item__isnull=True,
            is_active=True
        ).order_by('-training_date').first()
        
        if not forecast_model:
            error_data = {
                'status': 'no_forecast',
                'message': f'No forecast available for place {place.title}. Please generate forecasts first.',
                'place_id': place_id,
                'place_name': place.title
            }
            serializer = ForecastNotFoundSerializer(data=error_data)
            serializer.is_valid()
            return Response(serializer.data, status=status.HTTP_404_NOT_FOUND)
        
        # Get forecasts
        # Anchor to the model's training end date to support historical data evaluation
        anchor_date = forecast_model.training_end_date + timedelta(days=1)
        start_date = anchor_date - timedelta(days=7) if include_history else anchor_date
        end_date = anchor_date + timedelta(days=days)
        
        forecasts = DemandForecast.objects.filter(
            forecast_model=forecast_model,
            forecast_date__gte=start_date,
            forecast_date__lte=end_date
        ).order_by('forecast_date')
        
        # Build response using serializers
        response_data = {
            'place_id': place_id,
            'place_name': place.title,
            'item_id': None,
            'item_name': None,
            'forecast_count': forecasts.count(),
            'date_range': {
                'start': start_date,
                'end': end_date
            },
            'metrics': {
                'mape': forecast_model.mape,
                'rmse': forecast_model.rmse,
                'mae': forecast_model.mae,
                'training_date': forecast_model.training_date
            },
            'forecasts': forecasts
        }
        
        serializer = ForecastSummarySerializer(response_data)
        return Response(serializer.data)


class ForecastItemView(APIView):
    """
    Get demand forecasts for a specific item at a place.
    
    Endpoint: GET /api/forecast/{place_id}/item/{item_id}/
    
    Returns forecasts anchored to the model's training date.
    """
    
    def get(self, request, place_id, item_id):
        place = get_object_or_404(Place, pk=place_id)
        item = get_object_or_404(Item, pk=item_id)
        
        days = int(request.query_params.get('days', 7))
        
        # Get active forecast model for this item
        forecast_model = ForecastModel.objects.filter(
            place=place,
            item=item,
            is_active=True
        ).order_by('-training_date').first()
        
        if not forecast_model:
            error_data = {
                'status': 'no_forecast',
                'message': f'No forecast available for {item.title} at {place.title}',
                'place_id': place_id,
                'item_id': item_id
            }
            serializer = ForecastNotFoundSerializer(data=error_data)
            serializer.is_valid()
            return Response(serializer.data, status=status.HTTP_404_NOT_FOUND)
        
        # Anchor to the model's training end date to support historical data
        anchor_date = forecast_model.training_end_date + timedelta(days=1)
        start_date = anchor_date
        end_date = anchor_date + timedelta(days=days)
        
        forecasts = DemandForecast.objects.filter(
            forecast_model=forecast_model,
            forecast_date__gte=start_date,
            forecast_date__lte=end_date
        ).order_by('forecast_date')
        
        response_data = {
            'place_id': place_id,
            'place_name': place.title,
            'item_id': item_id,
            'item_name': item.title,
            'forecast_count': forecasts.count(),
            'date_range': {
                'start': start_date,
                'end': end_date
            },
            'metrics': {
                'mape': forecast_model.mape,
                'rmse': forecast_model.rmse,
                'mae': forecast_model.mae,
                'training_date': forecast_model.training_date
            },
            'forecasts': forecasts
        }
        
        serializer = ForecastSummarySerializer(response_data)
        return Response(serializer.data)


class GenerateForecastView(APIView):
    """
    Trigger forecast generation for a place.
    
    Endpoint: POST /api/forecast/generate/
    
    Payload:
        {
            "place_id": 1,
            "days_ahead": 7,
            "item_ids": [101, 102]  // Optional: generate for specific items only
        }
    """
    
    def post(self, request):
        request_serializer = GenerateForecastRequestSerializer(data=request.data)
        
        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        place_id = request_serializer.validated_data['place_id']
        days_ahead = request_serializer.validated_data.get('days_ahead', 7)
        item_ids = request_serializer.validated_data.get('item_ids', None)
        
        # Generate forecasts
        result = generate_forecasts_for_place(
            place_id=place_id,
            days_ahead=days_ahead,
            item_ids=item_ids
        )
        
        if 'error' in result:
            error_data = {
                'status': 'error',
                'message': result['error'],
                'place_id': place_id
            }
            error_serializer = GenerateForecastErrorSerializer(data=error_data)
            error_serializer.is_valid()
            return Response(error_serializer.data, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate total generated
        total_forecasts = sum(f.get('count', 0) for f in result.get('forecasts', []))
        
        # Use metrics from first forecast for summary
        first_forecast = result['forecasts'][0] if result['forecasts'] else {}
        raw_metrics = first_forecast.get('metrics', {})
        
        response_data = {
            'status': 'success',
            'place_id': place_id,
            'forecasts_generated': total_forecasts,
            'metrics': {
                'mape': raw_metrics.get('mape'),
                'rmse': raw_metrics.get('rmse'),
                'mae': raw_metrics.get('mae')
            },
            'message': f'Successfully generated {total_forecasts} forecasts for {days_ahead} days'
        }
        
        response_serializer = GenerateForecastResponseSerializer(data=response_data)
        response_serializer.is_valid()
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ForecastModelsListView(APIView):
    """
    List all trained forecast models.
    
    Endpoint: GET /api/forecast/models/
    Filters: place_id
    """
    
    def get(self, request):
        place_id = request.query_params.get('place_id')
        
        queryset = ForecastModel.objects.filter(is_active=True)
        
        if place_id:
            queryset = queryset.filter(place_id=place_id)
        
        queryset = queryset.order_by('-training_date')[:50]
        
        models_serializer = ForecastModelSerializer(queryset, many=True)
        
        response_data = {
            'count': len(models_serializer.data),
            'models': queryset
        }
        
        serializer = ForecastModelsListSerializer(response_data)
        return Response(serializer.data)


class ForecastDashboardView(TemplateView):
    """
    Render the main forecast dashboard page.
    """
    template_name = 'intelligence/dashboard.html'
    
    def get_context_data(self, **kwargs):
        from django.db.models import Count
        from apps.sales.models import Order
        
        context = super().get_context_data(**kwargs)
        
        # Get places with at least one order, sorted by activity
        places_with_orders = Place.objects.annotate(
            order_count=Count('orders')
        ).filter(order_count__gt=0).order_by('-order_count')[:20]
        
        context['places'] = places_with_orders
        context['recent_models'] = ForecastModel.objects.filter(
            is_active=True
        ).order_by('-training_date')[:5]
        return context


class AvailablePlacesView(APIView):
    """
    Get list of places that have data available for forecasting.
    
    Endpoint: GET /api/forecast/places/
    """
    
    def get(self, request):
        # We now query directly from the database instead of CSV files
        db_places = list(Place.objects.filter(active=True).values('id', 'title')[:50])
        
        enriched_places = []
        for place in db_places:
            # We could add order counts here if needed, but for now just returning available places
            enriched_places.append({
                'place_id': place['id'],
                'place_name': place['title'],
                'order_count': 0, # Placeholder, calculation is expensive
                'has_csv_data': True # Legacy field for compatibility
            })
        
        return Response({
            'count': len(enriched_places),
            'places': enriched_places
        })

class PlaceItemsView(APIView):
    """
    Get items for a specific place that have order history.
    
    GET /api/forecast/places/<place_id>/items/
    
    Returns items that have been ordered at this place,
    sorted by order frequency.
    """
    
    def get(self, request, place_id):
        from django.db.models import Sum, Count
        from apps.sales.models import OrderItem
        from apps.inventory.models import Item
        
        # Get items that have been ordered at this place with order counts
        items_with_orders = OrderItem.objects.filter(
            order__place_id=place_id,
            order__status__icontains='Closed',
            item__isnull=False
        ).values(
            'item_id',
            'item__title'
        ).annotate(
            order_count=Count('id'),
            total_quantity=Sum('quantity')
        ).order_by('-order_count')[:50]
        
        items = []
        for item in items_with_orders:
            items.append({
                'item_id': item['item_id'],
                'item_name': item['item__title'] or f"Item {item['item_id']}",
                'order_count': item['order_count'],
                'total_quantity': float(item['total_quantity'] or 0)
            })
        
        return Response({
            'place_id': place_id,
            'count': len(items),
            'items': items
        })


