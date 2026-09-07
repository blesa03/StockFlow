from decimal import Decimal

from django.test import TestCase

from apps.catalog.models import Category, Product
from apps.inventory.models import StockMovement
from apps.inventory.services import register_stock_entry
from apps.orders.models import Order
from apps.orders.services import (
    EmptyOrderError,
    InsufficientOrderStockError,
    InvalidOrderItemError,
    InvalidOrderStateError,
    add_order_item,
    cancel_order,
    confirm_order,
    create_order,
    remove_order_item,
    update_order_item_quantity,
)


class OrderServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
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

    def test_create_order_creates_draft(self):
        order = create_order(
            customer_name="Acme SL",
        )

        self.assertEqual(
            order.status,
            Order.Status.DRAFT,
        )

        self.assertEqual(
            order.customer_name,
            "Acme SL",
        )

    def test_add_order_item_uses_current_product_price(self):
        order = create_order(
            customer_name="Acme SL",
        )

        item = add_order_item(
            order=order,
            product=self.keyboard,
            quantity=2,
        )

        self.assertEqual(
            item.unit_price,
            Decimal("20.00"),
        )

    def test_adding_same_product_increases_quantity(self):
        order = create_order(
            customer_name="Acme SL",
        )

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=2,
        )

        item = add_order_item(
            order=order,
            product=self.keyboard,
            quantity=3,
        )

        self.assertEqual(
            item.quantity,
            5,
        )

        self.assertEqual(
            order.items.count(),
            1,
        )

    def test_order_item_quantity_can_be_updated(self):
        order = create_order(
            customer_name="Acme SL",
        )

        item = add_order_item(
            order=order,
            product=self.keyboard,
            quantity=2,
        )

        item = update_order_item_quantity(
            item=item,
            quantity=5,
        )

        self.assertEqual(
            item.quantity,
            5,
        )

    def test_order_item_can_be_removed(self):
        order = create_order(
            customer_name="Acme SL",
        )

        item = add_order_item(
            order=order,
            product=self.keyboard,
            quantity=2,
        )

        remove_order_item(
            item=item,
        )

        self.assertEqual(
            order.items.count(),
            0,
        )

    def test_order_item_quantity_must_be_positive(self):
        order = create_order(
            customer_name="Acme SL",
        )

        with self.assertRaises(
            InvalidOrderItemError
        ):
            add_order_item(
                order=order,
                product=self.keyboard,
                quantity=0,
            )

    def test_draft_order_does_not_modify_inventory(self):
        order = create_order(
            customer_name="Acme SL",
        )

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=5,
        )

        balance = self.keyboard.inventory_balance
        balance.refresh_from_db()

        self.assertEqual(
            balance.quantity,
            0,
        )

    def test_order_with_sufficient_stock_can_be_confirmed(self):
        register_stock_entry(
            product=self.keyboard,
            quantity=10,
            reason="Initial stock",
        )

        register_stock_entry(
            product=self.monitor,
            quantity=5,
            reason="Initial stock",
        )

        order = create_order(
            customer_name="Acme SL",
        )

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=3,
        )

        add_order_item(
            order=order,
            product=self.monitor,
            quantity=2,
        )

        confirmed_order = confirm_order(
            order=order,
        )

        self.keyboard.inventory_balance.refresh_from_db()
        self.monitor.inventory_balance.refresh_from_db()

        self.assertEqual(
            confirmed_order.status,
            Order.Status.CONFIRMED,
        )

        self.assertEqual(
            self.keyboard.inventory_balance.quantity,
            7,
        )

        self.assertEqual(
            self.monitor.inventory_balance.quantity,
            3,
        )

        self.assertEqual(
            StockMovement.objects.filter(
                order=confirmed_order,
            ).count(),
            2,
        )

    def test_confirmation_creates_order_linked_movements(self):
        register_stock_entry(
            product=self.keyboard,
            quantity=10,
            reason="Initial stock",
        )

        order = create_order(
            customer_name="Acme SL",
        )

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=3,
        )

        confirmed_order = confirm_order(
            order=order,
        )

        movement = StockMovement.objects.get(
            order=confirmed_order,
        )

        self.assertEqual(
            movement.movement_type,
            StockMovement.MovementType.EXIT,
        )

        self.assertEqual(
            movement.quantity_delta,
            -3,
        )

        self.assertEqual(
            movement.quantity_before,
            10,
        )

        self.assertEqual(
            movement.quantity_after,
            7,
        )

    def test_insufficient_stock_rolls_back_entire_order(self):
        register_stock_entry(
            product=self.keyboard,
            quantity=10,
            reason="Initial stock",
        )

        register_stock_entry(
            product=self.monitor,
            quantity=1,
            reason="Initial stock",
        )

        order = create_order(
            customer_name="Acme SL",
        )

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=3,
        )

        add_order_item(
            order=order,
            product=self.monitor,
            quantity=2,
        )

        with self.assertRaises(
            InsufficientOrderStockError
        ):
            confirm_order(
                order=order,
            )

        order.refresh_from_db()

        self.keyboard.inventory_balance.refresh_from_db()
        self.monitor.inventory_balance.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.DRAFT,
        )

        self.assertEqual(
            self.keyboard.inventory_balance.quantity,
            10,
        )

        self.assertEqual(
            self.monitor.inventory_balance.quantity,
            1,
        )

        self.assertEqual(
            StockMovement.objects.filter(
                order=order,
            ).count(),
            0,
        )

    def test_insufficient_stock_exception_contains_shortages(self):
        register_stock_entry(
            product=self.monitor,
            quantity=1,
            reason="Initial stock",
        )

        order = create_order(
            customer_name="Acme SL",
        )

        add_order_item(
            order=order,
            product=self.monitor,
            quantity=3,
        )

        with self.assertRaises(
            InsufficientOrderStockError
        ) as context:
            confirm_order(
                order=order,
            )

        shortages = context.exception.shortages

        self.assertEqual(
            len(shortages),
            1,
        )

        self.assertEqual(
            shortages[0]["sku"],
            "MN-001",
        )

        self.assertEqual(
            shortages[0]["requested"],
            3,
        )

        self.assertEqual(
            shortages[0]["available"],
            1,
        )

    def test_empty_order_cannot_be_confirmed(self):
        order = create_order(
            customer_name="Acme SL",
        )

        with self.assertRaises(
            EmptyOrderError
        ):
            confirm_order(
                order=order,
            )

    def test_confirmed_order_cannot_be_confirmed_again(self):
        register_stock_entry(
            product=self.keyboard,
            quantity=10,
            reason="Initial stock",
        )

        order = create_order(
            customer_name="Acme SL",
        )

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=3,
        )

        confirm_order(
            order=order,
        )

        with self.assertRaises(
            InvalidOrderStateError
        ):
            confirm_order(
                order=order,
            )

        self.keyboard.inventory_balance.refresh_from_db()

        self.assertEqual(
            self.keyboard.inventory_balance.quantity,
            7,
        )

    def test_confirmed_order_cannot_be_modified(self):
        register_stock_entry(
            product=self.keyboard,
            quantity=10,
            reason="Initial stock",
        )

        order = create_order(
            customer_name="Acme SL",
        )

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=2,
        )

        confirm_order(
            order=order,
        )

        with self.assertRaises(
            InvalidOrderStateError
        ):
            add_order_item(
                order=order,
                product=self.monitor,
                quantity=1,
            )

    def test_draft_order_can_be_cancelled(self):
        order = create_order(
            customer_name="Acme SL",
        )

        cancelled_order = cancel_order(
            order=order,
        )

        self.assertEqual(
            cancelled_order.status,
            Order.Status.CANCELLED,
        )

    def test_confirmed_order_cannot_be_cancelled(self):
        register_stock_entry(
            product=self.keyboard,
            quantity=10,
            reason="Initial stock",
        )

        order = create_order(
            customer_name="Acme SL",
        )

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=2,
        )

        order = confirm_order(
            order=order,
        )

        with self.assertRaises(
            InvalidOrderStateError
        ):
            cancel_order(
                order=order,
            )