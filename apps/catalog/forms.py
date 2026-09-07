from django import forms

from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product

        fields = (
            "sku",
            "name",
            "category",
            "supplier",
            "price",
            "minimum_stock",
            "active",
        )

        widgets = {  # noqa: RUF012
            "sku": forms.TextInput(
                attrs={
                    "placeholder": "KB-001",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Logitech K120",
                }
            ),
            "price": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "minimum_stock": forms.NumberInput(
                attrs={
                    "min": "0",
                }
            ),
        }

    def clean_sku(self):
        sku = self.cleaned_data["sku"]

        return sku.strip().upper()