from django.db import transaction

from apps.catalog.models import Product

from .models import InventoryBalance, StockMovement


class InventoryError(Exception):
    """Base exception for inventory operations."""


class InvalidQuantityError(InventoryError):
    """Raised when an inventory quantity is invalid."""


class InsufficientStockError(InventoryError):
    """Raised when an exit would leave the stock below zero."""


def _validate_reason(reason):
    if not reason or not reason.strip():
        raise ValueError("A reason is required for stock movements.")

    return reason.strip()


def _validate_positive_quantity(quantity):
    if not isinstance(quantity, int) or isinstance(quantity, bool):
        raise InvalidQuantityError("Quantity must be an integer.")

    if quantity <= 0:
        raise InvalidQuantityError(
            "Quantity must be greater than zero."
        )


def _get_locked_balance(product):
    return InventoryBalance.objects.select_for_update().get(
        product=product,
    )


def _create_movement(
    *,
    product,
    movement_type,
    quantity_delta,
    quantity_before,
    quantity_after,
    reason,
    created_by=None,
):
    return StockMovement.objects.create(
        product=product,
        movement_type=movement_type,
        quantity_delta=quantity_delta,
        quantity_before=quantity_before,
        quantity_after=quantity_after,
        reason=reason,
        created_by=created_by,
    )


@transaction.atomic
def register_stock_entry(
    *,
    product: Product,
    quantity: int,
    reason: str,
    created_by=None,
):
    _validate_positive_quantity(quantity)
    reason = _validate_reason(reason)

    balance = _get_locked_balance(product)

    quantity_before = balance.quantity
    quantity_after = quantity_before + quantity

    balance.quantity = quantity_after
    balance.save(update_fields=["quantity", "updated_at"])

    return _create_movement(
        product=product,
        movement_type=StockMovement.MovementType.ENTRY,
        quantity_delta=quantity,
        quantity_before=quantity_before,
        quantity_after=quantity_after,
        reason=reason,
        created_by=created_by,
    )


@transaction.atomic
def register_stock_exit(
    *,
    product: Product,
    quantity: int,
    reason: str,
    created_by=None,
):
    _validate_positive_quantity(quantity)
    reason = _validate_reason(reason)

    balance = _get_locked_balance(product)

    if balance.quantity < quantity:
        raise InsufficientStockError(
            f"Insufficient stock for {product.sku}. "
            f"Available: {balance.quantity}. "
            f"Requested: {quantity}."
        )

    quantity_before = balance.quantity
    quantity_after = quantity_before - quantity

    balance.quantity = quantity_after
    balance.save(update_fields=["quantity", "updated_at"])

    return _create_movement(
        product=product,
        movement_type=StockMovement.MovementType.EXIT,
        quantity_delta=-quantity,
        quantity_before=quantity_before,
        quantity_after=quantity_after,
        reason=reason,
        created_by=created_by,
    )


@transaction.atomic
def adjust_stock(
    *,
    product: Product,
    new_quantity: int,
    reason: str,
    created_by=None,
):
    if not isinstance(new_quantity, int) or isinstance(
        new_quantity,
        bool,
    ):
        raise InvalidQuantityError(
            "New quantity must be an integer."
        )

    if new_quantity < 0:
        raise InvalidQuantityError(
            "New quantity cannot be negative."
        )

    reason = _validate_reason(reason)

    balance = _get_locked_balance(product)

    quantity_before = balance.quantity

    if new_quantity == quantity_before:
        raise InvalidQuantityError(
            "New quantity must be different from current stock."
        )

    quantity_delta = new_quantity - quantity_before

    balance.quantity = new_quantity
    balance.save(update_fields=["quantity", "updated_at"])

    return _create_movement(
        product=product,
        movement_type=StockMovement.MovementType.ADJUSTMENT,
        quantity_delta=quantity_delta,
        quantity_before=quantity_before,
        quantity_after=new_quantity,
        reason=reason,
        created_by=created_by,
    )