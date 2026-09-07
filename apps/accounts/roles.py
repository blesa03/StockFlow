from django.contrib.auth.models import Group, Permission

MANAGER_GROUP = "Manager"
OPERATOR_GROUP = "Operator"


OPERATOR_PERMISSIONS = {
    # Catalog
    "catalog.view_category",
    "catalog.view_supplier",
    "catalog.view_product",

    # Inventory
    "inventory.view_inventorybalance",
    "inventory.view_stockmovement",
    "inventory.manage_stock",

    # Orders
    "orders.view_order",
    "orders.add_order",
    "orders.change_order",
    "orders.view_orderitem",
    "orders.add_orderitem",
    "orders.change_orderitem",
    "orders.confirm_order",
    "orders.cancel_order",
}


MANAGER_PERMISSIONS = OPERATOR_PERMISSIONS | {
    # Accounts
    "accounts.view_user",
    "accounts.add_user",
    "accounts.change_user",

    # Catalog management
    "catalog.add_category",
    "catalog.change_category",
    "catalog.add_supplier",
    "catalog.change_supplier",
    "catalog.add_product",
    "catalog.change_product",
}


ROLE_PERMISSIONS = {
    MANAGER_GROUP: MANAGER_PERMISSIONS,
    OPERATOR_GROUP: OPERATOR_PERMISSIONS,
}


def get_permission(permission_name):
    app_label, codename = permission_name.split(".", maxsplit=1)

    try:
        return Permission.objects.get(
            content_type__app_label=app_label,
            codename=codename,
        )
    except Permission.DoesNotExist as exc:
        raise RuntimeError(
            f"Permission '{permission_name}' does not exist. "
            "Run migrations before setting up roles."
        ) from exc


def sync_roles():
    groups = {}

    for group_name, permission_names in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(
            name=group_name,
        )

        permissions = [
            get_permission(permission_name)
            for permission_name in sorted(permission_names)
        ]

        group.permissions.set(permissions)

        groups[group_name] = group

    return groups