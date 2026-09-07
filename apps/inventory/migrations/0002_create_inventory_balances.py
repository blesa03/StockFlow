from django.db import migrations


def create_inventory_balances(apps, schema_editor):
    Product = apps.get_model(
        "catalog",
        "Product",
    )

    InventoryBalance = apps.get_model(
        "inventory",
        "InventoryBalance",
    )

    balances = [
        InventoryBalance(
            product_id=product.id,
            quantity=0,
        )
        for product in Product.objects.all()
    ]

    InventoryBalance.objects.bulk_create(
        balances,
        ignore_conflicts=True,
    )


def remove_inventory_balances(apps, schema_editor):
    InventoryBalance = apps.get_model(
        "inventory",
        "InventoryBalance",
    )

    InventoryBalance.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        ("inventory", "0001_initial"),
    ]

    operations = [  # noqa: RUF012
        migrations.RunPython(
            create_inventory_balances,
            remove_inventory_balances,
        ),
    ]