from django.urls import path

from . import views

app_name = "orders"


urlpatterns = [
    path(
        "orders/",
        views.order_list,
        name="order_list",
    ),
    path(
        "orders/new/",
        views.order_create,
        name="order_create",
    ),
    path(
        "orders/<int:order_id>/",
        views.order_detail,
        name="order_detail",
    ),
    path(
        (
            "orders/<int:order_id>/"
            "items/<int:item_id>/update/"
        ),
        views.order_item_update,
        name="order_item_update",
    ),
    path(
        (
            "orders/<int:order_id>/"
            "items/<int:item_id>/remove/"
        ),
        views.order_item_remove,
        name="order_item_remove",
    ),
    path(
        "orders/<int:order_id>/confirm/",
        views.order_confirm,
        name="order_confirm",
    ),
    path(
        "orders/<int:order_id>/cancel/",
        views.order_cancel,
        name="order_cancel",
    ),
]