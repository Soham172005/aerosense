from django.contrib import admin
from .models import Product

# Register your models here.

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "product_type", "price", "effectiveness", "rating")
    list_filter = ("product_type",)
    search_fields = ("name", "description")