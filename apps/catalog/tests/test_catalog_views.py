from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import Category, Supplier

User = get_user_model()


class CatalogEntityViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command(
            "setup_roles",
            verbosity=0,
        )

        cls.operator = User.objects.create_user(
            username="operator-catalog",
            password="test-password",
        )

        cls.manager = User.objects.create_user(
            username="manager-catalog",
            password="test-password",
        )

        cls.operator.groups.add(
            Group.objects.get(
                name="Operator",
            )
        )

        cls.manager.groups.add(
            Group.objects.get(
                name="Manager",
            )
        )

        cls.category = Category.objects.create(
            name="Keyboards",
            description="Computer keyboards.",
        )

        cls.supplier = Supplier.objects.create(
            name="Logitech",
            email="sales@logitech.example",
            phone="+34 950 000 000",
        )

    def test_operator_can_view_categories(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "catalog:category_list"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_operator_cannot_create_category(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "catalog:category_create"
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_manager_can_create_category(self):
        self.client.force_login(
            self.manager,
        )

        response = self.client.post(
            reverse(
                "catalog:category_create"
            ),
            {
                "name": "Monitors",
                "description": "Display devices.",
                "active": "on",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "catalog:category_list"
            ),
        )

        self.assertTrue(
            Category.objects.filter(
                name="Monitors",
            ).exists()
        )

    def test_manager_can_edit_category(self):
        self.client.force_login(
            self.manager,
        )

        response = self.client.post(
            reverse(
                "catalog:category_edit",
                args=[
                    self.category.pk
                ],
            ),
            {
                "name": "Mechanical Keyboards",
                "description": "Updated.",
                "active": "on",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "catalog:category_list"
            ),
        )

        self.category.refresh_from_db()

        self.assertEqual(
            self.category.name,
            "Mechanical Keyboards",
        )

    def test_category_search_filters_results(self):
        Category.objects.create(
            name="Monitors",
        )

        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "catalog:category_list"
            ),
            {
                "q": "Keyboard",
            },
        )

        categories = list(
            response.context[
                "categories"
            ]
        )

        self.assertEqual(
            categories,
            [self.category],
        )

    def test_operator_can_view_suppliers(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "catalog:supplier_list"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_operator_cannot_create_supplier(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "catalog:supplier_create"
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_manager_can_create_supplier(self):
        self.client.force_login(
            self.manager,
        )

        response = self.client.post(
            reverse(
                "catalog:supplier_create"
            ),
            {
                "name": "Samsung",
                "email": "sales@samsung.example",
                "phone": "+34 950 111 111",
                "active": "on",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "catalog:supplier_list"
            ),
        )

        self.assertTrue(
            Supplier.objects.filter(
                name="Samsung",
            ).exists()
        )

    def test_manager_can_deactivate_supplier(self):
        self.client.force_login(
            self.manager,
        )

        response = self.client.post(
            reverse(
                "catalog:supplier_edit",
                args=[
                    self.supplier.pk
                ],
            ),
            {
                "name": self.supplier.name,
                "email": self.supplier.email,
                "phone": self.supplier.phone,
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "catalog:supplier_list"
            ),
        )

        self.supplier.refresh_from_db()

        self.assertFalse(
            self.supplier.active,
        )

    def test_inactive_supplier_can_be_filtered(self):
        self.supplier.active = False
        self.supplier.save(
            update_fields=[
                "active"
            ]
        )

        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "catalog:supplier_list"
            ),
            {
                "active": "inactive",
            },
        )

        suppliers = list(
            response.context[
                "suppliers"
            ]
        )

        self.assertIn(
            self.supplier,
            suppliers,
        )