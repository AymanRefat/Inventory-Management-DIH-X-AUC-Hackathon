from django.contrib import admin
from .models import StockCategory, Item, SKU, Batch, AddOn, AddOnCategory, BillOfMaterial

@admin.register(StockCategory)
class StockCategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'place', 'external_id')

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'category', 'external_id')
    search_fields = ('title', 'external_id')
    list_filter = ('category',)

@admin.register(SKU)
class SKUAdmin(admin.ModelAdmin):
    list_display = ('title', 'item', 'quantity', 'unit')
    search_fields = ('title', 'item__title')

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('sku', 'quantity', 'expiration_date')
    list_filter = ('expiration_date',)

admin.site.register(AddOn)
admin.site.register(AddOnCategory)
admin.site.register(BillOfMaterial)
