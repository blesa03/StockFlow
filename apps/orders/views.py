from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import require_POST

from apps.inventory.services import InventoryError

from .forms import (
    OrderForm,
    OrderItemForm,
    OrderItemQuantityForm,
)
from .models import Order, OrderItem
from .selectors import (
    get_order_detail,
    get_order_metrics,
    get_orders,
)
from .services import (
    OrderError,
    add_order_item,
    cancel_order,
    confirm_order,
    create_order,
    remove_order_item,
    update_order_item_quantity,
)


def _is_htmx(request):
    return (
        request.headers.get("HX-Request")
        == "true"
    )


def _get_order_or_404(order_id):
    try:
        return get_order_detail(
            order_id
        )

    except Order.DoesNotExist as exc:
        raise Http404(
            "Order not found."
        ) from exc


def _render_order_workspace(
    request,
    order_id,
    *,
    add_item_form=None,
    feedback="",
    feedback_level="success",
):
    order = _get_order_or_404(
        order_id
    )

    if add_item_form is None:
        add_item_form = OrderItemForm()

    return render(
        request,
        "orders/partials/order_workspace.html",
        {
            "order": order,
            "add_item_form": add_item_form,
            "feedback": feedback,
            "feedback_level": feedback_level,
        },
    )


def _action_response(
    request,
    order,
    *,
    feedback,
    level="success",
):
    if _is_htmx(request):
        return _render_order_workspace(
            request,
            order.pk,
            feedback=feedback,
            feedback_level=level,
        )

    if level == "error":
        messages.error(
            request,
            feedback,
        )
    else:
        messages.success(
            request,
            feedback,
        )

    return redirect(
        "orders:order_detail",
        order_id=order.pk,
    )


@login_required
@permission_required(
    "orders.view_order",
    raise_exception=True,
)
def order_list(request):
    search = request.GET.get(
        "q",
        "",
    ).strip()

    status = request.GET.get(
        "status",
        "",
    )

    orders = get_orders(
        search=search,
        status=status,
    )

    paginator = Paginator(
        orders,
        20,
    )

    page = paginator.get_page(
        request.GET.get("page")
    )

    context = {
        "page": page,
        "metrics": get_order_metrics(),
        "statuses": Order.Status.choices,
        "filters": {
            "q": search,
            "status": status,
        },
    }

    return render(
        request,
        "orders/order_list.html",
        context,
    )


@login_required
@permission_required(
    "orders.add_order",
    raise_exception=True,
)
def order_create(request):
    if request.method == "POST":
        form = OrderForm(
            request.POST,
        )

        if form.is_valid():
            order = create_order(
                customer_name=(
                    form.cleaned_data[
                        "customer_name"
                    ]
                ),
                notes=(
                    form.cleaned_data[
                        "notes"
                    ]
                ),
                created_by=request.user,
            )

            messages.success(
                request,
                (
                    f"{order.order_number} "
                    "created as draft."
                ),
            )

            return redirect(
                "orders:order_detail",
                order_id=order.pk,
            )

    else:
        form = OrderForm()

    return render(
        request,
        "orders/order_form.html",
        {
            "form": form,
        },
    )


@login_required
@permission_required(
    "orders.view_order",
    raise_exception=True,
)
def order_detail(
    request,
    order_id,
):
    order = _get_order_or_404(
        order_id
    )

    add_item_form = OrderItemForm()

    if request.method == "POST":
        if not request.user.has_perm(
            "orders.add_orderitem"
        ):
            raise PermissionDenied

        add_item_form = OrderItemForm(
            request.POST
        )

        if add_item_form.is_valid():
            try:
                add_order_item(
                    order=order,
                    product=(
                        add_item_form
                        .cleaned_data[
                            "product"
                        ]
                    ),
                    quantity=(
                        add_item_form
                        .cleaned_data[
                            "quantity"
                        ]
                    ),
                )

            except OrderError as exc:
                if _is_htmx(request):
                    return _render_order_workspace(
                        request,
                        order.pk,
                        add_item_form=(
                            add_item_form
                        ),
                        feedback=str(exc),
                        feedback_level="error",
                    )

                messages.error(
                    request,
                    str(exc),
                )

                return redirect(
                    "orders:order_detail",
                    order_id=order.pk,
                )

            if _is_htmx(request):
                return _render_order_workspace(
                    request,
                    order.pk,
                    feedback=(
                        "Product added to order."
                    ),
                )

            messages.success(
                request,
                "Product added to order.",
            )

            return redirect(
                "orders:order_detail",
                order_id=order.pk,
            )

        if _is_htmx(request):
            return _render_order_workspace(
                request,
                order.pk,
                add_item_form=add_item_form,
                feedback=(
                    "Please correct the "
                    "highlighted fields."
                ),
                feedback_level="error",
            )

    context = {
        "order": order,
        "add_item_form": add_item_form,
    }

    return render(
        request,
        "orders/order_detail.html",
        context,
    )


@login_required
@permission_required(
    "orders.change_orderitem",
    raise_exception=True,
)
@require_POST
def order_item_update(
    request,
    order_id,
    item_id,
):
    order = get_object_or_404(
        Order,
        pk=order_id,
    )

    item = get_object_or_404(
        OrderItem,
        pk=item_id,
        order=order,
    )

    form = OrderItemQuantityForm(
        request.POST
    )

    if not form.is_valid():
        return _action_response(
            request,
            order,
            feedback=(
                "Quantity must be "
                "greater than zero."
            ),
            level="error",
        )

    try:
        update_order_item_quantity(
            item=item,
            quantity=(
                form.cleaned_data[
                    "quantity"
                ]
            ),
        )

    except OrderError as exc:
        return _action_response(
            request,
            order,
            feedback=str(exc),
            level="error",
        )

    return _action_response(
        request,
        order,
        feedback=(
            "Order quantity updated."
        ),
    )


@login_required
@permission_required(
    "orders.change_orderitem",
    raise_exception=True,
)
@require_POST
def order_item_remove(
    request,
    order_id,
    item_id,
):
    order = get_object_or_404(
        Order,
        pk=order_id,
    )

    item = get_object_or_404(
        OrderItem,
        pk=item_id,
        order=order,
    )

    try:
        remove_order_item(
            item=item,
        )

    except OrderError as exc:
        return _action_response(
            request,
            order,
            feedback=str(exc),
            level="error",
        )

    return _action_response(
        request,
        order,
        feedback=(
            "Product removed from order."
        ),
    )


@login_required
@permission_required(
    "orders.confirm_order",
    raise_exception=True,
)
@require_POST
def order_confirm(
    request,
    order_id,
):
    order = get_object_or_404(
        Order,
        pk=order_id,
    )

    try:
        confirm_order(
            order=order,
            confirmed_by=request.user,
        )

    except (
        OrderError,
        InventoryError,
    ) as exc:
        return _action_response(
            request,
            order,
            feedback=str(exc),
            level="error",
        )

    return _action_response(
        request,
        order,
        feedback=(
            f"{order.order_number} "
            "confirmed successfully."
        ),
    )


@login_required
@permission_required(
    "orders.cancel_order",
    raise_exception=True,
)
@require_POST
def order_cancel(
    request,
    order_id,
):
    order = get_object_or_404(
        Order,
        pk=order_id,
    )

    try:
        cancel_order(
            order=order,
        )

    except OrderError as exc:
        return _action_response(
            request,
            order,
            feedback=str(exc),
            level="error",
        )

    return _action_response(
        request,
        order,
        feedback=(
            f"{order.order_number} "
            "cancelled."
        ),
    )