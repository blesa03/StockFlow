from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

    fields = (
        "product",
        "quantity",
        "unit_price",
        "line_total_display",
    )

    readonly_fields = fields

    can_delete = False

    def line_total_display(self, obj):
        if not obj.pk:
            return "-"

        return obj.line_total

    line_total_display.short_description = "Total"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "customer_name",
        "status",
        "total_display",
        "created_at",
        "confirmed_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "order_number",
        "customer_name",
    )

    readonly_fields = (
        "order_number",
        "customer_name",
        "notes",
        "status",
        "created_by",
        "confirmed_by",
        "created_at",
        "confirmed_at",
        "total_display",
    )

    ordering = (
        "-created_at",
    )

    inlines = (
        OrderItemInline,
    )

    def total_display(self, obj):
        if not obj.pk:
            return "-"

        return obj.total

    total_display.short_description = "Total"

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