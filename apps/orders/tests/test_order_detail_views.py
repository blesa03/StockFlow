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
from apps.inventory.models import InventoryBalance
from apps.inventory.services import (
    register_stock_entry,
)
from apps.orders.models import Order
from apps.orders.services import (
    add_order_item,
    create_order,
)

User = get_user_model()


class OrderDetailViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command(
            "setup_roles",
            verbosity=0,
        )

        cls.operator = User.objects.create_user(
            username="order-editor",
            password="test-password",
        )

        cls.plain_user = User.objects.create_user(
            username="order-detail-plain",
            password="test-password",
        )

        cls.operator.groups.add(
            Group.objects.get(
                name="Operator",
            )
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

        cls.mouse = Product.objects.create(
            sku="MS-001",
            name="Logitech G203",
            category=cls.category,
            price=Decimal("30.00"),
            minimum_stock=4,
        )

        register_stock_entry(
            product=cls.keyboard,
            quantity=10,
            reason="Initial stock",
        )

        register_stock_entry(
            product=cls.mouse,
            quantity=8,
            reason="Initial stock",
        )

        cls.draft_order = create_order(
            customer_name="ACME Corp",
            notes="Draft order",
            created_by=cls.operator,
        )

        cls.keyboard_item = (
            add_order_item(
                order=cls.draft_order,
                product=cls.keyboard,
                quantity=2,
            )
        )

        cls.confirmed_order = (
            create_order(
                customer_name="Locked order",
                created_by=cls.operator,
            )
        )

        cls.confirmed_item = (
            add_order_item(
                order=cls.confirmed_order,
                product=cls.keyboard,
                quantity=1,
            )
        )

        cls.confirmed_order.status = (
            Order.Status.CONFIRMED
        )

        cls.confirmed_order.save(
            update_fields=[
                "status",
            ]
        )

    def test_order_detail_requires_authentication(self):
        response = self.client.get(
            reverse(
                "orders:order_detail",
                args=[
                    self.draft_order.pk
                ],
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_operator_can_view_order_detail(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "orders:order_detail",
                args=[
                    self.draft_order.pk
                ],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            self.draft_order.order_number,
        )

        self.assertContains(
            response,
            "Logitech K120",
        )

    def test_plain_user_cannot_view_order_detail(self):
        self.client.force_login(
            self.plain_user,
        )

        response = self.client.get(
            reverse(
                "orders:order_detail",
                args=[
                    self.draft_order.pk
                ],
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_order_detail_total_is_correct(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "orders:order_detail",
                args=[
                    self.draft_order.pk
                ],
            )
        )

        order = response.context[
            "order"
        ]

        self.assertEqual(
            order.total,
            Decimal("40.00"),
        )

    def test_operator_can_add_order_item(self):
        initial_stock = (
            InventoryBalance.objects
            .get(product=self.mouse)
            .quantity
        )

        self.client.force_login(
            self.operator,
        )

        response = self.client.post(
            reverse(
                "orders:order_detail",
                args=[
                    self.draft_order.pk
                ],
            ),
            {
                "product": self.mouse.pk,
                "quantity": "3",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "orders:order_detail",
                args=[
                    self.draft_order.pk
                ],
            ),
        )

        item = (
            self.draft_order
            .items
            .get(
                product=self.mouse,
            )
        )

        self.assertEqual(
            item.quantity,
            3,
        )

        final_stock = (
            InventoryBalance.objects
            .get(product=self.mouse)
            .quantity
        )

        self.assertEqual(
            final_stock,
            initial_stock,
        )

    def test_adding_same_product_increases_quantity(self):
        self.client.force_login(
            self.operator,
        )

        self.client.post(
            reverse(
                "orders:order_detail",
                args=[
                    self.draft_order.pk
                ],
            ),
            {
                "product": self.keyboard.pk,
                "quantity": "3",
            },
        )

        self.keyboard_item.refresh_from_db()

        self.assertEqual(
            self.keyboard_item.quantity,
            5,
        )

    def test_operator_can_update_item_quantity(self):
        initial_stock = (
            InventoryBalance.objects
            .get(product=self.keyboard)
            .quantity
        )

        self.client.force_login(
            self.operator,
        )

        response = self.client.post(
            reverse(
                "orders:order_item_update",
                args=[
                    self.draft_order.pk,
                    self.keyboard_item.pk,
                ],
            ),
            {
                "quantity": "6",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "orders:order_detail",
                args=[
                    self.draft_order.pk
                ],
            ),
        )

        self.keyboard_item.refresh_from_db()

        self.assertEqual(
            self.keyboard_item.quantity,
            6,
        )

        final_stock = (
            InventoryBalance.objects
            .get(product=self.keyboard)
            .quantity
        )

        self.assertEqual(
            final_stock,
            initial_stock,
        )

    def test_operator_can_remove_order_item(self):
        initial_stock = (
            InventoryBalance.objects
            .get(product=self.keyboard)
            .quantity
        )

        self.client.force_login(
            self.operator,
        )

        response = self.client.post(
            reverse(
                "orders:order_item_remove",
                args=[
                    self.draft_order.pk,
                    self.keyboard_item.pk,
                ],
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "orders:order_detail",
                args=[
                    self.draft_order.pk
                ],
            ),
        )

        self.assertFalse(
            self.draft_order
            .items
            .filter(
                pk=self.keyboard_item.pk,
            )
            .exists()
        )

        final_stock = (
            InventoryBalance.objects
            .get(product=self.keyboard)
            .quantity
        )

        self.assertEqual(
            final_stock,
            initial_stock,
        )

    def test_confirmed_order_cannot_add_items(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.post(
            reverse(
                "orders:order_detail",
                args=[
                    self.confirmed_order.pk
                ],
            ),
            {
                "product": self.mouse.pk,
                "quantity": "1",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "orders:order_detail",
                args=[
                    self.confirmed_order.pk
                ],
            ),
        )

        self.assertFalse(
            self.confirmed_order
            .items
            .filter(
                product=self.mouse,
            )
            .exists()
        )

    def test_confirmed_order_cannot_update_item(self):
        original_quantity = (
            self.confirmed_item.quantity
        )

        self.client.force_login(
            self.operator,
        )

        self.client.post(
            reverse(
                "orders:order_item_update",
                args=[
                    self.confirmed_order.pk,
                    self.confirmed_item.pk,
                ],
            ),
            {
                "quantity": "10",
            },
        )

        self.confirmed_item.refresh_from_db()

        self.assertEqual(
            self.confirmed_item.quantity,
            original_quantity,
        )

    def test_remove_item_only_accepts_post(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "orders:order_item_remove",
                args=[
                    self.draft_order.pk,
                    self.keyboard_item.pk,
                ],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )