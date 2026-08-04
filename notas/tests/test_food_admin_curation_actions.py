from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase

from notas.admin import FoodAdmin
from notas.admin_food_actions import (
    mark_foods_as_active,
    mark_foods_as_core,
    mark_foods_as_extended,
    mark_foods_as_hidden,
    mark_foods_as_inactive,
    mark_foods_as_rejected,
    mark_foods_as_unverified,
    mark_foods_as_verified,
)
from notas.domain.models import Food

User = get_user_model()


class FoodAdminCurationActionsTests(TestCase):
    def setUp(self):
        self.request_factory = RequestFactory()
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="12345678",
        )

        self.food = Food.objects.create(
            name="Imported Oats",
            canonical_name="imported oats",
            protein=16.9,
            carbs=66.3,
            fat=6.9,
            created_by=None,
            is_global=True,
            is_verified=False,
            is_active=True,
            visibility=Food.VISIBILITY_EXTENDED,
            data_quality_score=75,
        )

        self.modeladmin = FoodAdmin(
            Food,
            AdminSite(),
        )

    def _request(self):
        request = self.request_factory.post("/admin/notas/food/")
        request.user = self.admin_user

        setattr(request, "session", {})
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        return request

    def _queryset(self):
        return Food.objects.filter(id=self.food.id)

    def _refresh_food(self):
        self.food.refresh_from_db()
        return self.food

    def test_mark_foods_as_core_sets_core_and_active(self):
        mark_foods_as_core(
            self.modeladmin,
            self._request(),
            self._queryset(),
        )

        food = self._refresh_food()

        self.assertEqual(food.visibility, Food.VISIBILITY_CORE)
        self.assertTrue(food.is_active)

    def test_mark_foods_as_extended_sets_extended_and_active(self):
        self.food.visibility = Food.VISIBILITY_HIDDEN
        self.food.is_active = False
        self.food.save(update_fields=["visibility", "is_active"])

        mark_foods_as_extended(
            self.modeladmin,
            self._request(),
            self._queryset(),
        )

        food = self._refresh_food()

        self.assertEqual(food.visibility, Food.VISIBILITY_EXTENDED)
        self.assertTrue(food.is_active)

    def test_mark_foods_as_hidden_sets_hidden(self):
        mark_foods_as_hidden(
            self.modeladmin,
            self._request(),
            self._queryset(),
        )

        food = self._refresh_food()

        self.assertEqual(food.visibility, Food.VISIBILITY_HIDDEN)

    def test_mark_foods_as_rejected_sets_rejected_and_inactive(self):
        mark_foods_as_rejected(
            self.modeladmin,
            self._request(),
            self._queryset(),
        )

        food = self._refresh_food()

        self.assertEqual(food.visibility, Food.VISIBILITY_REJECTED)
        self.assertFalse(food.is_active)

    def test_mark_foods_as_verified_sets_verified(self):
        mark_foods_as_verified(
            self.modeladmin,
            self._request(),
            self._queryset(),
        )

        food = self._refresh_food()

        self.assertTrue(food.is_verified)

    def test_mark_foods_as_unverified_sets_unverified(self):
        self.food.is_verified = True
        self.food.save(update_fields=["is_verified"])

        mark_foods_as_unverified(
            self.modeladmin,
            self._request(),
            self._queryset(),
        )

        food = self._refresh_food()

        self.assertFalse(food.is_verified)

    def test_mark_foods_as_active_sets_active(self):
        self.food.is_active = False
        self.food.save(update_fields=["is_active"])

        mark_foods_as_active(
            self.modeladmin,
            self._request(),
            self._queryset(),
        )

        food = self._refresh_food()

        self.assertTrue(food.is_active)

    def test_mark_foods_as_inactive_sets_inactive(self):
        mark_foods_as_inactive(
            self.modeladmin,
            self._request(),
            self._queryset(),
        )

        food = self._refresh_food()

        self.assertFalse(food.is_active)

    def test_food_admin_exposes_curation_actions(self):
        action_names = {
            action.__name__
            for action in self.modeladmin.actions
        }

        self.assertIn("mark_foods_as_core", action_names)
        self.assertIn("mark_foods_as_extended", action_names)
        self.assertIn("mark_foods_as_hidden", action_names)
        self.assertIn("mark_foods_as_rejected", action_names)
        self.assertIn("mark_foods_as_verified", action_names)
        self.assertIn("mark_foods_as_unverified", action_names)
        self.assertIn("mark_foods_as_active", action_names)
        self.assertIn("mark_foods_as_inactive", action_names)