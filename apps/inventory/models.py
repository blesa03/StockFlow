from django.conf import settings
from django.db import models

from apps.catalog.models import Product


class InventoryBalance(models.Model):
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="inventory_balance",
    )

    quantity = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product__name"]  # noqa: RUF012
        constraints = [  # noqa: RUF012
            models.CheckConstraint(
                condition=models.Q(quantity__gte=0),
                name="inventory_balance_quantity_gte_0",
            ),
        ]

    def __str__(self):
        return f"{self.product.sku} - {self.quantity} units"


class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        ENTRY = "ENTRY", "Entry"
        EXIT = "EXIT", "Exit"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )

    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices,
    )

    quantity_delta = models.IntegerField()

    quantity_before = models.PositiveIntegerField()
    quantity_after = models.PositiveIntegerField()

    reason = models.CharField(max_length=255)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="stock_movements",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012
        constraints = [  # noqa: RUF012
            models.CheckConstraint(
                condition=~models.Q(quantity_delta=0),
                name="inventory_movement_delta_not_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_before__gte=0),
                name="inventory_movement_before_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_after__gte=0),
                name="inventory_movement_after_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    quantity_after=models.F("quantity_before")
                    + models.F("quantity_delta")
                ),
                name="inventory_movement_balance_consistent",
            ),
        ]

    def __str__(self):
        sign = "+" if self.quantity_delta > 0 else ""

        return (
            f"{self.product.sku} "
            f"{sign}{self.quantity_delta} "
            f"({self.movement_type})"
        )