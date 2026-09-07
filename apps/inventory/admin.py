from django.contrib import admin

from .models import InventoryBalance, StockMovement


@admin.register(InventoryBalance)
class InventoryBalanceAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "quantity",
        "updated_at",
    )

    search_fields = (
        "product__sku",
        "product__name",
    )

    ordering = (
        "product__name",
    )

    readonly_fields = (
        "product",
        "quantity",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "product",
        "movement_type",
        "quantity_delta",
        "quantity_before",
        "quantity_after",
        "order",
        "created_by",
    )

    list_filter = (
        "movement_type",
        "created_at",
    )

    search_fields = (
        "product__sku",
        "product__name",
        "reason",
        "order__order_number",
    )

    readonly_fields = (
        "product",
        "order",
        "movement_type",
        "quantity_delta",
        "quantity_before",
        "quantity_after",
        "reason",
        "created_by",
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in (
            "GET",
            "HEAD",
            "OPTIONS",
        )

    def has_delete_permission(self, request, obj=None):
        return False