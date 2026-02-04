from django.db import models
from apps.core.models import User, Place
from apps.inventory.models import Item, AddOn

class Campaign(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='campaigns')
    title = models.CharField(max_length=255)
    discount_type = models.CharField(max_length=50, blank=True) # percent, fixed
    value = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    external_id = models.CharField(max_length=100, unique=True, null=True, blank=True)

    def __str__(self):
        return self.title

class Order(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='orders')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
    status = models.CharField(max_length=50, default='Pending')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField() # We will insert historical data
    updated_at = models.DateTimeField(auto_now=True)
    
    external_id = models.CharField(max_length=100, unique=True, null=True, blank=True)

    def __str__(self):
        return f"Order {self.external_id or self.id} - {self.total_amount}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, related_name='order_items')
    
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2) # Price at moment of sale
    
    external_id = models.CharField(max_length=100, unique=True, null=True, blank=True)

    def __str__(self):
        return f"{self.quantity}x {self.item.title if self.item else 'Unknown'}"

class OrderItemAddOn(models.Model):
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='add_ons')
    add_on = models.ForeignKey(AddOn, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.add_on.title} for Item {self.order_item.id}"

class InvoiceItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    invoice_id = models.CharField(max_length=100, null=True, blank=True) # External ref
    product_id = models.CharField(max_length=100, null=True, blank=True)
    
    external_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CashBalance(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    closing_coins_and_notes = models.TextField(blank=True, null=True)
    opening_coins_and_notes = models.TextField(blank=True, null=True)
    transactions = models.TextField(blank=True, null=True) # JSON or text
    status = models.CharField(max_length=50, blank=True)
    
    start_time = models.DateTimeField(null=True, blank=True) # corresponds to created or similar
    end_time = models.DateTimeField(null=True, blank=True)
    
    external_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class BonusCode(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    points = models.IntegerField(default=0)
    redemptions = models.IntegerField(default=0)
    start_date_time = models.DateTimeField(null=True, blank=True)
    end_date_time = models.DateTimeField(null=True, blank=True)
    
    external_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class MostOrderedStat(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    item_id = models.CharField(max_length=100, blank=True) # External Item ID commonly
    item_name = models.CharField(max_length=255)
    order_count = models.IntegerField(default=0)
    store_address = models.TextField(blank=True)
    device_serial = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"{self.item_name} ({self.order_count})"
