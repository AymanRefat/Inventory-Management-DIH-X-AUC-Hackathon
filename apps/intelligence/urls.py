"""
URL routing for the intelligence app.
"""

from django.urls import path
from apps.intelligence.views import (
    ForecastListView,
    ForecastItemView,
    GenerateForecastView,
    ForecastModelsListView,
    ForecastDashboardView,
    AvailablePlacesView,
    PlaceItemsView,
)

app_name = 'intelligence'

urlpatterns = [
    # Dashboard
    path('', ForecastDashboardView.as_view(), name='dashboard'),
    
    # API endpoints
    path('api/forecast/generate/', GenerateForecastView.as_view(), name='generate-forecast'),
    path('api/forecast/models/', ForecastModelsListView.as_view(), name='forecast-models'),
    path('api/forecast/places/', AvailablePlacesView.as_view(), name='available-places'),
    path('api/forecast/places/<int:place_id>/items/', PlaceItemsView.as_view(), name='place-items'),
    path('api/forecast/<int:place_id>/', ForecastListView.as_view(), name='forecast-list'),
    path('api/forecast/<int:place_id>/item/<int:item_id>/', ForecastItemView.as_view(), name='forecast-item'),
]

