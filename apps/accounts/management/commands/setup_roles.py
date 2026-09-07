from django.core.management.base import BaseCommand

from apps.accounts.roles import sync_roles


class Command(BaseCommand):
    help = "Create or update StockFlow user roles and permissions."

    def handle(self, *args, **options):
        groups = sync_roles()

        for group_name, group in groups.items():
            self.stdout.write(
                f"{group_name}: "
                f"{group.permissions.count()} permissions"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "StockFlow roles configured successfully."
            )
        )