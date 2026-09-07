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

from .forms import ProductForm
from .models import Category, Product, Supplier
from .selectors import (
    get_product_with_stock,
    get_products,
)


@login_required
@permission_required(
    "catalog.view_product",
    raise_exception=True,
)
def product_list(request):
    search = request.GET.get(
        "q",
        "",
    ).strip()

    category = request.GET.get(
        "category",
        "",
    )

    supplier = request.GET.get(
        "supplier",
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

    products = get_products(
        search=search,
        category=category,
        supplier=supplier,
        stock_status=stock_status,
        active=active,
    )

    paginator = Paginator(
        products,
        15,
    )

    page = paginator.get_page(
        request.GET.get("page"),
    )

    context = {
        "page": page,
        "categories": Category.objects.order_by(
            "name"
        ),
        "suppliers": Supplier.objects.order_by(
            "name"
        ),
        "filters": {
            "q": search,
            "category": category,
            "supplier": supplier,
            "status": stock_status,
            "active": active,
        },
    }

    return render(
        request,
        "catalog/product_list.html",
        context,
    )


@login_required
@permission_required(
    "catalog.view_product",
    raise_exception=True,
)
def product_detail(request, product_id):
    try:
        product = get_product_with_stock(
            product_id
        )
    except Product.DoesNotExist:
        product = get_object_or_404(
            Product,
            pk=product_id,
        )

    movements = (
        product.stock_movements
        .select_related(
            "order",
            "created_by",
        )
        .order_by("-created_at")[:10]
    )

    context = {
        "product": product,
        "movements": movements,
    }

    return render(
        request,
        "catalog/product_detail.html",
        context,
    )


@login_required
@permission_required(
    "catalog.add_product",
    raise_exception=True,
)
def product_create(request):
    if request.method == "POST":
        form = ProductForm(
            request.POST,
        )

        if form.is_valid():
            product = form.save()

            messages.success(
                request,
                "Product created successfully.",
            )

            return redirect(
                "catalog:product_detail",
                product_id=product.pk,
            )

    else:
        form = ProductForm()

    return render(
        request,
        "catalog/product_form.html",
        {
            "form": form,
            "mode": "create",
        },
    )


@login_required
@permission_required(
    "catalog.change_product",
    raise_exception=True,
)
def product_edit(request, product_id):
    product = get_object_or_404(
        Product,
        pk=product_id,
    )

    if request.method == "POST":
        form = ProductForm(
            request.POST,
            instance=product,
        )

        if form.is_valid():
            product = form.save()

            messages.success(
                request,
                "Product updated successfully.",
            )

            return redirect(
                "catalog:product_detail",
                product_id=product.pk,
            )

    else:
        form = ProductForm(
            instance=product,
        )

    return render(
        request,
        "catalog/product_form.html",
        {
            "form": form,
            "product": product,
            "mode": "edit",
        },
    )