from django import forms

from apps.catalog.models import Product


class OrderForm(forms.Form):
    customer_name = forms.CharField(
        label="Customer",
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "placeholder": (
                    "Customer name or internal reference"
                ),
            }
        ),
    )

    notes = forms.CharField(
        label="Notes",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": (
                    "Optional notes for this order"
                ),
            }
        ),
    )

    def clean_customer_name(self):
        customer_name = self.cleaned_data[
            "customer_name"
        ].strip()

        if not customer_name:
            raise forms.ValidationError(
                "Customer name is required."
            )

        return customer_name

    def clean_notes(self):
        return self.cleaned_data[
            "notes"
        ].strip()


class ProductOrderChoiceField(
    forms.ModelChoiceField
):
    def label_from_instance(self, product):
        balance = getattr(
            product,
            "inventory_balance",
            None,
        )

        quantity = (
            balance.quantity
            if balance is not None
            else 0
        )

        return (
            f"{product.sku} — "
            f"{product.name} "
            f"({quantity} in stock)"
        )


class OrderItemForm(forms.Form):
    product = ProductOrderChoiceField(
        queryset=Product.objects.none(),
    )

    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(
            attrs={
                "min": "1",
            }
        ),
    )

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        self.fields["product"].queryset = (
            Product.objects
            .filter(
                active=True,
            )
            .select_related(
                "inventory_balance",
            )
            .order_by(
                "name",
            )
        )


class OrderItemQuantityForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                "min": "1",
            }
        ),
    )