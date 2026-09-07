from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.accounts.roles import (
    MANAGER_GROUP,
    OPERATOR_GROUP,
)


class AccountViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command(
            "setup_roles",
            verbosity=0,
        )

        cls.manager = User.objects.create_user(
            username="manager-test",
            password="test-password",
            first_name="Manager",
        )

        cls.operator = User.objects.create_user(
            username="operator-test",
            password="test-password",
            first_name="Operator",
        )

        cls.manager.groups.add(
            Group.objects.get(
                name=MANAGER_GROUP,
            )
        )

        cls.operator.groups.add(
            Group.objects.get(
                name=OPERATOR_GROUP,
            )
        )

    def test_user_list_requires_authentication(self):
        response = self.client.get(
            reverse(
                "accounts:user_list"
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_manager_can_view_users(self):
        self.client.force_login(
            self.manager,
        )

        response = self.client.get(
            reverse(
                "accounts:user_list"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "manager-test",
        )

        self.assertContains(
            response,
            "operator-test",
        )

    def test_operator_cannot_view_users(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "accounts:user_list"
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_manager_can_create_operator(self):
        self.client.force_login(
            self.manager,
        )

        response = self.client.post(
            reverse(
                "accounts:user_create"
            ),
            {
                "username": "new-operator",
                "first_name": "New",
                "last_name": "Operator",
                "email": "operator@example.com",
                "role": OPERATOR_GROUP,
                "password1": "TestPassword123!",
                "password2": "TestPassword123!",
                "is_active": "on",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "accounts:user_list"
            ),
        )

        user = User.objects.get(
            username="new-operator",
        )

        self.assertTrue(
            user.check_password(
                "TestPassword123!"
            )
        )

        self.assertTrue(
            user.groups.filter(
                name=OPERATOR_GROUP,
            ).exists()
        )

        self.assertFalse(
            user.groups.filter(
                name=MANAGER_GROUP,
            ).exists()
        )

    def test_operator_cannot_create_user(self):
        self.client.force_login(
            self.operator,
        )

        response = self.client.get(
            reverse(
                "accounts:user_create"
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_manager_can_promote_operator(self):
        self.client.force_login(
            self.manager,
        )

        response = self.client.post(
            reverse(
                "accounts:user_edit",
                args=[
                    self.operator.pk
                ],
            ),
            {
                "username": (
                    self.operator.username
                ),
                "first_name": (
                    self.operator.first_name
                ),
                "last_name": (
                    self.operator.last_name
                ),
                "email": (
                    self.operator.email
                ),
                "role": MANAGER_GROUP,
                "is_active": "on",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "accounts:user_list"
            ),
        )

        self.operator.refresh_from_db()

        self.assertTrue(
            self.operator.groups.filter(
                name=MANAGER_GROUP,
            ).exists()
        )

        self.assertFalse(
            self.operator.groups.filter(
                name=OPERATOR_GROUP,
            ).exists()
        )

    def test_manager_can_deactivate_other_user(self):
        self.client.force_login(
            self.manager,
        )

        response = self.client.post(
            reverse(
                "accounts:user_edit",
                args=[
                    self.operator.pk
                ],
            ),
            {
                "username": (
                    self.operator.username
                ),
                "first_name": (
                    self.operator.first_name
                ),
                "last_name": (
                    self.operator.last_name
                ),
                "email": (
                    self.operator.email
                ),
                "role": OPERATOR_GROUP,
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "accounts:user_list"
            ),
        )

        self.operator.refresh_from_db()

        self.assertFalse(
            self.operator.is_active
        )

    def test_manager_cannot_deactivate_self(self):
        self.client.force_login(
            self.manager,
        )

        response = self.client.post(
            reverse(
                "accounts:user_edit",
                args=[
                    self.manager.pk
                ],
            ),
            {
                "username": (
                    self.manager.username
                ),
                "first_name": (
                    self.manager.first_name
                ),
                "last_name": (
                    self.manager.last_name
                ),
                "email": (
                    self.manager.email
                ),
                "role": MANAGER_GROUP,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.manager.refresh_from_db()

        self.assertTrue(
            self.manager.is_active
        )

        self.assertContains(
            response,
            (
                "You cannot deactivate "
                "your own account."
            ),
        )

    def test_manager_cannot_demote_self(self):
        self.client.force_login(
            self.manager,
        )

        response = self.client.post(
            reverse(
                "accounts:user_edit",
                args=[
                    self.manager.pk
                ],
            ),
            {
                "username": (
                    self.manager.username
                ),
                "first_name": (
                    self.manager.first_name
                ),
                "last_name": (
                    self.manager.last_name
                ),
                "email": (
                    self.manager.email
                ),
                "role": OPERATOR_GROUP,
                "is_active": "on",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.manager.refresh_from_db()

        self.assertTrue(
            self.manager.groups.filter(
                name=MANAGER_GROUP,
            ).exists()
        )

        self.assertContains(
            response,
            (
                "You cannot remove your own "
                "Manager role."
            ),
        )

    def test_user_search_filters_results(self):
        self.client.force_login(
            self.manager,
        )

        response = self.client.get(
            reverse(
                "accounts:user_list"
            ),
            {
                "q": "operator-test",
            },
        )

        users = list(
            response.context[
                "page"
            ].object_list
        )

        self.assertIn(
            self.operator,
            users,
        )

        self.assertNotIn(
            self.manager,
            users,
        )

    def test_role_filter_returns_operators(self):
        self.client.force_login(
            self.manager,
        )

        response = self.client.get(
            reverse(
                "accounts:user_list"
            ),
            {
                "role": OPERATOR_GROUP,
            },
        )

        users = list(
            response.context[
                "page"
            ].object_list
        )

        self.assertIn(
            self.operator,
            users,
        )

        self.assertNotIn(
            self.manager,
            users,
        )

    def test_superuser_cannot_be_edited_from_interface(self):
        superuser = User.objects.create_superuser(
            username="root",
            password="test-password",
        )

        self.client.force_login(
            self.manager,
        )

        response = self.client.get(
            reverse(
                "accounts:user_edit",
                args=[
                    superuser.pk
                ],
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "accounts:user_list"
            ),
        )

        superuser.refresh_from_db()

        self.assertTrue(
            superuser.is_superuser
        )