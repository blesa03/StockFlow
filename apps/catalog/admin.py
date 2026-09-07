from django.contrib import admin

from .models import Category, Product, Supplier


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "active",
        "created_at",
    )

    list_filter = ("active",)

    search_fields = (
        "name",
    )

    ordering = (
        "name",
    )


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "phone",
        "active",
    )

    list_filter = (
        "active",
    )

    search_fields = (
        "name",
        "email",
    )

    ordering = (
        "name",
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "name",
        "category",
        "supplier",
        "price",
        "minimum_stock",
        "active",
    )

    list_filter = (
        "active",
        "category",
        "supplier",
    )

    search_fields = (
        "sku",
        "name",
    )

    autocomplete_fields = (
        "category",
        "supplier",
    )

    ordering = (
        "name",
    )