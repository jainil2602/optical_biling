from django.db import models
from django.contrib.auth.models import User


class Shop(models.Model):
    owner = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="shop"
    )

    shop_name = models.CharField(max_length=150)
    address = models.TextField()
    city = models.CharField(max_length=100)

    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)

    gst_number = models.CharField(
        max_length=50,
        blank=True
    )

    logo = models.ImageField(
        upload_to="shop_logos/",
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.shop_name