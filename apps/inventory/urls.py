from django.urls import path

from . import views

app_name = "inventory"


urlpatterns = [
    path(
        "inventory/",
        views.inventory_list,
        name="inventory_list",
    ),
    path(
        "inventory/movements/",
        views.movement_list,
        name="movement_list",
    ),
    path(
        "inventory/movements/new/",
        views.movement_create,
        name="movement_create",
    ),
]