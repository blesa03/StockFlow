from django.db.models import (
    Case,
    F,
    IntegerField,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.catalog.models import Product
from apps.inventory.models import StockMovement
from apps.orders.models import Order


def get_dashboard_metrics():
    today = timezone.localdate()

    return {
        "products": Product.objects.filter(
            active=True,
        ).count(),
        "low_stock": (
            Product.objects.filter(
                active=True,
            )
            .annotate(
                stock_quantity=Coalesce(
                    "inventory_balance__quantity",
                    Value(0),
                )
            )
            .filter(
                stock_quantity__lte=F("minimum_stock"),
            )
            .count()
        ),
        "draft_orders": Order.objects.filter(
            status=Order.Status.DRAFT,
        ).count(),
        "movements_today": StockMovement.objects.filter(
            created_at__date=today,
        ).count(),
    }


def get_products_requiring_attention(limit=6):
    queryset = (
        Product.objects.filter(
            active=True,
        )
        .select_related(
            "category",
            "supplier",
        )
        .annotate(
            stock_quantity=Coalesce(
                "inventory_balance__quantity",
                Value(0),
            )
        )
        .filter(
            stock_quantity__lte=F("minimum_stock"),
        )
        .annotate(
            stock_status=Case(
                When(
                    stock_quantity=0,
                    then=Value("out"),
                ),
                default=Value("low"),
            ),
            attention_priority=Case(
                When(
                    stock_quantity=0,
                    then=Value(0),
                ),
                default=Value(1),
                output_field=IntegerField(),
            ),
        )
        .order_by(
            "attention_priority",
            "stock_quantity",
            "name",
        )
    )

    return queryset[:limit]


def get_recent_movements(limit=8):
    return (
        StockMovement.objects.select_related(
            "product",
            "order",
            "created_by",
        )
        .order_by("-created_at")[:limit]
    )