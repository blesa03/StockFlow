from django.urls import path

from .views import (
    InventoryListAPIView,
    MovementListAPIView,
    OrderCancelAPIView,
    OrderConfirmAPIView,
    OrderDetailAPIView,
    OrderItemCreateAPIView,
    OrderItemDetailAPIView,
    OrderListCreateAPIView,
    ProductListAPIView,
)

app_name = "api"


urlpatterns = [
    path(
        "products/",
        ProductListAPIView.as_view(),
        name="product_list",
    ),

    path(
        "inventory/",
        InventoryListAPIView.as_view(),
        name="inventory_list",
    ),

    path(
        "movements/",
        MovementListAPIView.as_view(),
        name="movement_list",
    ),

    path(
        "orders/",
        OrderListCreateAPIView.as_view(),
        name="order_list",
    ),

    path(
        "orders/<int:order_id>/",
        OrderDetailAPIView.as_view(),
        name="order_detail",
    ),

    path(
        "orders/<int:order_id>/items/",
        OrderItemCreateAPIView.as_view(),
        name="order_item_create",
    ),

    path(
        (
            "orders/<int:order_id>/"
            "items/<int:item_id>/"
        ),
        OrderItemDetailAPIView.as_view(),
        name="order_item_detail",
    ),

    path(
        "orders/<int:order_id>/confirm/",
        OrderConfirmAPIView.as_view(),
        name="order_confirm",
    ),

    path(
        "orders/<int:order_id>/cancel/",
        OrderCancelAPIView.as_view(),
        name="order_cancel",
    ),
]