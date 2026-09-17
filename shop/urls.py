from django.urls import path
from .views import shop_setup

urlpatterns = [
    path("setup/", shop_setup, name="shop_setup"),
]