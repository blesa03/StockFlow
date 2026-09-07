from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.core.exceptions import (
    PermissionDenied,
)
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import (
    require_POST,
)

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
    create_order,
    remove_order_item,
    update_order_item_quantity,
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
def order_detail(request, order_id):
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
                messages.error(
                    request,
                    str(exc),
                )

                return redirect(
                    "orders:order_detail",
                    order_id=order.pk,
                )

            messages.success(
                request,
                "Product added to order.",
            )

            return redirect(
                "orders:order_detail",
                order_id=order.pk,
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
        messages.error(
            request,
            "Quantity must be greater than zero.",
        )

        return redirect(
            "orders:order_detail",
            order_id=order.pk,
        )

    try:
        update_order_item_quantity(
            item=item,
            quantity=form.cleaned_data[
                "quantity"
            ],
        )

    except OrderError as exc:
        messages.error(
            request,
            str(exc),
        )

    else:
        messages.success(
            request,
            "Order quantity updated.",
        )

    return redirect(
        "orders:order_detail",
        order_id=order.pk,
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
        messages.error(
            request,
            str(exc),
        )

    else:
        messages.success(
            request,
            "Product removed from order.",
        )

    return redirect(
        "orders:order_detail",
        order_id=order.pk,
    )