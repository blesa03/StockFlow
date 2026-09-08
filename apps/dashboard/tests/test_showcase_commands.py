from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import (
    CommandError,
    call_command,
)
from django.test import TestCase

from apps.catalog.models import (
    Category,
    Product,
    Supplier,
)
from apps.inventory.models import (
    StockMovement,
)
from apps.orders.models import Order

User = get_user_model()


class ShowcaseCommandTests(TestCase):
    def test_reset_requires_confirmation(self):
        User.objects.create_superuser(
            username="root",
            password="password",
        )

        with self.assertRaises(
            CommandError
        ):
            call_command(
                "reset_app_data"
            )

    def test_reset_preserves_superuser(self):
        superuser = (
            User.objects.create_superuser(
                username="root",
                password="password",
            )
        )

        User.objects.create_user(
            username="normal",
            password="password",
        )

        Category.objects.create(
            name="Temporary"
        )

        call_command(
            "reset_app_data",
            yes=True,
            stdout=StringIO(),
        )

        self.assertTrue(
            User.objects.filter(
                pk=superuser.pk
            ).exists()
        )

        self.assertFalse(
            User.objects.filter(
                username="normal"
            ).exists()
        )

        self.assertFalse(
            Category.objects.exists()
        )

    def test_seed_creates_showcase_dataset(self):
        User.objects.create_superuser(
            username="root",
            password="password",
        )

        call_command(
            "seed_showcase_data",
            stdout=StringIO(),
        )

        self.assertEqual(
            Category.objects.count(),
            7,
        )

        self.assertEqual(
            Supplier.objects.count(),
            5,
        )

        self.assertEqual(
            Product.objects.count(),
            30,
        )

        self.assertEqual(
            Order.objects.filter(
                status="CONFIRMED"
            ).count(),
            12,
        )

        self.assertEqual(
            Order.objects.filter(
                status="DRAFT"
            ).count(),
            5,
        )

        self.assertEqual(
            Order.objects.filter(
                status="CANCELLED"
            ).count(),
            3,
        )

        self.assertGreater(
            StockMovement.objects.count(),
            50,
        )

    def test_seed_refuses_non_empty_database(self):
        User.objects.create_superuser(
            username="root",
            password="password",
        )

        Category.objects.create(
            name="Existing data"
        )

        with self.assertRaises(
            CommandError
        ):
            call_command(
                "seed_showcase_data"
            )