from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import (
    Category,
    Product,
)
from apps.orders.models import Order
from apps.orders.services import add_order_item

User = get_user_model()


class OrderViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command(
            "setup_roles",
            verbosity=0,
        )

        cls.operator = User.objects.create_user(
            username="orders-operator",
            password="test-password",
        )

        cls.plain_user = User.objects.create_user(
            username="orders-plain",
            password="test-password",
        )

        cls.operator.groups.add(
            Group.objects.get(
                name="Operator",
            )
        )

        cls.category = Category.objects.create(
            name="Keyboards",
        )

        cls.product = Product.objects.create(
            sku="KB-001",
            name="Logitech K120",
            category=cls.category,
            price=Decimal("20.00"),
            minimum_stock=5,
        )

        cls.draft_order = Order.objects.create(
            customer_name="ACME Corp",
            status=Order.Status.DRAFT,
            created_by=cls.operator,
        )

        cls.confirmed_order = Order.objects.create(
            customer_name="Northwind",
            status=Order.Status.CONFIRMED,
            created_by=cls.operator,
        )

        add_order_item(
            order=cls.draft_order,
            product=cls.product,
            quantity=2,
        )

    def test_order_list_requires_authentication(self):
        response = self.client.get(
            reverse(
                "orders:order_list"
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_operator_can_view_orders(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "orders:order_list"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "ACME Corp",
        )

        self.assertContains(
            response,
            "Northwind",
        )

    def test_plain_user_cannot_view_orders(self):
        self.client.force_login(
            self.plain_user,
        )

        response = self.client.get(
            reverse(
                "orders:order_list"
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_order_search_filters_by_customer(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "orders:order_list"
            ),
            {
                "q": "ACME",
            },
        )

        orders = list(
            response.context[
                "page"
            ].object_list
        )

        self.assertIn(
            self.draft_order,
            orders,
        )

        self.assertNotIn(
            self.confirmed_order,
            orders,
        )

    def test_status_filter_returns_drafts(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "orders:order_list"
            ),
            {
                "status": Order.Status.DRAFT,
            },
        )

        orders = list(
            response.context[
                "page"
            ].object_list
        )

        self.assertIn(
            self.draft_order,
            orders,
        )

        self.assertNotIn(
            self.confirmed_order,
            orders,
        )

    def test_order_list_includes_item_count_and_total(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "orders:order_list"
            )
        )

        order = next(
            order
            for order in response.context[
                "page"
            ].object_list
            if order.pk == self.draft_order.pk
        )

        self.assertEqual(
            order.item_count,
            1,
        )

        self.assertEqual(
            order.total_amount,
            Decimal("40.00"),
        )

    def test_operator_can_access_order_create(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "orders:order_create"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_operator_can_create_draft_order(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.post(
            reverse(
                "orders:order_create"
            ),
            {
                "customer_name": "Contoso",
                "notes": "Priority delivery",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "orders:order_list"
            ),
        )

        order = Order.objects.get(
            customer_name="Contoso",
        )

        self.assertEqual(
            order.status,
            Order.Status.DRAFT,
        )

        self.assertEqual(
            order.created_by,
            self.operator,
        )

        self.assertEqual(
            order.items.count(),
            0,
        )

    def test_new_order_does_not_change_inventory(self):
        initial_quantity = (
            self.product
            .inventory_balance
            .quantity
        )

        self.client.force_login(
            self.operator,
        )

        self.client.post(
            reverse(
                "orders:order_create"
            ),
            {
                "customer_name": "Inventory Test",
                "notes": "",
            },
        )

        self.product\
            .inventory_balance\
            .refresh_from_db()

        self.assertEqual(
            self.product
            .inventory_balance
            .quantity,
            initial_quantity,
        )

    def test_plain_user_cannot_create_orders(self):
        self.client.force_login(
            self.plain_user,
        )

        response = self.client.get(
            reverse(
                "orders:order_create"
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )