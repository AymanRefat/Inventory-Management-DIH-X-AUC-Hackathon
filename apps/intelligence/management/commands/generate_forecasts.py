"""
Management command to generate AI demand forecasts.

Key Features:
- Forecast specific places or all places
- Forecast specific items or place-level demand
- Adjustable forecast horizon (days ahead)

Usage:
    python manage.py generate_forecasts --place_id=1 --days=7
    python manage.py generate_forecasts --all --days=14
    python manage.py generate_forecasts --place_id=1 --item_ids=101,102
"""

from django.core.management.base import BaseCommand, CommandError
from apps.core.models import Place
from apps.intelligence.forecaster import generate_forecasts_for_place


class Command(BaseCommand):
    help = 'Generates AI demand forecasts using Prophet for places and items.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--place_id',
            type=int,
            help='ID of the specific place (location) to forecast for'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Generate forecasts for ALL active places (batch mode)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to predict into the future (default: 7)'
        )
        parser.add_argument(
            '--item_ids',
            type=str,
            help='Comma-separated list of Item IDs to forecast (e.g. "101,102"). If omitted, forecasts place-level demand.'
        )

    def handle(self, *args, **options):
        place_id = options.get('place_id')
        generate_all = options.get('all')
        days = options.get('days', 7)
        item_ids_str = options.get('item_ids')
        
        # Parse item IDs if provided
        item_ids = None
        if item_ids_str:
            try:
                item_ids = [int(x.strip()) for x in item_ids_str.split(',')]
            except ValueError:
                raise CommandError("item_ids must be comma-separated integers")
        
        if not place_id and not generate_all:
            raise CommandError("You must specify either --place_id or --all")
        
        if generate_all:
            places = Place.objects.filter(active=True)
            self.stdout.write(f"Generating forecasts for {places.count()} places...")
            
            for place in places:
                self._generate_for_place(place.id, days, item_ids)
        else:
            if not Place.objects.filter(pk=place_id).exists():
                raise CommandError(f"Place with id {place_id} does not exist")
            
            self._generate_for_place(place_id, days, item_ids)
        
        self.stdout.write(self.style.SUCCESS("Forecast generation complete!"))

    def _generate_for_place(self, place_id, days, item_ids):
        """Generate forecasts for a single place."""
        place = Place.objects.get(pk=place_id)
        self.stdout.write(f"Processing: {place.title} (ID: {place_id})")
        
        try:
            result = generate_forecasts_for_place(
                place_id=place_id,
                days_ahead=days,
                item_ids=item_ids
            )
            
            if 'error' in result:
                self.stdout.write(
                    self.style.WARNING(f"  Warning: {result['error']}")
                )
            else:
                total = sum(f.get('count', 0) for f in result.get('forecasts', []))
                metrics = result['forecasts'][0]['metrics'] if result['forecasts'] else {}
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Generated {total} forecasts. "
                        f"MAPE: {metrics.get('mape', 'N/A')}%, "
                        f"RMSE: {metrics.get('rmse', 'N/A')}"
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  Error: {str(e)}")
            )
