from django.contrib.auth import get_user_model
from django.core.management import (
    BaseCommand,
    CommandError,
    call_command,
)
from django.core.management.color import no_style
from django.db import connection, transaction

from apps.catalog.models import (
    Category,
    Product,
    Supplier,
)
from apps.inventory.models import (
    InventoryBalance,
    StockMovement,
)
from apps.orders.models import (
    Order,
    OrderItem,
)

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Remove StockFlow operational data while "
        "preserving superusers."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help=(
                "Confirm destructive database reset."
            ),
        )

    def handle(self, *args, **options):
        if not options["yes"]:
            raise CommandError(
                (
                    "This command deletes StockFlow data. "
                    "Run again with --yes to confirm."
                )
            )

        superusers = User.objects.filter(
            is_superuser=True
        )

        if not superusers.exists():
            raise CommandError(
                (
                    "No superuser exists. Reset aborted "
                    "to avoid removing every login account."
                )
            )

        self.stdout.write(
            self.style.WARNING(
                "Resetting StockFlow application data..."
            )
        )

        with transaction.atomic():
            deleted = {}

            deleted["movements"] = (
                StockMovement.objects.all().delete()[0]
            )

            deleted["orders"] = (
                Order.objects.all().delete()[0]
            )

            deleted["balances"] = (
                InventoryBalance.objects.all().delete()[0]
            )

            deleted["products"] = (
                Product.objects.all().delete()[0]
            )

            deleted["suppliers"] = (
                Supplier.objects.all().delete()[0]
            )

            deleted["categories"] = (
                Category.objects.all().delete()[0]
            )

            deleted["users"] = (
                User.objects.filter(
                    is_superuser=False
                ).delete()[0]
            )

            self._reset_sequences()

        call_command(
            "setup_roles",
            verbosity=0,
        )

        self.stdout.write("")

        self.stdout.write(
            f"Categories removed: {deleted['categories']}"
        )
        self.stdout.write(
            f"Suppliers removed: {deleted['suppliers']}"
        )
        self.stdout.write(
            f"Products removed: {deleted['products']}"
        )
        self.stdout.write(
            f"Balances removed: {deleted['balances']}"
        )
        self.stdout.write(
            f"Movements removed: {deleted['movements']}"
        )
        self.stdout.write(
            f"Orders removed: {deleted['orders']}"
        )
        self.stdout.write(
            f"Non-superusers removed: {deleted['users']}"
        )

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                (
                    "StockFlow reset complete. "
                    f"{superusers.count()} "
                    "superuser(s) preserved."
                )
            )
        )

    def _reset_sequences(self):
        models = (
            Category,
            Supplier,
            Product,
            InventoryBalance,
            StockMovement,
            Order,
            OrderItem,
        )

        sql_list = (
            connection.ops.sequence_reset_sql(
                no_style(),
                models,
            )
        )

        if not sql_list:
            return

        with connection.cursor() as cursor:
            for sql in sql_list:
                cursor.execute(sql)