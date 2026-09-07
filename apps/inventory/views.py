from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.core.paginator import Paginator
from django.shortcuts import redirect, render

from apps.catalog.models import Category

from .forms import InventoryMovementForm
from .models import StockMovement
from .selectors import (
    get_inventory_balances,
    get_inventory_metrics,
    get_stock_movements,
)
from .services import (
    InventoryError,
    adjust_stock,
    register_stock_entry,
    register_stock_exit,
)


@login_required
@permission_required(
    "inventory.view_inventorybalance",
    raise_exception=True,
)
def inventory_list(request):
    search = request.GET.get(
        "q",
        "",
    ).strip()

    category = request.GET.get(
        "category",
        "",
    )

    stock_status = request.GET.get(
        "status",
        "",
    )

    active = request.GET.get(
        "active",
        "active",
    )

    balances = get_inventory_balances(
        search=search,
        category=category,
        stock_status=stock_status,
        active=active,
    )

    paginator = Paginator(
        balances,
        20,
    )

    page = paginator.get_page(
        request.GET.get("page")
    )

    context = {
        "page": page,
        "metrics": get_inventory_metrics(),
        "categories": Category.objects.order_by(
            "name"
        ),
        "filters": {
            "q": search,
            "category": category,
            "status": stock_status,
            "active": active,
        },
        "inventory_section": "balances",
    }

    return render(
        request,
        "inventory/balance_list.html",
        context,
    )


@login_required
@permission_required(
    "inventory.view_stockmovement",
    raise_exception=True,
)
def movement_list(request):
    search = request.GET.get(
        "q",
        "",
    ).strip()

    movement_type = request.GET.get(
        "type",
        "",
    )

    movements = get_stock_movements(
        search=search,
        movement_type=movement_type,
    )

    paginator = Paginator(
        movements,
        25,
    )

    page = paginator.get_page(
        request.GET.get("page")
    )

    context = {
        "page": page,
        "movement_types": (
            StockMovement.MovementType.choices
        ),
        "filters": {
            "q": search,
            "type": movement_type,
        },
        "inventory_section": "movements",
    }

    return render(
        request,
        "inventory/movement_list.html",
        context,
    )


@login_required
@permission_required(
    "inventory.manage_stock",
    raise_exception=True,
)
def movement_create(request):
    product_id = request.GET.get(
        "product"
    )

    if request.method == "POST":
        form = InventoryMovementForm(
            request.POST,
        )

        if form.is_valid():
            product = form.cleaned_data[
                "product"
            ]

            operation_type = (
                form.cleaned_data[
                    "operation_type"
                ]
            )

            quantity = form.cleaned_data[
                "quantity"
            ]

            reason = form.cleaned_data[
                "reason"
            ]

            try:
                if (
                    operation_type
                    == StockMovement.MovementType.ENTRY
                ):
                    movement = register_stock_entry(
                        product=product,
                        quantity=quantity,
                        reason=reason,
                        created_by=request.user,
                    )

                elif (
                    operation_type
                    == StockMovement.MovementType.EXIT
                ):
                    movement = register_stock_exit(
                        product=product,
                        quantity=quantity,
                        reason=reason,
                        created_by=request.user,
                    )

                else:
                    movement = adjust_stock(  # noqa: F841
                        product=product,
                        new_quantity=quantity,
                        reason=reason,
                        created_by=request.user,
                    )

            except InventoryError as exc:
                form.add_error(
                    None,
                    str(exc),
                )

            else:
                messages.success(
                    request,
                    (
                        "Inventory movement "
                        "registered successfully."
                    ),
                )

                return redirect(
                    "inventory:movement_list"
                )

    else:
        form = InventoryMovementForm(
            product_id=product_id,
        )

    context = {
        "form": form,
        "inventory_section": "movements",
    }

    return render(
        request,
        "inventory/movement_form.html",
        context,
    )