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
from apps.inventory.models import (
    InventoryBalance,
    StockMovement,
)
from apps.inventory.services import (
    register_stock_entry,
)
from apps.orders.models import Order
from apps.orders.services import (
    add_order_item,
    create_order,
    update_order_item_quantity,
)

User = get_user_model()


class OrderHtmxViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command(
            "setup_roles",
            verbosity=0,
        )

        cls.operator = User.objects.create_user(
            username="htmx-operator",
            password="test-password",
        )

        cls.operator.groups.add(
            Group.objects.get(
                name="Operator",
            )
        )

        cls.category = Category.objects.create(
            name="HTMX peripherals",
        )

        cls.keyboard = Product.objects.create(
            sku="HT-KB-001",
            name="HTMX Keyboard",
            category=cls.category,
            price=Decimal("20.00"),
            minimum_stock=2,
        )

        cls.mouse = Product.objects.create(
            sku="HT-MS-001",
            name="HTMX Mouse",
            category=cls.category,
            price=Decimal("30.00"),
            minimum_stock=2,
        )

        register_stock_entry(
            product=cls.keyboard,
            quantity=10,
            reason="Initial HTMX stock",
        )

        register_stock_entry(
            product=cls.mouse,
            quantity=8,
            reason="Initial HTMX stock",
        )

    def setUp(self):
        self.order = create_order(
            customer_name="HTMX Customer",
            created_by=self.operator,
        )

        self.item = add_order_item(
            order=self.order,
            product=self.keyboard,
            quantity=2,
        )

        self.client.force_login(
            self.operator,
        )

    def _stock(self, product):
        return (
            InventoryBalance.objects
            .get(product=product)
            .quantity
        )

    def _htmx_post(
        self,
        url,
        data=None,
    ):
        return self.client.post(
            url,
            data or {},
            HTTP_HX_REQUEST="true",
        )

    def test_htmx_add_item_returns_workspace_partial(self):
        stock_before = self._stock(
            self.mouse
        )

        response = self._htmx_post(
            reverse(
                "orders:order_detail",
                args=[self.order.pk],
            ),
            {
                "product": self.mouse.pk,
                "quantity": "3",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            (
                "orders/partials/"
                "order_workspace.html"
            ),
        )

        self.assertContains(
            response,
            'id="order-workspace"',
        )

        self.assertContains(
            response,
            "HTMX Mouse",
        )

        self.assertNotContains(
            response,
            "<html",
        )

        self.assertTrue(
            self.order.items.filter(
                product=self.mouse,
                quantity=3,
            ).exists()
        )

        self.assertEqual(
            self._stock(
                self.mouse
            ),
            stock_before,
        )

    def test_htmx_update_quantity_returns_updated_workspace(self):
        stock_before = self._stock(
            self.keyboard
        )

        response = self._htmx_post(
            reverse(
                "orders:order_item_update",
                args=[
                    self.order.pk,
                    self.item.pk,
                ],
            ),
            {
                "quantity": "5",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.item.refresh_from_db()

        self.assertEqual(
            self.item.quantity,
            5,
        )

        self.assertEqual(
            self._stock(
                self.keyboard
            ),
            stock_before,
        )

        self.assertContains(
            response,
            "Order quantity updated.",
        )

    def test_htmx_remove_item_returns_updated_workspace(self):
        response = self._htmx_post(
            reverse(
                "orders:order_item_remove",
                args=[
                    self.order.pk,
                    self.item.pk,
                ],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            self.order.items.filter(
                pk=self.item.pk,
            ).exists()
        )

        self.assertContains(
            response,
            "Product removed from order.",
        )

    def test_htmx_confirmation_updates_status_and_stock(self):
        stock_before = self._stock(
            self.keyboard
        )

        response = self._htmx_post(
            reverse(
                "orders:order_confirm",
                args=[self.order.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.CONFIRMED,
        )

        self.assertEqual(
            self._stock(
                self.keyboard
            ),
            stock_before - 2,
        )

        self.assertEqual(
            StockMovement.objects.filter(
                order=self.order,
            ).count(),
            1,
        )

        self.assertContains(
            response,
            "Confirmed order",
        )

    def test_htmx_failed_confirmation_keeps_full_rollback(self):
        update_order_item_quantity(
            item=self.item,
            quantity=50,
        )

        stock_before = self._stock(
            self.keyboard
        )

        response = self._htmx_post(
            reverse(
                "orders:order_confirm",
                args=[self.order.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.DRAFT,
        )

        self.assertEqual(
            self._stock(
                self.keyboard
            ),
            stock_before,
        )

        self.assertFalse(
            StockMovement.objects.filter(
                order=self.order,
            ).exists()
        )

        self.assertEqual(
            response.context[
                "feedback_level"
            ],
            "error",
        )

        self.assertTrue(
            response.context[
                "feedback"
            ]
        )

    def test_htmx_cancel_updates_workspace_without_stock_change(self):
        stock_before = self._stock(
            self.keyboard
        )

        response = self._htmx_post(
            reverse(
                "orders:order_cancel",
                args=[self.order.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.CANCELLED,
        )

        self.assertEqual(
            self._stock(
                self.keyboard
            ),
            stock_before,
        )

        self.assertContains(
            response,
            "Cancelled order",
        )