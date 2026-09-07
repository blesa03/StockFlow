from django.contrib.auth.models import Group
from django.db import transaction

from .models import User
from .roles import (
    MANAGER_GROUP,
    OPERATOR_GROUP,
)

VALID_ROLES = {
    MANAGER_GROUP,
    OPERATOR_GROUP,
}


class AccountError(Exception):
    pass


class InvalidRoleError(AccountError):
    pass


class SelfManagementError(AccountError):
    pass


def _get_role_group(role):
    if role not in VALID_ROLES:
        raise InvalidRoleError(
            f"Invalid role: {role}."
        )

    try:
        return Group.objects.get(
            name=role,
        )

    except Group.DoesNotExist as exc:
        raise InvalidRoleError(
            (  # noqa: UP034
                f"Role '{role}' is not configured. "
                "Run setup_roles first."
            )
        ) from exc


@transaction.atomic
def create_managed_user(
    *,
    username,
    password,
    role,
    first_name="",
    last_name="",
    email="",
    is_active=True,
):
    role_group = _get_role_group(
        role
    )

    user = User.objects.create_user(
        username=username,
        password=password,
        first_name=first_name,
        last_name=last_name,
        email=email,
        is_active=is_active,
    )

    user.groups.set(
        [role_group]
    )

    return user


@transaction.atomic
def update_managed_user(
    *,
    user,
    actor,
    username,
    first_name,
    last_name,
    email,
    role,
    is_active,
):
    if user.is_superuser:
        raise AccountError(
            (  # noqa: UP034
                "Superusers cannot be modified "
                "from StockFlow user management."
            )
        )

    if user.pk == actor.pk:
        if not is_active:
            raise SelfManagementError(
                (  # noqa: UP034
                    "You cannot deactivate "
                    "your own account."
                )
            )

        if role != MANAGER_GROUP:
            raise SelfManagementError(
                (  # noqa: UP034
                    "You cannot remove your own "
                    "Manager role."
                )
            )

    role_group = _get_role_group(
        role
    )

    user.username = username
    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    user.is_active = is_active

    user.save(
        update_fields=[
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
        ]
    )

    user.groups.set(
        [role_group]
    )

    return user