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
from apps.inventory.models import StockMovement
from apps.inventory.services import (
    register_stock_entry,
)

User = get_user_model()


class InventoryViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command(
            "setup_roles",
            verbosity=0,
        )

        cls.category = Category.objects.create(
            name="Monitors",
        )

        cls.product = Product.objects.create(
            sku="MN-001",
            name="Samsung Monitor",
            category=cls.category,
            price=Decimal("149.99"),
            minimum_stock=5,
        )

        cls.second_product = Product.objects.create(
            sku="MN-002",
            name="LG Monitor",
            category=cls.category,
            price=Decimal("129.99"),
            minimum_stock=3,
        )

        register_stock_entry(
            product=cls.product,
            quantity=10,
            reason="Initial stock",
        )

        cls.operator = User.objects.create_user(
            username="inventory-operator",
            password="test-password",
        )

        cls.plain_user = User.objects.create_user(
            username="plain-user",
            password="test-password",
        )

        cls.operator.groups.add(
            Group.objects.get(
                name="Operator",
            )
        )

    def test_inventory_requires_authentication(self):
        response = self.client.get(
            reverse(
                "inventory:inventory_list"
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_operator_can_view_inventory(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "inventory:inventory_list"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Samsung Monitor",
        )

    def test_plain_user_cannot_view_inventory(self):
        self.client.force_login(
            self.plain_user,
        )

        response = self.client.get(
            reverse(
                "inventory:inventory_list"
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_stock_status_filter_returns_out_of_stock(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "inventory:inventory_list"
            ),
            {
                "status": "out",
            },
        )

        balances = list(
            response.context[
                "page"
            ].object_list
        )

        products = [
            balance.product
            for balance in balances
        ]

        self.assertIn(
            self.second_product,
            products,
        )

        self.assertNotIn(
            self.product,
            products,
        )

    def test_operator_can_view_movements(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "inventory:movement_list"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Initial stock",
        )

    def test_operator_can_register_stock_entry(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.post(
            reverse(
                "inventory:movement_create"
            ),
            {
                "operation_type": (
                    StockMovement
                    .MovementType
                    .ENTRY
                ),
                "product": (
                    self.second_product.pk
                ),
                "quantity": "12",
                "reason": "Supplier delivery",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "inventory:movement_list"
            ),
        )

        self.second_product\
            .inventory_balance\
            .refresh_from_db()

        self.assertEqual(
            self.second_product
            .inventory_balance
            .quantity,
            12,
        )

        self.assertTrue(
            StockMovement.objects.filter(
                product=self.second_product,
                quantity_delta=12,
                reason="Supplier delivery",
                created_by=self.operator,
            ).exists()
        )

    def test_operator_can_register_stock_exit(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.post(
            reverse(
                "inventory:movement_create"
            ),
            {
                "operation_type": (
                    StockMovement
                    .MovementType
                    .EXIT
                ),
                "product": self.product.pk,
                "quantity": "4",
                "reason": "Damaged stock",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "inventory:movement_list"
            ),
        )

        self.product\
            .inventory_balance\
            .refresh_from_db()

        self.assertEqual(
            self.product
            .inventory_balance
            .quantity,
            6,
        )

    def test_exit_cannot_make_stock_negative(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.post(
            reverse(
                "inventory:movement_create"
            ),
            {
                "operation_type": (
                    StockMovement
                    .MovementType
                    .EXIT
                ),
                "product": self.product.pk,
                "quantity": "50",
                "reason": "Invalid exit",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.context[
                "form"
            ].non_field_errors()
        )

        self.product\
            .inventory_balance\
            .refresh_from_db()

        self.assertEqual(
            self.product
            .inventory_balance
            .quantity,
            10,
        )

    def test_adjustment_sets_exact_quantity(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.post(
            reverse(
                "inventory:movement_create"
            ),
            {
                "operation_type": (
                    StockMovement
                    .MovementType
                    .ADJUSTMENT
                ),
                "product": self.product.pk,
                "quantity": "7",
                "reason": "Physical stock count",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "inventory:movement_list"
            ),
        )

        self.product\
            .inventory_balance\
            .refresh_from_db()

        self.assertEqual(
            self.product
            .inventory_balance
            .quantity,
            7,
        )

    def test_plain_user_cannot_register_movements(self):
        self.client.force_login(
            self.plain_user,
        )

        response = self.client.get(
            reverse(
                "inventory:movement_create"
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )