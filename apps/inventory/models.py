from django.db import models
from apps.core.models import Place

class StockCategory(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='categories')
    title = models.CharField(max_length=255)
    external_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    def __str__(self):
        return self.title

class AddOnCategory(models.Model):
    title = models.CharField(max_length=255)
    external_id = models.CharField(max_length=100, unique=True, null=True, blank=True)

    def __str__(self):
        return self.title

class AddOn(models.Model):
    category = models.ForeignKey(AddOnCategory, on_delete=models.CASCADE, related_name='add_ons')
    title = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    external_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    def __str__(self):
        return self.title

class Item(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='items', null=True) # Items usually belong to a place
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # Linking to StockCategory as "section"
    category = models.ForeignKey(StockCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    
    # M2M relationships
    add_on_categories = models.ManyToManyField(AddOnCategory, blank=True, related_name='items')
    
    external_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

class SKU(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='skus')
    title = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=15, decimal_places=3, default=0) # Inventory level
    unit = models.CharField(max_length=50, blank=True)
    low_stock_threshold = models.DecimalField(max_digits=15, decimal_places=3, null=True)
    
    external_id = models.CharField(max_length=100, unique=True, null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({self.item.title})"

class BillOfMaterial(models.Model):
    parent_sku = models.ForeignKey(SKU, on_delete=models.CASCADE, related_name='bom_parents')
    child_sku = models.ForeignKey(SKU, on_delete=models.CASCADE, related_name='bom_children')
    quantity = models.DecimalField(max_digits=10, decimal_places=4) # How much child is needed for 1 parent
    
    class Meta:
        unique_together = ('parent_sku', 'child_sku')

class Batch(models.Model):
    """
    Tracks specific batches of SKUs for expiration (FIFO/FEFO).
    """
    sku = models.ForeignKey(SKU, on_delete=models.CASCADE, related_name='batches')
    quantity = models.DecimalField(max_digits=15, decimal_places=3)
    expiration_date = models.DateField()
    received_date = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.sku.title} - Exp: {self.expiration_date}"

class InventoryReport(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    user = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    data = models.TextField(blank=True) # JSON dump
    excel = models.URLField(blank=True, null=True)
    pdf = models.URLField(blank=True, null=True)
    
    external_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TaxonomyTerm(models.Model):
    user = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255)
    vocabulary = models.CharField(max_length=255, blank=True)
    
    external_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class MenuItemAddOnDefinition(models.Model):
    # Mapping dim_menu_item_add_ons.csv
    # "id","category_id","created","title","select_as_default","status","index","price"
    # This seems to be a variation or option definition distinct from 'AddOn' possibly?
    # Or just another table for AddOns.
    title = models.CharField(max_length=255)
    category_id_ref = models.CharField(max_length=100, blank=True) # External Category ID
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    select_as_default = models.BooleanField(default=False)
    status = models.CharField(max_length=50, blank=True)
    
    external_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
