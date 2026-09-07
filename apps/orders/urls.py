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
]