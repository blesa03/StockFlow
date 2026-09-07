from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.core.paginator import Paginator
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from .forms import (
    UserCreateForm,
    UserEditForm,
)
from .models import User
from .roles import (
    MANAGER_GROUP,
    OPERATOR_GROUP,
)
from .selectors import (
    get_user_metrics,
    get_users,
)
from .services import (
    AccountError,
    create_managed_user,
    update_managed_user,
)


@login_required
@permission_required(
    "accounts.view_user",
    raise_exception=True,
)
def user_list(request):
    search = request.GET.get(
        "q",
        "",
    ).strip()

    role = request.GET.get(
        "role",
        "",
    )

    active = request.GET.get(
        "active",
        "all",
    )

    users = get_users(
        search=search,
        role=role,
        active=active,
    )

    paginator = Paginator(
        users,
        20,
    )

    page = paginator.get_page(
        request.GET.get("page")
    )

    context = {
        "page": page,
        "metrics": get_user_metrics(),
        "roles": (
            (
                MANAGER_GROUP,
                "Manager",
            ),
            (
                OPERATOR_GROUP,
                "Operator",
            ),
        ),
        "filters": {
            "q": search,
            "role": role,
            "active": active,
        },
    }

    return render(
        request,
        "accounts/user_list.html",
        context,
    )


@login_required
@permission_required(
    "accounts.add_user",
    raise_exception=True,
)
def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(
            request.POST,
        )

        if form.is_valid():
            user = create_managed_user(
                username=(
                    form.cleaned_data[
                        "username"
                    ]
                ),
                password=(
                    form.cleaned_data[
                        "password1"
                    ]
                ),
                first_name=(
                    form.cleaned_data[
                        "first_name"
                    ]
                ),
                last_name=(
                    form.cleaned_data[
                        "last_name"
                    ]
                ),
                email=(
                    form.cleaned_data[
                        "email"
                    ]
                ),
                role=(
                    form.cleaned_data[
                        "role"
                    ]
                ),
                is_active=(
                    form.cleaned_data[
                        "is_active"
                    ]
                ),
            )

            messages.success(
                request,
                (
                    f"User {user.username} "
                    "created successfully."
                ),
            )

            return redirect(
                "accounts:user_list"
            )

    else:
        form = UserCreateForm(
            initial={
                "is_active": True,
            }
        )

    return render(
        request,
        "accounts/user_form.html",
        {
            "form": form,
            "mode": "create",
        },
    )


@login_required
@permission_required(
    "accounts.change_user",
    raise_exception=True,
)
def user_edit(
    request,
    user_id,
):
    user = get_object_or_404(
        User.objects.prefetch_related(
            "groups"
        ),
        pk=user_id,
    )

    if user.is_superuser:
        messages.error(
            request,
            (
                "Superusers cannot be modified "
                "from this interface."
            ),
        )

        return redirect(
            "accounts:user_list"
        )

    if request.method == "POST":
        form = UserEditForm(
            request.POST,
            instance=user,
        )

        if form.is_valid():
            try:
                update_managed_user(
                    user=user,
                    actor=request.user,
                    username=(
                        form.cleaned_data[
                            "username"
                        ]
                    ),
                    first_name=(
                        form.cleaned_data[
                            "first_name"
                        ]
                    ),
                    last_name=(
                        form.cleaned_data[
                            "last_name"
                        ]
                    ),
                    email=(
                        form.cleaned_data[
                            "email"
                        ]
                    ),
                    role=(
                        form.cleaned_data[
                            "role"
                        ]
                    ),
                    is_active=(
                        form.cleaned_data[
                            "is_active"
                        ]
                    ),
                )

            except AccountError as exc:
                form.add_error(
                    None,
                    str(exc),
                )

            else:
                messages.success(
                    request,
                    (
                        f"User {user.username} "
                        "updated successfully."
                    ),
                )

                return redirect(
                    "accounts:user_list"
                )

    else:
        form = UserEditForm(
            instance=user,
        )

    return render(
        request,
        "accounts/user_form.html",
        {
            "form": form,
            "mode": "edit",
            "managed_user": user,
        },
    )