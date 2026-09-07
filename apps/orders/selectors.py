from decimal import Decimal

from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Prefetch,
    Q,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce

from .models import Order, OrderItem

ORDER_TOTAL_FIELD = DecimalField(
    max_digits=14,
    decimal_places=2,
)


def get_orders(
    *,
    search="",
    status="",
):
    line_total_expression = (
        ExpressionWrapper(
            F("items__quantity")
            * F("items__unit_price"),
            output_field=ORDER_TOTAL_FIELD,
        )
    )

    queryset = (
        Order.objects
        .select_related(
            "created_by",
            "confirmed_by",
        )
        .annotate(
            item_count=Count(
                "items",
            ),
            total_amount=Coalesce(
                Sum(
                    line_total_expression,
                ),
                Value(
                    Decimal("0.00"),
                    output_field=(
                        ORDER_TOTAL_FIELD
                    ),
                ),
                output_field=(
                    ORDER_TOTAL_FIELD
                ),
            ),
        )
    )

    if search:
        queryset = queryset.filter(
            Q(
                order_number__icontains=search
            )
            | Q(
                customer_name__icontains=search
            )
            | Q(
                notes__icontains=search
            )
        )

    if status:
        queryset = queryset.filter(
            status=status,
        )

    return queryset.order_by(
        "-created_at"
    )


def get_order_metrics():
    queryset = Order.objects.all()

    return {
        "total": queryset.count(),
        "draft": queryset.filter(
            status=Order.Status.DRAFT,
        ).count(),
        "confirmed": queryset.filter(
            status=Order.Status.CONFIRMED,
        ).count(),
        "cancelled": queryset.filter(
            status=Order.Status.CANCELLED,
        ).count(),
    }


def get_order_detail(order_id):
    item_queryset = (
        OrderItem.objects
        .select_related(
            "product",
            "product__category",
            "product__inventory_balance",
        )
        .order_by(
            "pk",
        )
    )

    return (
        Order.objects
        .select_related(
            "created_by",
            "confirmed_by",
        )
        .prefetch_related(
            Prefetch(
                "items",
                queryset=item_queryset,
            )
        )
        .get(
            pk=order_id,
        )
    )