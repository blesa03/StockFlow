from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import Category, Product
from apps.inventory.services import register_stock_entry
from apps.orders.services import (
    add_order_item,
    create_order,
)

User = get_user_model()


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="operator",
            password="test-password",
        )

        cls.category = Category.objects.create(
            name="Peripherals",
        )

        cls.keyboard = Product.objects.create(
            sku="KB-001",
            name="Logitech K120",
            category=cls.category,
            price=Decimal("20.00"),
            minimum_stock=5,
        )

        cls.monitor = Product.objects.create(
            sku="MN-001",
            name="Samsung Monitor",
            category=cls.category,
            price=Decimal("100.00"),
            minimum_stock=2,
        )

        register_stock_entry(
            product=cls.keyboard,
            quantity=10,
            reason="Initial stock",
        )

        cls.order = create_order(
            customer_name="Acme SL",
        )

        add_order_item(
            order=cls.order,
            product=cls.keyboard,
            quantity=2,
        )

    def setUp(self):
        self.client.force_login(
            self.user,
        )

    def test_dashboard_is_available_to_authenticated_user(self):
        response = self.client.get(
            reverse("dashboard"),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_dashboard_contains_real_metrics(self):
        response = self.client.get(
            reverse("dashboard"),
        )

        metrics = response.context["metrics"]

        self.assertEqual(
            metrics["products"],
            2,
        )

        self.assertEqual(
            metrics["low_stock"],
            1,
        )

        self.assertEqual(
            metrics["draft_orders"],
            1,
        )

        self.assertEqual(
            metrics["movements_today"],
            1,
        )

    def test_out_of_stock_product_requires_attention(self):
        response = self.client.get(
            reverse("dashboard"),
        )

        products = list(
            response.context["attention_products"]
        )

        self.assertIn(
            self.monitor,
            products,
        )

    def test_product_with_healthy_stock_does_not_require_attention(self):
        response = self.client.get(
            reverse("dashboard"),
        )

        products = list(
            response.context["attention_products"]
        )

        self.assertNotIn(
            self.keyboard,
            products,
        )

    def test_recent_movements_are_displayed(self):
        response = self.client.get(
            reverse("dashboard"),
        )

        movements = list(
            response.context["recent_movements"]
        )

        self.assertEqual(
            len(movements),
            1,
        )

        self.assertEqual(
            movements[0].product,
            self.keyboard,
        )