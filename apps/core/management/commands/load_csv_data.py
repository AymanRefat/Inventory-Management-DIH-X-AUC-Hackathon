"""
Management command to load CSV data into the database.

Loads places, items, orders, and order_items from CSV files.
"""

import os
import csv
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.utils import timezone

# Increase CSV field size limit
csv.field_size_limit(sys.maxsize)


class Command(BaseCommand):
    help = 'Load CSV data files into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--places',
            action='store_true',
            help='Load only places'
        )
        parser.add_argument(
            '--items',
            action='store_true',
            help='Load only items'
        )
        parser.add_argument(
            '--orders',
            action='store_true',
            help='Load only orders'
        )
        parser.add_argument(
            '--order-items',
            action='store_true',
            help='Load only order items'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Load all data (places, items, orders, order_items)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of rows to load per file'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=5000,
            help='Batch size for bulk inserts (default: 5000)'
        )

    def handle(self, *args, **options):
        data_dir = os.path.join(settings.BASE_DIR, 'data')
        
        load_all = options['all']
        limit = options['limit']
        batch_size = options['batch_size']
        
        if load_all or options['places']:
            self.load_places(data_dir, limit, batch_size)
        
        if load_all or options['items']:
            self.load_items(data_dir, limit, batch_size)
        
        if load_all or options['orders']:
            self.load_orders(data_dir, limit, batch_size)
        
        if load_all or options['order_items']:
            self.load_order_items(data_dir, limit, batch_size)
        
        if not any([load_all, options['places'], options['items'], 
                    options['orders'], options['order_items']]):
            self.stdout.write(self.style.WARNING(
                'No data type specified. Use --all or specific flags (--places, --items, --orders, --order-items)'
            ))

    def safe_int(self, value, default=None):
        """Convert value to int safely."""
        if value is None or value == '' or value == 'None':
            return default
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default

    def safe_decimal(self, value, default=Decimal('0')):
        """Convert value to Decimal safely."""
        if value is None or value == '' or value == 'None':
            return default
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return default

    def safe_datetime(self, timestamp, default=None):
        """Convert Unix timestamp to datetime."""
        if timestamp is None or timestamp == '' or timestamp == 'None':
            return default or timezone.now()
        try:
            ts = int(float(timestamp))
            return datetime.fromtimestamp(ts, tz=timezone.get_current_timezone())
        except (ValueError, TypeError, OSError):
            return default or timezone.now()

    def load_places(self, data_dir, limit=None, batch_size=5000):
        """Load places from dim_places.csv."""
        from apps.core.models import Place
        
        filepath = os.path.join(data_dir, 'dim_places.csv')
        if not os.path.exists(filepath):
            self.stdout.write(self.style.ERROR(f'File not found: {filepath}'))
            return
        
        self.stdout.write(f'Loading places from {filepath}...')
        
        # Get existing place IDs
        existing_ids = set(Place.objects.values_list('id', flat=True))
        
        places_to_create = []
        count = 0
        skipped = 0
        
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                if limit and count >= limit:
                    break
                
                place_id = self.safe_int(row.get('id'))
                if not place_id:
                    skipped += 1
                    continue
                
                if place_id in existing_ids:
                    skipped += 1
                    continue
                
                place = Place(
                    id=place_id,
                    title=row.get('title', f'Place {place_id}')[:255],
                    description=row.get('description', '')[:1000] if row.get('description') else '',
                    active=True,
                    country=row.get('country', '')[:100] if row.get('country') else None,
                    currency=row.get('currency', '')[:10] if row.get('currency') else None,
                    timezone=row.get('timezone', '')[:50] if row.get('timezone') else None,
                    street_address=row.get('street_address', '')[:500] if row.get('street_address') else None,
                    contact_email=row.get('email', '')[:254] if row.get('email') else None,
                    contact_phone=row.get('phone', '')[:50] if row.get('phone') else None,
                )
                places_to_create.append(place)
                count += 1
                
                if len(places_to_create) >= batch_size:
                    Place.objects.bulk_create(places_to_create, ignore_conflicts=True)
                    self.stdout.write(f'  Created {count} places...')
                    places_to_create = []
        
        # Create remaining
        if places_to_create:
            Place.objects.bulk_create(places_to_create, ignore_conflicts=True)
        
        self.stdout.write(self.style.SUCCESS(
            f'Loaded {count} places ({skipped} skipped)'
        ))

    def load_items(self, data_dir, limit=None, batch_size=5000):
        """Load items from dim_items.csv."""
        from apps.inventory.models import Item
        from apps.core.models import Place
        
        filepath = os.path.join(data_dir, 'dim_items.csv')
        if not os.path.exists(filepath):
            self.stdout.write(self.style.ERROR(f'File not found: {filepath}'))
            return
        
        self.stdout.write(f'Loading items from {filepath}...')
        
        # Get existing item IDs and place IDs
        existing_item_ids = set(Item.objects.values_list('id', flat=True))
        valid_place_ids = set(Place.objects.values_list('id', flat=True))
        
        items_to_create = []
        count = 0
        skipped = 0
        
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                if limit and count >= limit:
                    break
                
                item_id = self.safe_int(row.get('id'))
                if not item_id:
                    skipped += 1
                    continue
                
                if item_id in existing_item_ids:
                    skipped += 1
                    continue
                
                # Get place_id from user_id (items belong to place via user)
                place_id = self.safe_int(row.get('user_id'))
                if not place_id or place_id not in valid_place_ids:
                    # Create a placeholder place if needed
                    if place_id and place_id not in valid_place_ids:
                        Place.objects.get_or_create(
                            id=place_id,
                            defaults={'title': f'Place {place_id}', 'active': True}
                        )
                        valid_place_ids.add(place_id)
                    else:
                        skipped += 1
                        continue
                
                item = Item(
                    id=item_id,
                    place_id=place_id,
                    title=row.get('title', f'Item {item_id}')[:255],
                    description=row.get('description', '')[:1000] if row.get('description') else '',
                    price=self.safe_decimal(row.get('price'), Decimal('0')),
                )
                items_to_create.append(item)
                count += 1
                
                if len(items_to_create) >= batch_size:
                    Item.objects.bulk_create(items_to_create, ignore_conflicts=True)
                    self.stdout.write(f'  Created {count} items...')
                    items_to_create = []
        
        # Create remaining
        if items_to_create:
            Item.objects.bulk_create(items_to_create, ignore_conflicts=True)
        
        self.stdout.write(self.style.SUCCESS(
            f'Loaded {count} items ({skipped} skipped)'
        ))

    def load_orders(self, data_dir, limit=None, batch_size=5000):
        """Load orders from fct_orders.csv."""
        from apps.sales.models import Order
        from apps.core.models import Place
        
        filepath = os.path.join(data_dir, 'fct_orders.csv')
        if not os.path.exists(filepath):
            self.stdout.write(self.style.ERROR(f'File not found: {filepath}'))
            return
        
        self.stdout.write(f'Loading orders from {filepath}...')
        
        # Get existing order IDs and place IDs
        existing_order_ids = set(Order.objects.values_list('id', flat=True))
        valid_place_ids = set(Place.objects.values_list('id', flat=True))
        
        orders_to_create = []
        count = 0
        skipped = 0
        
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                if limit and count >= limit:
                    break
                
                order_id = self.safe_int(row.get('id'))
                if not order_id:
                    skipped += 1
                    continue
                
                if order_id in existing_order_ids:
                    skipped += 1
                    continue
                
                place_id = self.safe_int(row.get('place_id'))
                if not place_id:
                    skipped += 1
                    continue
                
                # Create place if needed
                if place_id not in valid_place_ids:
                    Place.objects.get_or_create(
                        id=place_id,
                        defaults={'title': f'Place {place_id}', 'active': True}
                    )
                    valid_place_ids.add(place_id)
                
                order = Order(
                    id=order_id,
                    place_id=place_id,
                    status=row.get('status', 'Unknown')[:50],
                    total_amount=self.safe_decimal(row.get('total_amount'), Decimal('0')),
                    payment_method=row.get('payment_method', '')[:50] if row.get('payment_method') else '',
                    created_at=self.safe_datetime(row.get('created')),
                    external_id=str(order_id),
                )
                orders_to_create.append(order)
                count += 1
                
                if len(orders_to_create) >= batch_size:
                    Order.objects.bulk_create(orders_to_create, ignore_conflicts=True)
                    self.stdout.write(f'  Created {count} orders...')
                    orders_to_create = []
        
        # Create remaining
        if orders_to_create:
            Order.objects.bulk_create(orders_to_create, ignore_conflicts=True)
        
        self.stdout.write(self.style.SUCCESS(
            f'Loaded {count} orders ({skipped} skipped)'
        ))

    def load_order_items(self, data_dir, limit=None, batch_size=5000):
        """Load order items from fct_order_items.csv."""
        from apps.sales.models import OrderItem, Order
        from apps.inventory.models import Item
        
        filepath = os.path.join(data_dir, 'fct_order_items.csv')
        if not os.path.exists(filepath):
            self.stdout.write(self.style.ERROR(f'File not found: {filepath}'))
            return
        
        self.stdout.write(f'Loading order items from {filepath}...')
        
        # Get existing order item IDs, order IDs, and item IDs
        existing_ids = set(OrderItem.objects.values_list('id', flat=True))
        valid_order_ids = set(Order.objects.values_list('id', flat=True))
        valid_item_ids = set(Item.objects.values_list('id', flat=True))
        
        items_to_create = []
        count = 0
        skipped = 0
        
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                if limit and count >= limit:
                    break
                
                oi_id = self.safe_int(row.get('id'))
                if not oi_id:
                    skipped += 1
                    continue
                
                if oi_id in existing_ids:
                    skipped += 1
                    continue
                
                order_id = self.safe_int(row.get('order_id'))
                if not order_id or order_id not in valid_order_ids:
                    skipped += 1
                    continue
                
                item_id = self.safe_int(row.get('item_id'))
                # item_id can be null in OrderItem model
                if item_id and item_id not in valid_item_ids:
                    item_id = None  # Set to null if item doesn't exist
                
                order_item = OrderItem(
                    id=oi_id,
                    order_id=order_id,
                    item_id=item_id,
                    quantity=self.safe_decimal(row.get('quantity'), Decimal('1')),
                    price=self.safe_decimal(row.get('price'), Decimal('0')),
                    external_id=str(oi_id),
                )
                items_to_create.append(order_item)
                count += 1
                
                if len(items_to_create) >= batch_size:
                    OrderItem.objects.bulk_create(items_to_create, ignore_conflicts=True)
                    self.stdout.write(f'  Created {count} order items...')
                    items_to_create = []
        
        # Create remaining
        if items_to_create:
            OrderItem.objects.bulk_create(items_to_create, ignore_conflicts=True)
        
        self.stdout.write(self.style.SUCCESS(
            f'Loaded {count} order items ({skipped} skipped)'
        ))
