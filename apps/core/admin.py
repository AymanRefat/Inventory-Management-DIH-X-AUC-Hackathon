from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Place

@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ('title', 'id', 'active', 'country')
    search_fields = ('title', 'id')

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_staff')
    ordering = ('email',)
