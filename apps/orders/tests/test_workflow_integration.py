from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import User
from apps.catalog.models import Category, Product
from apps.inventory.models import (
    InventoryBalance,
    StockMovement,
)
from apps.inventory.services import (
    InventoryError,
    register_stock_entry,
)
from apps.orders.models import Order
from apps.orders.services import (
    OrderError,
    add_order_item,
    cancel_order,
    confirm_order,
    create_order,
    remove_order_item,
    update_order_item_quantity,
)


class OrderWorkflowIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="workflow-user",
            password="test-password",
        )

        cls.category = Category.objects.create(
            name="Workflow products",
        )

        cls.keyboard = Product.objects.create(
            sku="WF-KB-001",
            name="Workflow Keyboard",
            category=cls.category,
            price=Decimal("20.00"),
            minimum_stock=2,
        )

        cls.mouse = Product.objects.create(
            sku="WF-MS-001",
            name="Workflow Mouse",
            category=cls.category,
            price=Decimal("30.00"),
            minimum_stock=2,
        )

        register_stock_entry(
            product=cls.keyboard,
            quantity=10,
            reason="Initial workflow stock",
        )

        register_stock_entry(
            product=cls.mouse,
            quantity=8,
            reason="Initial workflow stock",
        )

    def _stock(self, product):
        return (
            InventoryBalance.objects
            .get(product=product)
            .quantity
        )

    def _create_order(
        self,
        customer="Workflow Customer",
    ):
        return create_order(
            customer_name=customer,
            created_by=self.user,
        )

    def test_complete_order_workflow(self):
        order = self._create_order()

        keyboard_stock = self._stock(
            self.keyboard
        )

        mouse_stock = self._stock(
            self.mouse
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

        # Draft editing must not affect inventory.
        self.assertEqual(
            self._stock(self.keyboard),
            keyboard_stock,
        )

        self.assertEqual(
            self._stock(self.mouse),
            mouse_stock,
        )

        confirm_order(
            order=order,
            confirmed_by=self.user,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.CONFIRMED,
        )

        self.assertEqual(
            order.confirmed_by,
            self.user,
        )

        self.assertEqual(
            self._stock(self.keyboard),
            keyboard_stock - 3,
        )

        self.assertEqual(
            self._stock(self.mouse),
            mouse_stock - 2,
        )

        movements = (
            StockMovement.objects
            .filter(order=order)
        )

        self.assertEqual(
            movements.count(),
            2,
        )

        self.assertTrue(
            all(
                movement.movement_type
                == StockMovement.MovementType.EXIT
                for movement in movements
            )
        )

    def test_shortage_rolls_back_every_product(self):
        order = self._create_order(
            "Rollback Customer"
        )

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=4,
        )

        add_order_item(
            order=order,
            product=self.mouse,
            quantity=100,
        )

        keyboard_before = self._stock(
            self.keyboard
        )

        mouse_before = self._stock(
            self.mouse
        )

        with self.assertRaises(
            (
                OrderError,
                InventoryError,
            )
        ):
            confirm_order(
                order=order,
                confirmed_by=self.user,
            )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.DRAFT,
        )

        self.assertEqual(
            self._stock(self.keyboard),
            keyboard_before,
        )

        self.assertEqual(
            self._stock(self.mouse),
            mouse_before,
        )

        self.assertFalse(
            StockMovement.objects.filter(
                order=order
            ).exists()
        )

    def test_draft_can_request_more_than_available_stock(self):
        order = self._create_order()

        item = add_order_item(
            order=order,
            product=self.keyboard,
            quantity=50,
        )

        self.assertEqual(
            item.quantity,
            50,
        )

        self.assertEqual(
            self._stock(self.keyboard),
            10,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.DRAFT,
        )

    def test_confirmed_order_cannot_be_modified(self):
        order = self._create_order()

        item = add_order_item(
            order=order,
            product=self.keyboard,
            quantity=2,
        )

        confirm_order(
            order=order,
            confirmed_by=self.user,
        )

        with self.assertRaises(OrderError):
            add_order_item(
                order=order,
                product=self.mouse,
                quantity=1,
            )

        with self.assertRaises(OrderError):
            update_order_item_quantity(
                item=item,
                quantity=5,
            )

        with self.assertRaises(OrderError):
            remove_order_item(
                item=item,
            )

    def test_cancelled_order_cannot_be_modified(self):
        order = self._create_order()

        item = add_order_item(
            order=order,
            product=self.keyboard,
            quantity=2,
        )

        stock_before = self._stock(
            self.keyboard
        )

        cancel_order(
            order=order,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.CANCELLED,
        )

        self.assertEqual(
            self._stock(self.keyboard),
            stock_before,
        )

        with self.assertRaises(OrderError):
            update_order_item_quantity(
                item=item,
                quantity=10,
            )

        with self.assertRaises(OrderError):
            remove_order_item(
                item=item,
            )

    def test_order_cannot_be_confirmed_twice(self):
        order = self._create_order()

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=2,
        )

        confirm_order(
            order=order,
            confirmed_by=self.user,
        )

        stock_after_first = self._stock(
            self.keyboard
        )

        movement_count = (
            StockMovement.objects
            .filter(order=order)
            .count()
        )

        with self.assertRaises(
            (
                OrderError,
                InventoryError,
            )
        ):
            confirm_order(
                order=order,
                confirmed_by=self.user,
            )

        self.assertEqual(
            self._stock(self.keyboard),
            stock_after_first,
        )

        self.assertEqual(
            StockMovement.objects
            .filter(order=order)
            .count(),
            movement_count,
        )

    def test_order_item_keeps_price_snapshot(self):
        order = self._create_order()

        item = add_order_item(
            order=order,
            product=self.keyboard,
            quantity=2,
        )

        self.assertEqual(
            item.unit_price,
            Decimal("20.00"),
        )

        self.keyboard.price = Decimal(
            "99.00"
        )

        self.keyboard.save(
            update_fields=[
                "price",
            ]
        )

        item.refresh_from_db()

        self.assertEqual(
            item.unit_price,
            Decimal("20.00"),
        )

        self.assertEqual(
            item.line_total,
            Decimal("40.00"),
        )