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
]