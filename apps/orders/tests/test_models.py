from decimal import Decimal

from django.test import TestCase

from apps.catalog.models import Category, Product
from apps.orders.models import Order, OrderItem


class OrderModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(
            name="Keyboards",
        )

        cls.product = Product.objects.create(
            sku="KB-001",
            name="Logitech K120",
            category=cls.category,
            price=Decimal("19.99"),
            minimum_stock=5,
        )

    def test_order_number_is_generated(self):
        order = Order.objects.create(
            customer_name="Acme SL",
        )

        self.assertEqual(
            order.order_number,
            f"ORD-{order.pk:06d}",
        )

    def test_new_order_is_draft(self):
        order = Order.objects.create(
            customer_name="Acme SL",
        )

        self.assertEqual(
            order.status,
            Order.Status.DRAFT,
        )

    def test_order_string_representation_is_order_number(self):
        order = Order.objects.create(
            customer_name="Acme SL",
        )

        self.assertEqual(
            str(order),
            order.order_number,
        )

    def test_order_item_total_is_calculated(self):
        order = Order.objects.create(
            customer_name="Acme SL",
        )

        item = OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=3,
            unit_price=Decimal("19.99"),
        )

        self.assertEqual(
            item.line_total,
            Decimal("59.97"),
        )

    def test_order_total_is_sum_of_items(self):
        second_product = Product.objects.create(
            sku="KB-002",
            name="Another Keyboard",
            category=self.category,
            price=Decimal("10.00"),
        )

        order = Order.objects.create(
            customer_name="Acme SL",
        )

        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=2,
            unit_price=Decimal("19.99"),
        )

        OrderItem.objects.create(
            order=order,
            product=second_product,
            quantity=1,
            unit_price=Decimal("10.00"),
        )

        self.assertEqual(
            order.total,
            Decimal("49.98"),
        )