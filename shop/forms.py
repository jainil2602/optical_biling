from django import forms
from .models import Shop


class ShopForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = [
            "shop_name",
            "address",
            "city",
            "phone",
            "email",
            "gst_number",
            "logo",
        ]

        widgets = {
            "shop_name": forms.TextInput(attrs={
                "placeholder": "Enter shop name"
            }),
            "address": forms.Textarea(attrs={
                "placeholder": "Enter complete shop address",
                "rows": 3
            }),
            "city": forms.TextInput(attrs={
                "placeholder": "Enter city"
            }),
            "phone": forms.TextInput(attrs={
                "placeholder": "Enter phone number"
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "Enter email address"
            }),
            "gst_number": forms.TextInput(attrs={
                "placeholder": "Enter GST number (optional)"
            }),
        }