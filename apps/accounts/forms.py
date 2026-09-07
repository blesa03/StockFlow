from django import forms
from django.contrib.auth.forms import (
    UserCreationForm,
)

from .models import User
from .roles import (
    MANAGER_GROUP,
    OPERATOR_GROUP,
)

ROLE_CHOICES = (
    (
        OPERATOR_GROUP,
        "Operator",
    ),
    (
        MANAGER_GROUP,
        "Manager",
    ),
)


class UserCreateForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        initial=OPERATOR_GROUP,
    )

    class Meta:
        model = User

        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "password1",
            "password2",
            "is_active",
        )

        widgets = {  # noqa: RUF012
            "username": forms.TextInput(
                attrs={
                    "placeholder": "j.smith",
                }
            ),
            "first_name": forms.TextInput(
                attrs={
                    "placeholder": "John",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "placeholder": "Smith",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "john@example.com",
                }
            ),
        }

    def clean_username(self):
        return self.cleaned_data[
            "username"
        ].strip()

    def clean_email(self):
        return self.cleaned_data[
            "email"
        ].strip().lower()


class UserEditForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
    )

    class Meta:
        model = User

        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "is_active",
        )

        widgets = {  # noqa: RUF012
            "username": forms.TextInput(),
            "first_name": forms.TextInput(),
            "last_name": forms.TextInput(),
            "email": forms.EmailInput(),
        }

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )

        if self.instance and self.instance.pk:
            role = (
                self.instance.groups
                .filter(
                    name__in=(
                        MANAGER_GROUP,
                        OPERATOR_GROUP,
                    )
                )
                .values_list(
                    "name",
                    flat=True,
                )
                .first()
            )

            if role:
                self.fields[
                    "role"
                ].initial = role

    def clean_username(self):
        return self.cleaned_data[
            "username"
        ].strip()

    def clean_email(self):
        return self.cleaned_data[
            "email"
        ].strip().lower()