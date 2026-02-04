from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # Standard fields: username, first_name, last_name, email, password, etc.
    # Custom fields from dim_users
    mobile_phone = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=10, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    language = models.CharField(max_length=10, blank=True, null=True)
    roles = models.JSONField(default=list, blank=True) # Storing roles as list
    api_key = models.CharField(max_length=255, blank=True, null=True)
    
    # We will use email as the unique identifier
    email = models.EmailField(unique=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

class Place(models.Model):
    # Fields from dim_places
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    
    # Location / Contact
    country = models.CharField(max_length=100, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    timezone = models.CharField(max_length=50, blank=True, null=True)
    street_address = models.TextField(blank=True, null=True)
    
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=50, blank=True, null=True)
    
    # Configuration
    opening_hours = models.JSONField(blank=True, null=True)
    logo_url = models.URLField(blank=True, null=True)
    website_url = models.URLField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
