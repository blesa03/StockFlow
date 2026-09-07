from rest_framework.permissions import BasePermission


class HasDjangoModelPermissions(BasePermission):
    """
    Checks the Django permissions declared by each API view.

    Example:

    required_permissions = {
        "GET": ("catalog.view_product",),
        "POST": ("orders.add_order",),
    }
    """

    def has_permission(
        self,
        request,
        view,
    ):
        required_permissions = getattr(
            view,
            "required_permissions",
            {},
        )

        permissions = required_permissions.get(
            request.method,
            (),
        )

        return all(
            request.user.has_perm(
                permission
            )
            for permission in permissions
        )