from decimal import Decimal

from django.test import TestCase

from apps.catalog.models import Category, Product, Supplier
from apps.inventory.models import StockMovement
from apps.inventory.services import (
    InsufficientStockError,
    InvalidQuantityError,
    adjust_stock,
    register_stock_entry,
    register_stock_exit,
)


class InventoryServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(
            name="Keyboards",
        )

        cls.supplier = Supplier.objects.create(
            name="Logitech",
        )

        cls.product = Product.objects.create(
            sku="KB-001",
            name="Logitech K120",
            category=cls.category,
            supplier=cls.supplier,
            price=Decimal("19.99"),
            minimum_stock=5,
        )

    def test_product_gets_inventory_balance_automatically(self):
        balance = self.product.inventory_balance

        self.assertEqual(balance.quantity, 0)

    def test_stock_entry_increases_balance(self):
        movement = register_stock_entry(
            product=self.product,
            quantity=20,
            reason="Initial stock",
        )

        balance = self.product.inventory_balance
        balance.refresh_from_db()

        self.assertEqual(balance.quantity, 20)

        self.assertEqual(
            movement.movement_type,
            StockMovement.MovementType.ENTRY,
        )

        self.assertEqual(movement.quantity_delta, 20)
        self.assertEqual(movement.quantity_before, 0)
        self.assertEqual(movement.quantity_after, 20)

    def test_stock_exit_reduces_balance(self):
        register_stock_entry(
            product=self.product,
            quantity=20,
            reason="Initial stock",
        )

        movement = register_stock_exit(
            product=self.product,
            quantity=3,
            reason="Manual stock exit",
        )

        balance = self.product.inventory_balance
        balance.refresh_from_db()

        self.assertEqual(balance.quantity, 17)

        self.assertEqual(
            movement.movement_type,
            StockMovement.MovementType.EXIT,
        )

        self.assertEqual(movement.quantity_delta, -3)
        self.assertEqual(movement.quantity_before, 20)
        self.assertEqual(movement.quantity_after, 17)

    def test_stock_exit_cannot_make_balance_negative(self):
        register_stock_entry(
            product=self.product,
            quantity=5,
            reason="Initial stock",
        )

        with self.assertRaises(InsufficientStockError):
            register_stock_exit(
                product=self.product,
                quantity=8,
                reason="Invalid exit",
            )

        balance = self.product.inventory_balance
        balance.refresh_from_db()

        self.assertEqual(balance.quantity, 5)

        self.assertEqual(
            StockMovement.objects.count(),
            1,
        )

    def test_adjust_stock_changes_balance_to_exact_quantity(self):
        register_stock_entry(
            product=self.product,
            quantity=10,
            reason="Initial stock",
        )

        movement = adjust_stock(
            product=self.product,
            new_quantity=4,
            reason="Physical inventory correction",
        )

        balance = self.product.inventory_balance
        balance.refresh_from_db()

        self.assertEqual(balance.quantity, 4)

        self.assertEqual(
            movement.movement_type,
            StockMovement.MovementType.ADJUSTMENT,
        )

        self.assertEqual(movement.quantity_delta, -6)
        self.assertEqual(movement.quantity_before, 10)
        self.assertEqual(movement.quantity_after, 4)

    def test_entry_quantity_must_be_positive(self):
        with self.assertRaises(InvalidQuantityError):
            register_stock_entry(
                product=self.product,
                quantity=0,
                reason="Invalid entry",
            )

        with self.assertRaises(InvalidQuantityError):
            register_stock_entry(
                product=self.product,
                quantity=-1,
                reason="Invalid entry",
            )

    def test_exit_quantity_must_be_positive(self):
        with self.assertRaises(InvalidQuantityError):
            register_stock_exit(
                product=self.product,
                quantity=0,
                reason="Invalid exit",
            )

    def test_adjustment_cannot_set_negative_stock(self):
        with self.assertRaises(InvalidQuantityError):
            adjust_stock(
                product=self.product,
                new_quantity=-1,
                reason="Invalid adjustment",
            )

    def test_adjustment_must_change_current_quantity(self):
        with self.assertRaises(InvalidQuantityError):
            adjust_stock(
                product=self.product,
                new_quantity=0,
                reason="No actual change",
            )