from django.contrib import admin
from .models import Campaign, Order, OrderItem, OrderItemAddOn

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('title', 'place', 'discount_type', 'value')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'external_id', 'place', 'user', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'place')
    search_fields = ('external_id', 'id')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'item', 'quantity', 'price')

@admin.register(OrderItemAddOn)
class OrderItemAddOnAdmin(admin.ModelAdmin):
    list_display = ('order_item', 'add_on')

