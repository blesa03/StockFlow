from django import forms
from django.db.models import Q

from .models import Category, Product, Supplier


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        category_query = Q(active=True)
        supplier_query = Q(active=True)

        if self.instance and self.instance.pk:
            category_query |= Q(
                pk=self.instance.category_id,
            )

            if self.instance.supplier_id:
                supplier_query |= Q(
                    pk=self.instance.supplier_id,
                )

        self.fields["category"].queryset = (
            Category.objects
            .filter(category_query)
            .order_by("name")
        )

        self.fields["supplier"].queryset = (
            Supplier.objects
            .filter(supplier_query)
            .order_by("name")
        )

    def clean_sku(self):
        sku = self.cleaned_data["sku"]

        return sku.strip().upper()


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category

        fields = (
            "name",
            "description",
            "active",
        )

        widgets = {  # noqa: RUF012
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Keyboards",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": (
                        "Optional category description."
                    ),
                }
            ),
        }

    def clean_name(self):
        return self.cleaned_data["name"].strip()


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier

        fields = (
            "name",
            "email",
            "phone",
            "active",
        )

        widgets = {  # noqa: RUF012
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Logitech",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "sales@example.com",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "placeholder": "+34 950 000 000",
                }
            ),
        }

    def clean_name(self):
        return self.cleaned_data["name"].strip()

    def clean_email(self):
        email = self.cleaned_data["email"]

        return email.strip().lower()

    def clean_phone(self):
        return self.cleaned_data["phone"].strip()