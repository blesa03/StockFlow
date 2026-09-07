from django import forms

from apps.catalog.models import Product

from .models import StockMovement


class InventoryMovementForm(forms.Form):
    operation_type = forms.ChoiceField(
        label="Operation",
        choices=(
            (
                StockMovement.MovementType.ENTRY,
                "Entry",
            ),
            (
                StockMovement.MovementType.EXIT,
                "Exit",
            ),
            (
                StockMovement.MovementType.ADJUSTMENT,
                "Adjustment",
            ),
        ),
    )

    product = forms.ModelChoiceField(
        queryset=Product.objects.none(),
    )

    quantity = forms.IntegerField(
        min_value=0,
        help_text=(
            "For entries and exits, enter the "
            "quantity to move. For adjustments, "
            "enter the final stock quantity."
        ),
    )

    reason = forms.CharField(
        max_length=255,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": (
                    "Reason for the inventory operation"
                ),
            }
        ),
    )

    def __init__(
        self,
        *args,
        product_id=None,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        self.fields["product"].queryset = (
            Product.objects
            .select_related(
                "category",
            )
            .order_by(
                "-active",
                "name",
            )
        )

        if product_id:
            self.fields[
                "product"
            ].initial = product_id

    def clean(self):
        cleaned_data = super().clean()

        operation_type = cleaned_data.get(
            "operation_type"
        )

        quantity = cleaned_data.get(
            "quantity"
        )

        if quantity is None:
            return cleaned_data

        if (
            operation_type
            in (
                StockMovement.MovementType.ENTRY,
                StockMovement.MovementType.EXIT,
            )
            and quantity <= 0
        ):
            self.add_error(
                "quantity",
                (
                    "Entry and exit quantities "
                    "must be greater than zero."
                ),
            )

        return cleaned_data