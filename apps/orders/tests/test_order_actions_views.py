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
)

User = get_user_model()


class OrderActionViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command(
            "setup_roles",
            verbosity=0,
        )

        cls.operator = User.objects.create_user(
            username="order-actions-operator",
            password="test-password",
        )

        cls.plain_user = User.objects.create_user(
            username="order-actions-plain",
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
            sku="KB-ACT-001",
            name="Action Keyboard",
            category=cls.category,
            price=Decimal("20.00"),
            minimum_stock=2,
        )

        cls.mouse = Product.objects.create(
            sku="MS-ACT-001",
            name="Action Mouse",
            category=cls.category,
            price=Decimal("30.00"),
            minimum_stock=2,
        )

        register_stock_entry(
            product=cls.keyboard,
            quantity=10,
            reason="Initial test stock",
        )

        register_stock_entry(
            product=cls.mouse,
            quantity=8,
            reason="Initial test stock",
        )

    def _create_draft(
        self,
        *,
        customer_name="Test customer",
    ):
        return create_order(
            customer_name=customer_name,
            created_by=self.operator,
        )

    def _stock(self, product):
        return (
            InventoryBalance.objects
            .get(product=product)
            .quantity
        )

    def test_confirm_requires_authentication(self):
        order = self._create_draft()

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=1,
        )

        response = self.client.post(
            reverse(
                "orders:order_confirm",
                args=[order.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.DRAFT,
        )

    def test_plain_user_cannot_confirm_order(self):
        order = self._create_draft()

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=1,
        )

        self.client.force_login(
            self.plain_user,
        )

        response = self.client.post(
            reverse(
                "orders:order_confirm",
                args=[order.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.DRAFT,
        )

    def test_operator_can_confirm_order(self):
        order = self._create_draft(
            customer_name="Confirmation test",
        )

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=3,
        )

        add_order_item(
            order=order,
            product=self.mouse,
            quantity=2,
        )

        self.client.force_login(
            self.operator,
        )

        response = self.client.post(
            reverse(
                "orders:order_confirm",
                args=[order.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "orders:order_detail",
                args=[order.pk],
            ),
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.CONFIRMED,
        )

        self.assertEqual(
            order.confirmed_by,
            self.operator,
        )

        self.assertEqual(
            self._stock(
                self.keyboard
            ),
            7,
        )

        self.assertEqual(
            self._stock(
                self.mouse
            ),
            6,
        )

    def test_confirmation_creates_linked_exit_movements(self):
        order = self._create_draft()

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=3,
        )

        add_order_item(
            order=order,
            product=self.mouse,
            quantity=2,
        )

        self.client.force_login(
            self.operator,
        )

        self.client.post(
            reverse(
                "orders:order_confirm",
                args=[order.pk],
            )
        )

        movements = (
            StockMovement.objects
            .filter(
                order=order,
            )
            .order_by(
                "product__sku"
            )
        )

        self.assertEqual(
            movements.count(),
            2,
        )

        keyboard_movement = (
            movements.get(
                product=self.keyboard,
            )
        )

        mouse_movement = (
            movements.get(
                product=self.mouse,
            )
        )

        self.assertEqual(
            keyboard_movement.movement_type,
            StockMovement.MovementType.EXIT,
        )

        self.assertEqual(
            keyboard_movement.quantity_delta,
            -3,
        )

        self.assertEqual(
            keyboard_movement.quantity_before,
            10,
        )

        self.assertEqual(
            keyboard_movement.quantity_after,
            7,
        )

        self.assertEqual(
            keyboard_movement.created_by,
            self.operator,
        )

        self.assertEqual(
            mouse_movement.quantity_delta,
            -2,
        )

        self.assertEqual(
            mouse_movement.quantity_before,
            8,
        )

        self.assertEqual(
            mouse_movement.quantity_after,
            6,
        )

    def test_insufficient_stock_rolls_back_entire_confirmation(self):
        order = self._create_draft(
            customer_name="Rollback test",
        )

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=4,
        )

        add_order_item(
            order=order,
            product=self.mouse,
            quantity=20,
        )

        keyboard_before = self._stock(
            self.keyboard
        )

        mouse_before = self._stock(
            self.mouse
        )

        self.client.force_login(
            self.operator,
        )

        response = self.client.post(
            reverse(
                "orders:order_confirm",
                args=[order.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "orders:order_detail",
                args=[order.pk],
            ),
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.DRAFT,
        )

        self.assertEqual(
            self._stock(
                self.keyboard
            ),
            keyboard_before,
        )

        self.assertEqual(
            self._stock(
                self.mouse
            ),
            mouse_before,
        )

        self.assertFalse(
            StockMovement.objects.filter(
                order=order,
            ).exists()
        )

    def test_confirmed_order_cannot_be_confirmed_twice(self):
        order = self._create_draft()

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=2,
        )

        self.client.force_login(
            self.operator,
        )

        confirm_url = reverse(
            "orders:order_confirm",
            args=[order.pk],
        )

        self.client.post(
            confirm_url
        )

        stock_after_first_confirmation = (
            self._stock(
                self.keyboard
            )
        )

        movement_count = (
            StockMovement.objects
            .filter(
                order=order,
            )
            .count()
        )

        self.client.post(
            confirm_url
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.CONFIRMED,
        )

        self.assertEqual(
            self._stock(
                self.keyboard
            ),
            stock_after_first_confirmation,
        )

        self.assertEqual(
            StockMovement.objects
            .filter(
                order=order,
            )
            .count(),
            movement_count,
        )

    def test_confirm_only_accepts_post(self):
        order = self._create_draft()

        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "orders:order_confirm",
                args=[order.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

    def test_operator_can_cancel_draft(self):
        order = self._create_draft(
            customer_name="Cancel test",
        )

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=4,
        )

        stock_before = self._stock(
            self.keyboard
        )

        self.client.force_login(
            self.operator,
        )

        response = self.client.post(
            reverse(
                "orders:order_cancel",
                args=[order.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "orders:order_detail",
                args=[order.pk],
            ),
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.CANCELLED,
        )

        self.assertEqual(
            self._stock(
                self.keyboard
            ),
            stock_before,
        )

        self.assertFalse(
            StockMovement.objects.filter(
                order=order,
            ).exists()
        )

    def test_cancelled_order_cannot_be_confirmed(self):
        order = self._create_draft()

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=2,
        )

        self.client.force_login(
            self.operator,
        )

        self.client.post(
            reverse(
                "orders:order_cancel",
                args=[order.pk],
            )
        )

        stock_before = self._stock(
            self.keyboard
        )

        self.client.post(
            reverse(
                "orders:order_confirm",
                args=[order.pk],
            )
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.CANCELLED,
        )

        self.assertEqual(
            self._stock(
                self.keyboard
            ),
            stock_before,
        )

        self.assertFalse(
            StockMovement.objects.filter(
                order=order,
            ).exists()
        )

    def test_cancel_only_accepts_post(self):
        order = self._create_draft()

        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "orders:order_cancel",
                args=[order.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )