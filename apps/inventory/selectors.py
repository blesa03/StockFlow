from django.db.models import (
    Case,
    CharField,
    Count,
    F,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce

from .models import InventoryBalance, StockMovement


def with_stock_status(queryset):
    return queryset.annotate(
        stock_status=Case(
            When(
                quantity=0,
                then=Value("out"),
            ),
            When(
                quantity__lte=F(
                    "product__minimum_stock"
                ),
                then=Value("low"),
            ),
            default=Value("healthy"),
            output_field=CharField(),
        )
    )


def get_inventory_balances(
    *,
    search="",
    category="",
    stock_status="",
    active="active",
):
    queryset = (
        InventoryBalance.objects
        .select_related(
            "product",
            "product__category",
            "product__supplier",
        )
    )

    queryset = with_stock_status(queryset)

    if search:
        queryset = queryset.filter(
            Q(
                product__sku__icontains=search
            )
            | Q(
                product__name__icontains=search
            )
        )

    if category:
        queryset = queryset.filter(
            product__category_id=category,
        )

    if stock_status == "healthy":
        queryset = queryset.filter(
            quantity__gt=F(
                "product__minimum_stock"
            )
        )

    elif stock_status == "low":
        queryset = queryset.filter(
            quantity__gt=0,
            quantity__lte=F(
                "product__minimum_stock"
            ),
        )

    elif stock_status == "out":
        queryset = queryset.filter(
            quantity=0,
        )

    if active == "active":
        queryset = queryset.filter(
            product__active=True,
        )

    elif active == "inactive":
        queryset = queryset.filter(
            product__active=False,
        )

    return queryset.order_by(
        "product__name"
    )


def get_inventory_metrics():
    queryset = InventoryBalance.objects.filter(
        product__active=True,
    )

    aggregate = queryset.aggregate(
        products=Count("pk"),
        total_units=Coalesce(
            Sum("quantity"),
            0,
        ),
    )

    aggregate["low_stock"] = (
        queryset
        .filter(
            quantity__gt=0,
            quantity__lte=F(
                "product__minimum_stock"
            ),
        )
        .count()
    )

    aggregate["out_of_stock"] = (
        queryset
        .filter(
            quantity=0,
        )
        .count()
    )

    return aggregate


def get_stock_movements(
    *,
    search="",
    movement_type="",
):
    queryset = (
        StockMovement.objects
        .select_related(
            "product",
            "order",
            "created_by",
        )
    )

    if search:
        queryset = queryset.filter(
            Q(
                product__sku__icontains=search
            )
            | Q(
                product__name__icontains=search
            )
            | Q(
                reason__icontains=search
            )
            | Q(
                order__order_number__icontains=search
            )
        )

    if movement_type:
        queryset = queryset.filter(
            movement_type=movement_type,
        )

    return queryset.order_by(
        "-created_at"
    )