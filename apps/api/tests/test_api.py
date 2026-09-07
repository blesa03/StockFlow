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
from apps.inventory.models import (
    InventoryBalance,
    StockMovement,
)
from apps.inventory.services import (
    register_stock_entry,
)
from apps.orders.models import Order
from apps.orders.services import (
    add_order_item,
    create_order,
)


class StockFlowApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command(
            "setup_roles",
            verbosity=0,
        )

        cls.operator = User.objects.create_user(
            username="api-operator",
            password="test-password",
        )

        cls.plain_user = User.objects.create_user(
            username="api-plain",
            password="test-password",
        )

        cls.operator.groups.add(
            Group.objects.get(
                name="Operator",
            )
        )

        cls.category = Category.objects.create(
            name="API peripherals",
        )

        cls.keyboard = Product.objects.create(
            sku="API-KB-001",
            name="API Keyboard",
            category=cls.category,
            price=Decimal("20.00"),
            minimum_stock=2,
        )

        cls.mouse = Product.objects.create(
            sku="API-MS-001",
            name="API Mouse",
            category=cls.category,
            price=Decimal("30.00"),
            minimum_stock=2,
        )

        register_stock_entry(
            product=cls.keyboard,
            quantity=10,
            reason="Initial API stock",
        )

        register_stock_entry(
            product=cls.mouse,
            quantity=8,
            reason="Initial API stock",
        )

    def setUp(self):
        self.client.force_authenticate(
            self.operator
        )

    def _stock(self, product):
        return (
            InventoryBalance.objects
            .get(product=product)
            .quantity
        )

    def test_products_require_authentication(self):
        self.client.force_authenticate(
            user=None
        )

        response = self.client.get(
            reverse(
                "api:product_list"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_operator_can_list_products(self):
        response = self.client.get(
            reverse(
                "api:product_list"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["count"],
            2,
        )

    def test_product_api_contains_stock_information(self):
        response = self.client.get(
            reverse(
                "api:product_list"
            ),
            {
                "q": "API Keyboard",
            },
        )

        product = response.data[
            "results"
        ][0]

        self.assertEqual(
            product[
                "stock_quantity"
            ],
            10,
        )

        self.assertEqual(
            product[
                "stock_status"
            ],
            "healthy",
        )

    def test_operator_can_list_inventory(self):
        response = self.client.get(
            reverse(
                "api:inventory_list"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["count"],
            2,
        )

    def test_plain_user_cannot_list_inventory(self):
        self.client.force_authenticate(
            self.plain_user
        )

        response = self.client.get(
            reverse(
                "api:inventory_list"
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_operator_can_create_draft_order(self):
        response = self.client.post(
            reverse(
                "api:order_list"
            ),
            {
                "customer_name": (
                    "REST Customer"
                ),
                "notes": "API order",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        order = Order.objects.get(
            customer_name=(
                "REST Customer"
            )
        )

        self.assertEqual(
            order.status,
            Order.Status.DRAFT,
        )

        self.assertEqual(
            order.created_by,
            self.operator,
        )

    def test_api_can_add_item_without_changing_stock(self):
        order = create_order(
            customer_name="API Draft",
            created_by=self.operator,
        )

        stock_before = self._stock(
            self.keyboard
        )

        response = self.client.post(
            reverse(
                "api:order_item_create",
                args=[order.pk],
            ),
            {
                "product": (
                    self.keyboard.pk
                ),
                "quantity": 3,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            order.items.filter(
                product=self.keyboard,
                quantity=3,
            ).exists()
        )

        self.assertEqual(
            self._stock(
                self.keyboard
            ),
            stock_before,
        )

    def test_api_can_update_item_without_changing_stock(self):
        order = create_order(
            customer_name="API Update",
            created_by=self.operator,
        )

        item = add_order_item(
            order=order,
            product=self.keyboard,
            quantity=2,
        )

        stock_before = self._stock(
            self.keyboard
        )

        response = self.client.patch(
            reverse(
                "api:order_item_detail",
                args=[
                    order.pk,
                    item.pk,
                ],
            ),
            {
                "quantity": 6,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        item.refresh_from_db()

        self.assertEqual(
            item.quantity,
            6,
        )

        self.assertEqual(
            self._stock(
                self.keyboard
            ),
            stock_before,
        )

    def test_api_can_remove_item_without_changing_stock(self):
        order = create_order(
            customer_name="API Remove",
            created_by=self.operator,
        )

        item = add_order_item(
            order=order,
            product=self.keyboard,
            quantity=2,
        )

        stock_before = self._stock(
            self.keyboard
        )

        response = self.client.delete(
            reverse(
                "api:order_item_detail",
                args=[
                    order.pk,
                    item.pk,
                ],
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            order.items.filter(
                pk=item.pk
            ).exists()
        )

        self.assertEqual(
            self._stock(
                self.keyboard
            ),
            stock_before,
        )

    def test_api_confirmation_updates_stock_and_movements(self):
        order = create_order(
            customer_name=(
                "API Confirmation"
            ),
            created_by=self.operator,
        )

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=3,
        )

        add_order_item(
            order=order,
            product=self.mouse,
            quantity=2,
        )

        response = self.client.post(
            reverse(
                "api:order_confirm",
                args=[order.pk],
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.CONFIRMED,
        )

        self.assertEqual(
            self._stock(
                self.keyboard
            ),
            7,
        )

        self.assertEqual(
            self._stock(
                self.mouse
            ),
            6,
        )

        self.assertEqual(
            StockMovement.objects.filter(
                order=order,
            ).count(),
            2,
        )

    def test_api_confirmation_rolls_back_on_shortage(self):
        order = create_order(
            customer_name=(
                "API Rollback"
            ),
            created_by=self.operator,
        )

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=4,
        )

        add_order_item(
            order=order,
            product=self.mouse,
            quantity=50,
        )

        keyboard_before = (
            self._stock(
                self.keyboard
            )
        )

        mouse_before = (
            self._stock(
                self.mouse
            )
        )

        response = self.client.post(
            reverse(
                "api:order_confirm",
                args=[order.pk],
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.DRAFT,
        )

        self.assertEqual(
            self._stock(
                self.keyboard
            ),
            keyboard_before,
        )

        self.assertEqual(
            self._stock(
                self.mouse
            ),
            mouse_before,
        )

        self.assertFalse(
            StockMovement.objects.filter(
                order=order,
            ).exists()
        )

    def test_api_can_cancel_draft_without_changing_stock(self):
        order = create_order(
            customer_name="API Cancel",
            created_by=self.operator,
        )

        add_order_item(
            order=order,
            product=self.keyboard,
            quantity=3,
        )

        stock_before = self._stock(
            self.keyboard
        )

        response = self.client.post(
            reverse(
                "api:order_cancel",
                args=[order.pk],
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            Order.Status.CANCELLED,
        )

        self.assertEqual(
            self._stock(
                self.keyboard
            ),
            stock_before,
        )

    def test_confirmed_order_cannot_be_modified_through_api(self):
        order = create_order(
            customer_name="API Locked",
            created_by=self.operator,
        )

        item = add_order_item(
            order=order,
            product=self.keyboard,
            quantity=2,
        )

        self.client.post(
            reverse(
                "api:order_confirm",
                args=[order.pk],
            ),
            {},
            format="json",
        )

        response = self.client.patch(
            reverse(
                "api:order_item_detail",
                args=[
                    order.pk,
                    item.pk,
                ],
            ),
            {
                "quantity": 50,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        item.refresh_from_db()

        self.assertEqual(
            item.quantity,
            2,
        )

    def test_order_browsable_api_renders(self):
        response = self.client.get(
            reverse(
                "api:order_list"
            ),
            HTTP_ACCEPT="text/html",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn(
            "text/html",
            response[
                "Content-Type"
            ],
        )

    def test_all_browsable_api_endpoints_render(self):
        order = create_order(
            customer_name="Browsable API",
            created_by=self.operator,
        )

        item = add_order_item(
            order=order,
            product=self.keyboard,
            quantity=1,
        )

        endpoints = (
            (
                reverse(
                    "api:product_list"
                ),
                status.HTTP_200_OK,
            ),
            (
                reverse(
                    "api:inventory_list"
                ),
                status.HTTP_200_OK,
            ),
            (
                reverse(
                    "api:movement_list"
                ),
                status.HTTP_200_OK,
            ),
            (
                reverse(
                    "api:order_list"
                ),
                status.HTTP_200_OK,
            ),
            (
                reverse(
                    "api:order_detail",
                    args=[order.pk],
                ),
                status.HTTP_200_OK,
            ),
            (
                reverse(
                    "api:order_item_create",
                    args=[order.pk],
                ),
                status.HTTP_405_METHOD_NOT_ALLOWED,
            ),
            (
                reverse(
                    "api:order_item_detail",
                    args=[
                        order.pk,
                        item.pk,
                    ],
                ),
                status.HTTP_405_METHOD_NOT_ALLOWED,
            ),
            (
                reverse(
                    "api:order_confirm",
                    args=[order.pk],
                ),
                status.HTTP_405_METHOD_NOT_ALLOWED,
            ),
            (
                reverse(
                    "api:order_cancel",
                    args=[order.pk],
                ),
                status.HTTP_405_METHOD_NOT_ALLOWED,
            ),
        )

        for url, expected_status in endpoints:
            with self.subTest(
                url=url
            ):
                response = self.client.get(
                    url,
                    HTTP_ACCEPT="text/html",
                )

                self.assertEqual(
                    response.status_code,
                    expected_status,
                )