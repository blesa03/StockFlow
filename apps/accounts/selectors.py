from django.db.models import Q

from .models import User


def get_users(
    *,
    search="",
    role="",
    active="all",
):
    queryset = (
        User.objects
        .prefetch_related("groups")
        .order_by("username")
    )

    if search:
        queryset = queryset.filter(
            Q(username__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
        )

    if role:
        queryset = queryset.filter(
            groups__name=role,
        )

    if active == "active":
        queryset = queryset.filter(
            is_active=True,
        )

    elif active == "inactive":
        queryset = queryset.filter(
            is_active=False,
        )

    return queryset.distinct()


def get_user_metrics():
    queryset = User.objects.all()

    return {
        "total": queryset.count(),
        "active": queryset.filter(
            is_active=True,
        ).count(),
        "managers": queryset.filter(
            groups__name="Manager",
        ).distinct().count(),
        "operators": queryset.filter(
            groups__name="Operator",
        ).distinct().count(),
    }