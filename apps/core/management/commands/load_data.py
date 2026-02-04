import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.models import Place, User
from apps.inventory.models import StockCategory, AddOnCategory, AddOn, Item, SKU, BillOfMaterial, Batch
from apps.sales.models import Campaign, Order, OrderItem
import random
from datetime import timedelta

class Command(BaseCommand):
    help = 'Load data from CSV files into the database (Normalized)'

    def handle(self, *args, **options):
        self.stdout.write('Loading normalized data...')
        
        # Paths
        base_dir = 'data'
        
        # Helper to read CSV
        def read_csv(filename):
             path = os.path.join(base_dir, filename)
             if not os.path.exists(path):
                 print(f"Warning: {filename} not found.")
                 return []
             with open(path, 'r', encoding='utf-8') as f:
                 return list(csv.DictReader(f))

        # 1. Places
        self.stdout.write('Loading Places...')
        places_data = read_csv('dim_places.csv')
        for row in places_data:
            Place.objects.update_or_create(
                id=row['id'],
                defaults={
                    'title': row.get('title', 'Unknown'),
                    'currency': row.get('currency'),
                    'country': row.get('country'),
                    'timezone': row.get('timezone'),
                    'active': row.get('active') == '1'
                }
            )

        # 2. Users
        self.stdout.write('Loading Users...')
        users_data = read_csv('dim_users.csv')
        users_to_create = []
        for row in users_data:
            email = row.get('email')
            if not email:
                email = f"user_{row['id']}@example.com"
            
            # Skip if exists (for re-runs)
            if User.objects.filter(email=email).exists():
                continue
                
            users_to_create.append(User(
                username=email,
                email=email,
                first_name=row.get('first_name', ''),
                last_name=row.get('last_name', ''),
                mobile_phone=row.get('mobile_phone'),
                country=row.get('country'),
                currency=row.get('currency'),
            ))
        User.objects.bulk_create(users_to_create, ignore_conflicts=True)

        # 3. Categories
        self.stdout.write('Loading Categories...')
        cats_data = read_csv('dim_stock_categories.csv')
        for row in cats_data:
            StockCategory.objects.update_or_create(
                external_id=row['id'],
                defaults={
                    'title': row.get('title', 'Unknown'),
                    'place_id': row.get('place_id') if Place.objects.filter(id=row.get('place_id')).exists() else None
                }
            )

        # 4. Items (Inventory)
        self.stdout.write('Loading Items...')
        items_data = read_csv('dim_items.csv')
        for row in items_data:
            try:
                price = float(row.get('price', 0) or 0)
            except:
                price = 0
            
            section_id = row.get('section_id')
            category = StockCategory.objects.filter(external_id=section_id).first() 
            
            Item.objects.update_or_create(
                external_id=row['id'],
                defaults={
                    'title': row.get('title', 'Unknown'),
                    'description': row.get('description', ''),
                    'price': price,
                    'category': category,
                    # We assume place_id might be inferred or we skip it for now as it wasn't in dim_items directly? 
                    # check dim_items schema -> no place_id. Maybe it's global or derived from section?
                    # Let's leave place null for now or assume a default place if needed.
                }
            )

        # 5. SKUs
        self.stdout.write('Loading SKUs...')
        skus_data = read_csv('dim_skus.csv')
        for row in skus_data:
            item_id = row.get('item_id')
            item = Item.objects.filter(external_id=item_id).first()
            if not item:
                continue
                
            try:
                qty = float(row.get('quantity', 0) or 0)
            except:
                qty = 0
            
            sku, _ = SKU.objects.update_or_create(
                external_id=row['id'],
                defaults={
                    'title': row.get('title', 'Unknown'),
                    'item': item,
                    'quantity': qty,
                    'unit': row.get('unit', '')
                }
            )
            
            # Create dummy batches for this SKU
            Batch.objects.get_or_create(
                sku=sku,
                defaults={
                    'quantity': qty,
                    'expiration_date': timezone.now().date() + timedelta(days=random.randint(2, 30))
                }
            )

        # 6. Orders
        self.stdout.write('Loading Orders (Top 1000 latest)...')
        orders_data = read_csv('fct_orders.csv')
        # Sort by date desc and take top 1000 to save time
        orders_data.sort(key=lambda x: x['created'], reverse=True)
        orders_data = orders_data[:1000]
        
        for row in orders_data:
            place_id = row.get('place_id')
            if not Place.objects.filter(id=place_id).exists():
                continue
                
            user_external_id = row.get('user_id')
            # Mapping user is hard without ID map, let's try to match by email if possible or just skip user linkage for speed
            # We implemented User with auto-email. We can't easily link back without a map.
            # For hackathon, let's leave user null if not easily found.
            
            try:
                ts = int(row.get('created', 0))
                created_dt = datetime.fromtimestamp(ts)
            except:
                created_dt = timezone.now()
                
            Order.objects.update_or_create(
                external_id=row['id'],
                defaults={
                    'place_id': place_id,
                    'status': row.get('status', 'Pending'),
                    'total_amount': row.get('total_amount', 0),
                    'created_at': created_dt,
                    'payment_method': row.get('payment_method', '')
                }
            )

        # 7. Order Items
        self.stdout.write('Loading OrderItems...')
        oi_data = read_csv('fct_order_items.csv')
        # Filter for loaded orders
        loaded_order_ids = set(Order.objects.values_list('external_id', flat=True))
        
        items_to_create = []
        for row in oi_data:
            order_id = row.get('order_id')
            if order_id not in loaded_order_ids:
                continue
                
            item_id = row.get('item_id')
            item = Item.objects.filter(external_id=item_id).first()
            if not item:
                continue
                
            order = Order.objects.get(external_id=order_id)
            
            items_to_create.append(OrderItem(
                external_id=row['id'],
                order=order,
                item=item,
                quantity=row.get('quantity', 1),
                price=row.get('price', 0)
            ))
        
        OrderItem.objects.bulk_create(items_to_create, ignore_conflicts=True)
        
        self.stdout.write(self.style.SUCCESS('Data loading complete!'))
