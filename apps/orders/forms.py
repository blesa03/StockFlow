from django import forms


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