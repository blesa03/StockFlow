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
    CategoryForm,
    ProductForm,
    SupplierForm,
)
from .models import Category, Product, Supplier
from .selectors import (
    get_categories,
    get_product_with_stock,
    get_products,
    get_suppliers,
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
        "catalog_section": "products",
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
        "catalog_section": "products",
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
            "catalog_section": "products",
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
            "catalog_section": "products",
        },
    )


@login_required
@permission_required(
    "catalog.view_category",
    raise_exception=True,
)
def category_list(request):
    search = request.GET.get(
        "q",
        "",
    ).strip()

    active = request.GET.get(
        "active",
        "active",
    )

    categories = get_categories(
        search=search,
        active=active,
    )

    context = {
        "categories": categories,
        "filters": {
            "q": search,
            "active": active,
        },
        "catalog_section": "categories",
    }

    return render(
        request,
        "catalog/category_list.html",
        context,
    )


@login_required
@permission_required(
    "catalog.add_category",
    raise_exception=True,
)
def category_create(request):
    if request.method == "POST":
        form = CategoryForm(
            request.POST,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Category created successfully.",
            )

            return redirect(
                "catalog:category_list"
            )

    else:
        form = CategoryForm()

    return render(
        request,
        "catalog/category_form.html",
        {
            "form": form,
            "mode": "create",
            "catalog_section": "categories",
        },
    )


@login_required
@permission_required(
    "catalog.change_category",
    raise_exception=True,
)
def category_edit(request, category_id):
    category = get_object_or_404(
        Category,
        pk=category_id,
    )

    if request.method == "POST":
        form = CategoryForm(
            request.POST,
            instance=category,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Category updated successfully.",
            )

            return redirect(
                "catalog:category_list"
            )

    else:
        form = CategoryForm(
            instance=category,
        )

    return render(
        request,
        "catalog/category_form.html",
        {
            "form": form,
            "category": category,
            "mode": "edit",
            "catalog_section": "categories",
        },
    )


@login_required
@permission_required(
    "catalog.view_supplier",
    raise_exception=True,
)
def supplier_list(request):
    search = request.GET.get(
        "q",
        "",
    ).strip()

    active = request.GET.get(
        "active",
        "active",
    )

    suppliers = get_suppliers(
        search=search,
        active=active,
    )

    context = {
        "suppliers": suppliers,
        "filters": {
            "q": search,
            "active": active,
        },
        "catalog_section": "suppliers",
    }

    return render(
        request,
        "catalog/supplier_list.html",
        context,
    )


@login_required
@permission_required(
    "catalog.add_supplier",
    raise_exception=True,
)
def supplier_create(request):
    if request.method == "POST":
        form = SupplierForm(
            request.POST,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Supplier created successfully.",
            )

            return redirect(
                "catalog:supplier_list"
            )

    else:
        form = SupplierForm()

    return render(
        request,
        "catalog/supplier_form.html",
        {
            "form": form,
            "mode": "create",
            "catalog_section": "suppliers",
        },
    )


@login_required
@permission_required(
    "catalog.change_supplier",
    raise_exception=True,
)
def supplier_edit(request, supplier_id):
    supplier = get_object_or_404(
        Supplier,
        pk=supplier_id,
    )

    if request.method == "POST":
        form = SupplierForm(
            request.POST,
            instance=supplier,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Supplier updated successfully.",
            )

            return redirect(
                "catalog:supplier_list"
            )

    else:
        form = SupplierForm(
            instance=supplier,
        )

    return render(
        request,
        "catalog/supplier_form.html",
        {
            "form": form,
            "supplier": supplier,
            "mode": "edit",
            "catalog_section": "suppliers",
        },
    )