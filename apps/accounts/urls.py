from django.urls import path

from . import views

app_name = "accounts"


urlpatterns = [
    path(
        "users/",
        views.user_list,
        name="user_list",
    ),
    path(
        "users/new/",
        views.user_create,
        name="user_create",
    ),
    path(
        "users/<int:user_id>/edit/",
        views.user_edit,
        name="user_edit",
    ),
]