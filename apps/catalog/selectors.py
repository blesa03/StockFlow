from django.db.models import (
    Case,
    CharField,
    F,
    IntegerField,
    Q,
    Value,
    When,
)
from django.db.models.functions import Coalesce

from .models import Product


def with_stock_information(queryset):
    return queryset.annotate(
        stock_quantity=Coalesce(
            "inventory_balance__quantity",
            Value(0),
            output_field=IntegerField(),
        ),
    ).annotate(
        stock_status=Case(
            When(
                stock_quantity=0,
                then=Value("out"),
            ),
            When(
                stock_quantity__lte=F("minimum_stock"),
                then=Value("low"),
            ),
            default=Value("healthy"),
            output_field=CharField(),
        ),
    )


def get_products(
    *,
    search="",
    category="",
    supplier="",
    stock_status="",
    active="active",
):
    queryset = (
        Product.objects
        .select_related(
            "category",
            "supplier",
        )
    )

    queryset = with_stock_information(queryset)

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(sku__icontains=search)
        )

    if category:
        queryset = queryset.filter(
            category_id=category,
        )

    if supplier:
        queryset = queryset.filter(
            supplier_id=supplier,
        )

    if stock_status == "healthy":
        queryset = queryset.filter(
            stock_quantity__gt=F("minimum_stock"),
        )

    elif stock_status == "low":
        queryset = queryset.filter(
            stock_quantity__gt=0,
            stock_quantity__lte=F("minimum_stock"),
        )

    elif stock_status == "out":
        queryset = queryset.filter(
            stock_quantity=0,
        )

    if active == "active":
        queryset = queryset.filter(
            active=True,
        )

    elif active == "inactive":
        queryset = queryset.filter(
            active=False,
        )

    return queryset.order_by(
        "name",
    )


def get_product_with_stock(product_id):
    return (
        with_stock_information(
            Product.objects.select_related(
                "category",
                "supplier",
            )
        )
        .get(pk=product_id)
    )