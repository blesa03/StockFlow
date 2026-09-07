from decimal import Decimal, InvalidOperation

from django.db import transaction

from apps.catalog.models import Product
from apps.inventory.models import (
    InventoryBalance,
    StockMovement,
)

from .models import Order, OrderItem


class OrderError(Exception):
    """Base exception for order operations."""


class InvalidOrderStateError(OrderError):
    """Raised when an operation is invalid for the order state."""


class InvalidOrderItemError(OrderError):
    """Raised when order item data is invalid."""


class EmptyOrderError(OrderError):
    """Raised when attempting to confirm an empty order."""


class InsufficientOrderStockError(OrderError):
    """Raised when one or more order items have insufficient stock."""

    def __init__(self, shortages):
        self.shortages = shortages

        message = "Insufficient stock for one or more products."

        super().__init__(message)


def _validate_customer_name(customer_name):
    if not customer_name or not customer_name.strip():
        raise ValueError("Customer name is required.")

    return customer_name.strip()


def _validate_quantity(quantity):
    if not isinstance(quantity, int) or isinstance(quantity, bool):
        raise InvalidOrderItemError(
            "Quantity must be an integer."
        )

    if quantity <= 0:
        raise InvalidOrderItemError(
            "Quantity must be greater than zero."
        )


def _validate_unit_price(unit_price):
    try:
        unit_price = Decimal(str(unit_price))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise InvalidOrderItemError(
            "Unit price must be a valid decimal number."
        ) from exc

    if unit_price < 0:
        raise InvalidOrderItemError(
            "Unit price cannot be negative."
        )

    return unit_price


def _get_locked_order(order):
    return Order.objects.select_for_update().get(
        pk=order.pk,
    )


def _ensure_draft(order):
    if order.status != Order.Status.DRAFT:
        raise InvalidOrderStateError(
            f"{order.order_number} is not editable."
        )


def create_order(
    *,
    customer_name,
    notes="",
    created_by=None,
):
    customer_name = _validate_customer_name(
        customer_name
    )

    return Order.objects.create(
        customer_name=customer_name,
        notes=notes.strip() if notes else "",
        created_by=created_by,
    )


@transaction.atomic
def add_order_item(
    *,
    order: Order,
    product: Product,
    quantity: int,
    unit_price=None,
):
    _validate_quantity(quantity)

    locked_order = _get_locked_order(order)
    _ensure_draft(locked_order)

    if unit_price is None:
        unit_price = product.price

    unit_price = _validate_unit_price(unit_price)

    item, created = OrderItem.objects.get_or_create(
        order=locked_order,
        product=product,
        defaults={
            "quantity": quantity,
            "unit_price": unit_price,
        },
    )

    if not created:
        item.quantity += quantity
        item.save(
            update_fields=["quantity"]
        )

    return item


@transaction.atomic
def update_order_item_quantity(
    *,
    item: OrderItem,
    quantity: int,
):
    _validate_quantity(quantity)

    locked_order = _get_locked_order(
        item.order
    )

    _ensure_draft(locked_order)

    locked_item = OrderItem.objects.select_for_update().get(
        pk=item.pk,
        order=locked_order,
    )

    locked_item.quantity = quantity

    locked_item.save(
        update_fields=["quantity"]
    )

    return locked_item


@transaction.atomic
def remove_order_item(
    *,
    item: OrderItem,
):
    locked_order = _get_locked_order(
        item.order
    )

    _ensure_draft(locked_order)

    locked_item = OrderItem.objects.select_for_update().get(
        pk=item.pk,
        order=locked_order,
    )

    locked_item.delete()


@transaction.atomic
def cancel_order(
    *,
    order: Order,
):
    locked_order = _get_locked_order(order)

    _ensure_draft(locked_order)

    locked_order.status = Order.Status.CANCELLED

    locked_order.save(
        update_fields=["status"]
    )

    return locked_order


@transaction.atomic
def confirm_order(
    *,
    order: Order,
    confirmed_by=None,
):
    locked_order = _get_locked_order(order)

    _ensure_draft(locked_order)

    items = list(
        OrderItem.objects.filter(
            order=locked_order,
        )
        .select_related("product")
        .order_by("product_id")
    )

    if not items:
        raise EmptyOrderError(
            "An empty order cannot be confirmed."
        )

    product_ids = [
        item.product_id
        for item in items
    ]

    balances = list(
        InventoryBalance.objects
        .select_for_update()
        .filter(product_id__in=product_ids)
        .order_by("product_id")
    )

    balances_by_product = {
        balance.product_id: balance
        for balance in balances
    }

    shortages = []

    for item in items:
        balance = balances_by_product.get(
            item.product_id
        )

        available = (
            balance.quantity
            if balance is not None
            else 0
        )

        if available < item.quantity:
            shortages.append(
                {
                    "product_id": item.product_id,
                    "sku": item.product.sku,
                    "name": item.product.name,
                    "requested": item.quantity,
                    "available": available,
                }
            )

    if shortages:
        raise InsufficientOrderStockError(
            shortages
        )

    for item in items:
        balance = balances_by_product[
            item.product_id
        ]

        quantity_before = balance.quantity
        quantity_after = (
            quantity_before - item.quantity
        )

        balance.quantity = quantity_after

        balance.save(
            update_fields=[
                "quantity",
                "updated_at",
            ]
        )

        StockMovement.objects.create(
            product=item.product,
            order=locked_order,
            movement_type=(
                StockMovement.MovementType.EXIT
            ),
            quantity_delta=-item.quantity,
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            reason=(
                f"Order {locked_order.order_number}"
            ),
            created_by=confirmed_by,
        )

    locked_order.mark_as_confirmed(
        user=confirmed_by
    )

    locked_order.save(
        update_fields=[
            "status",
            "confirmed_by",
            "confirmed_at",
        ]
    )

    return locked_order