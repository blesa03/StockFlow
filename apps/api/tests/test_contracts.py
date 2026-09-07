from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.catalog.models import (
    Category,
    Product,
)
from apps.orders.services import (
    add_order_item,
    create_order,
)


class ApiContractTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command(
            "setup_roles",
            verbosity=0,
        )

        cls.operator = User.objects.create_user(
            username="contract-operator",
            password="test-password",
        )

        cls.plain_user = User.objects.create_user(
            username="contract-plain",
            password="test-password",
        )

        cls.operator.groups.add(
            Group.objects.get(
                name="Operator",
            )
        )

        cls.category = Category.objects.create(
            name="Contract products",
        )

        cls.product = Product.objects.create(
            sku="CT-001",
            name="Contract Keyboard",
            category=cls.category,
            price=Decimal("25.00"),
            minimum_stock=2,
        )

    def setUp(self):
        self.client.force_authenticate(
            self.operator
        )

    def test_order_detail_has_expected_contract(self):
        order = create_order(
            customer_name="Contract Customer",
            notes="Contract test",
            created_by=self.operator,
        )

        response = self.client.get(
            reverse(
                "api:order_detail",
                args=[order.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            set(response.data.keys()),
            {
                "id",
                "order_number",
                "customer_name",
                "notes",
                "status",
                "items",
                "total",
                "created_by",
                "confirmed_by",
                "created_at",
            },
        )

    def test_invalid_item_quantity_returns_400(self):
        order = create_order(
            customer_name="Invalid quantity",
            created_by=self.operator,
        )

        response = self.client.post(
            reverse(
                "api:order_item_create",
                args=[order.pk],
            ),
            {
                "product": self.product.pk,
                "quantity": 0,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_unknown_product_returns_400(self):
        order = create_order(
            customer_name="Unknown product",
            created_by=self.operator,
        )

        response = self.client.post(
            reverse(
                "api:order_item_create",
                args=[order.pk],
            ),
            {
                "product": 999999,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_item_from_another_order_returns_404(self):
        first_order = create_order(
            customer_name="First order",
            created_by=self.operator,
        )

        second_order = create_order(
            customer_name="Second order",
            created_by=self.operator,
        )

        item = add_order_item(
            order=first_order,
            product=self.product,
            quantity=1,
        )

        response = self.client.patch(
            reverse(
                "api:order_item_detail",
                args=[
                    second_order.pk,
                    item.pk,
                ],
            ),
            {
                "quantity": 5,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_plain_user_cannot_create_order(self):
        self.client.force_authenticate(
            self.plain_user
        )

        response = self.client.post(
            reverse(
                "api:order_list"
            ),
            {
                "customer_name": "Forbidden",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_order_actions_do_not_accept_get(self):
        order = create_order(
            customer_name="HTTP methods",
            created_by=self.operator,
        )

        urls = (
            reverse(
                "api:order_confirm",
                args=[order.pk],
            ),
            reverse(
                "api:order_cancel",
                args=[order.pk],
            ),
        )

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(
                    url
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                )