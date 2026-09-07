from django.urls import path

from . import views

app_name = "catalog"


urlpatterns = [
    path(
        "products/",
        views.product_list,
        name="product_list",
    ),
    path(
        "products/new/",
        views.product_create,
        name="product_create",
    ),
    path(
        "products/<int:product_id>/",
        views.product_detail,
        name="product_detail",
    ),
    path(
        "products/<int:product_id>/edit/",
        views.product_edit,
        name="product_edit",
    ),

    path(
        "categories/",
        views.category_list,
        name="category_list",
    ),
    path(
        "categories/new/",
        views.category_create,
        name="category_create",
    ),
    path(
        "categories/<int:category_id>/edit/",
        views.category_edit,
        name="category_edit",
    ),

    path(
        "suppliers/",
        views.supplier_list,
        name="supplier_list",
    ),
    path(
        "suppliers/new/",
        views.supplier_create,
        name="supplier_create",
    ),
    path(
        "suppliers/<int:supplier_id>/edit/",
        views.supplier_edit,
        name="supplier_edit",
    ),
]