from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.core.paginator import Paginator
from django.shortcuts import redirect, render

from .forms import OrderForm
from .models import Order
from .selectors import (
    get_order_metrics,
    get_orders,
)
from .services import create_order


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
                customer_name=form.cleaned_data[
                    "customer_name"
                ],
                notes=form.cleaned_data[
                    "notes"
                ],
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
                "orders:order_list"
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