from django.urls import path
from . import views

urlpatterns = [
    path("", views.customer_list, name="customer_list"),
    path("add/", views.customer_add, name="customer_add"),
    path(
        "<int:customer_id>/",
        views.customer_detail,
        name="customer_detail"
    ),
]