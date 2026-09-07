from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import (
    Category,
    Product,
    Supplier,
)
from apps.inventory.services import register_stock_entry

User = get_user_model()


class ProductViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command(
            "setup_roles",
            verbosity=0,
        )

        cls.category = Category.objects.create(
            name="Keyboards",
        )

        cls.supplier = Supplier.objects.create(
            name="Logitech",
        )

        cls.healthy_product = Product.objects.create(
            sku="KB-001",
            name="Logitech K120",
            category=cls.category,
            supplier=cls.supplier,
            price=Decimal("20.00"),
            minimum_stock=5,
        )

        cls.low_product = Product.objects.create(
            sku="KB-002",
            name="Low Stock Keyboard",
            category=cls.category,
            supplier=cls.supplier,
            price=Decimal("30.00"),
            minimum_stock=5,
        )

        cls.out_product = Product.objects.create(
            sku="KB-003",
            name="Out of Stock Keyboard",
            category=cls.category,
            supplier=cls.supplier,
            price=Decimal("40.00"),
            minimum_stock=3,
        )

        register_stock_entry(
            product=cls.healthy_product,
            quantity=10,
            reason="Initial stock",
        )

        register_stock_entry(
            product=cls.low_product,
            quantity=3,
            reason="Initial stock",
        )

        cls.operator = User.objects.create_user(
            username="operator",
            password="test-password",
        )

        cls.manager = User.objects.create_user(
            username="manager",
            password="test-password",
        )

        cls.operator.groups.add(
            Group.objects.get(
                name="Operator",
            )
        )

        cls.manager.groups.add(
            Group.objects.get(
                name="Manager",
            )
        )

    def test_product_list_requires_authentication(self):
        response = self.client.get(
            reverse(
                "catalog:product_list"
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_operator_can_view_product_list(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "catalog:product_list"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_search_filters_products(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "catalog:product_list"
            ),
            {
                "q": "K120",
            },
        )

        products = list(
            response.context["page"].object_list
        )

        self.assertEqual(
            products,
            [self.healthy_product],
        )

    def test_low_stock_filter_returns_low_products(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "catalog:product_list"
            ),
            {
                "status": "low",
            },
        )

        products = list(
            response.context["page"].object_list
        )

        self.assertIn(
            self.low_product,
            products,
        )

        self.assertNotIn(
            self.healthy_product,
            products,
        )

        self.assertNotIn(
            self.out_product,
            products,
        )

    def test_out_of_stock_filter_returns_zero_stock_products(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "catalog:product_list"
            ),
            {
                "status": "out",
            },
        )

        products = list(
            response.context["page"].object_list
        )

        self.assertIn(
            self.out_product,
            products,
        )

    def test_operator_cannot_create_products(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "catalog:product_create"
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_manager_can_access_product_create(self):
        self.client.force_login(
            self.manager,
        )

        response = self.client.get(
            reverse(
                "catalog:product_create"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_manager_can_create_product(self):
        self.client.force_login(
            self.manager,
        )

        response = self.client.post(
            reverse(
                "catalog:product_create"
            ),
            {
                "sku": " kb-010 ",
                "name": "New Keyboard",
                "category": self.category.pk,
                "supplier": self.supplier.pk,
                "price": "49.99",
                "minimum_stock": "4",
                "active": "on",
            },
        )

        product = Product.objects.get(
            sku="KB-010",
        )

        self.assertRedirects(
            response,
            reverse(
                "catalog:product_detail",
                args=[product.pk],
            ),
        )

        self.assertEqual(
            product.inventory_balance.quantity,
            0,
        )

    def test_operator_can_view_product_detail(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "catalog:product_detail",
                args=[
                    self.healthy_product.pk
                ],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context[
                "product"
            ].stock_quantity,
            10,
        )