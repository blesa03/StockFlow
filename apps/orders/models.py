from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.catalog.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"

    order_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )

    customer_name = models.CharField(max_length=200)

    notes = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_orders",
        null=True,
        blank=True,
    )

    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="confirmed_orders",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012

    def save(self, *args, **kwargs):
        creating = self._state.adding

        super().save(*args, **kwargs)

        if creating and not self.order_number:
            self.order_number = f"ORD-{self.pk:06d}"

            type(self).objects.filter(
                pk=self.pk,
            ).update(
                order_number=self.order_number,
            )

    @property
    def total(self):
        return sum(
            (
                item.line_total
                for item in self.items.all()
            ),
            Decimal("0.00"),
        )

    @property
    def is_editable(self):
        return self.status == self.Status.DRAFT

    def mark_as_confirmed(self, user=None):
        self.status = self.Status.CONFIRMED
        self.confirmed_by = user
        self.confirmed_at = timezone.now()

    def __str__(self):
        return self.order_number or f"Order #{self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
    )

    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    class Meta:
        ordering = ["id"]  # noqa: RUF012
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["order", "product"],
                name="orders_item_unique_product_per_order",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="orders_item_quantity_gt_0",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=0),
                name="orders_item_unit_price_gte_0",
            ),
        ]

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return (
            f"{self.order} - "
            f"{self.product.sku} x{self.quantity}"
        )