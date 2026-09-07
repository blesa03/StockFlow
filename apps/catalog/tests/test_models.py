from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from apps.catalog.models import Category, Product, Supplier


class CategoryModelTests(TestCase):
    def test_string_representation_returns_name(self):
        category = Category(name="Keyboards")

        self.assertEqual(str(category), "Keyboards")

    def test_category_name_must_be_unique(self):
        Category.objects.create(name="Keyboards")

        with self.assertRaises(IntegrityError), transaction.atomic():
            Category.objects.create(name="Keyboards")


class SupplierModelTests(TestCase):
    def test_string_representation_returns_name(self):
        supplier = Supplier(name="Logitech")

        self.assertEqual(str(supplier), "Logitech")


class ProductModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(
            name="Keyboards",
        )

        cls.supplier = Supplier.objects.create(
            name="Logitech",
        )

    def create_product(self, **kwargs):
        defaults = {
            "sku": "KB-001",
            "name": "Logitech K120",
            "category": self.category,
            "supplier": self.supplier,
            "price": Decimal("19.99"),
            "minimum_stock": 5,
        }

        defaults.update(kwargs)

        return Product.objects.create(**defaults)

    def test_string_representation_contains_sku_and_name(self):
        product = self.create_product()

        self.assertEqual(
            str(product),
            "KB-001 - Logitech K120",
        )

    def test_sku_is_normalized_to_uppercase(self):
        product = self.create_product(
            sku=" kb-002 ",
        )

        self.assertEqual(
            product.sku,
            "KB-002",
        )

    def test_sku_must_be_unique(self):
        self.create_product()

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_product(
                name="Another keyboard",
            )

    def test_product_price_cannot_be_negative(self):
        product = Product(
            sku="KB-003",
            name="Invalid product",
            category=self.category,
            price=Decimal("-1.00"),
        )

        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_minimum_stock_cannot_be_negative(self):
        product = Product(
            sku="KB-004",
            name="Invalid product",
            category=self.category,
            price=Decimal("10.00"),
            minimum_stock=-1,
        )

        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_supplier_can_be_empty(self):
        product = self.create_product(
            sku="KB-005",
            supplier=None,
        )

        self.assertIsNone(product.supplier)

    def test_category_with_products_cannot_be_deleted(self):
        self.create_product()

        with self.assertRaises(ProtectedError):
            self.category.delete()