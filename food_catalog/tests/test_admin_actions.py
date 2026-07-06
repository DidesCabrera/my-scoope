from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from food_catalog.admin import CatalogFoodAdmin
from food_catalog.models import CatalogFood, CatalogFoodPortion, CatalogFoodSource


class CatalogFoodAdminActionTests(TestCase):
    def test_publish_action_marks_catalog_food_as_published(self):
        user = get_user_model().objects.create_superuser(
            username="curator",
            email="curator@example.com",
            password="x",
        )
        catalog_food = _create_catalog_food()
        _make_publishable(catalog_food)
        request = RequestFactory().post("/admin/food_catalog/catalogfood/")
        request.user = user
        request._messages = _DummyMessages()
        admin = CatalogFoodAdmin(CatalogFood, AdminSite())

        admin.mark_as_published(request, CatalogFood.objects.filter(pk=catalog_food.pk))

        catalog_food.refresh_from_db()
        self.assertEqual(catalog_food.status, CatalogFood.STATUS_PUBLISHED)
        self.assertEqual(catalog_food.reviewed_by, user)
        self.assertIsNotNone(catalog_food.reviewed_at)
        self.assertIsNotNone(catalog_food.published_at)

    def test_publish_action_blocks_catalog_food_without_publication_evidence(self):
        user = get_user_model().objects.create_superuser(
            username="curator",
            email="curator@example.com",
            password="x",
        )
        catalog_food = _create_catalog_food()
        request = RequestFactory().post("/admin/food_catalog/catalogfood/")
        request.user = user
        request._messages = _DummyMessages()
        admin = CatalogFoodAdmin(CatalogFood, AdminSite())

        admin.mark_as_published(request, CatalogFood.objects.filter(pk=catalog_food.pk))

        catalog_food.refresh_from_db()
        self.assertEqual(catalog_food.status, CatalogFood.STATUS_REVIEWED)
        self.assertIsNone(catalog_food.reviewed_by)
        self.assertIsNone(catalog_food.reviewed_at)
        self.assertIsNone(catalog_food.published_at)

    def test_pending_review_action_updates_status(self):
        catalog_food = _create_catalog_food()
        request = RequestFactory().post("/admin/food_catalog/catalogfood/")
        request.user = get_user_model().objects.create_user(username="editor")
        request._messages = _DummyMessages()
        admin = CatalogFoodAdmin(CatalogFood, AdminSite())

        admin.mark_as_pending_review(request, CatalogFood.objects.filter(pk=catalog_food.pk))

        catalog_food.refresh_from_db()
        self.assertEqual(catalog_food.status, CatalogFood.STATUS_PENDING_REVIEW)

    def test_verified_action_uses_protected_workflow(self):
        catalog_food = _create_catalog_food(status=CatalogFood.STATUS_PENDING_REVIEW)
        request = RequestFactory().post("/admin/food_catalog/catalogfood/")
        request.user = get_user_model().objects.create_user(username="editor")
        request._messages = _DummyMessages()
        admin = CatalogFoodAdmin(CatalogFood, AdminSite())

        admin.mark_as_verified(request, CatalogFood.objects.filter(pk=catalog_food.pk))

        catalog_food.refresh_from_db()
        self.assertEqual(catalog_food.status, CatalogFood.STATUS_PENDING_REVIEW)

    def test_reviewed_then_verified_actions_follow_workflow(self):
        user = get_user_model().objects.create_user(username="editor")
        catalog_food = _create_catalog_food(status=CatalogFood.STATUS_PENDING_REVIEW)
        request = RequestFactory().post("/admin/food_catalog/catalogfood/")
        request.user = user
        request._messages = _DummyMessages()
        admin = CatalogFoodAdmin(CatalogFood, AdminSite())

        admin.mark_as_reviewed(request, CatalogFood.objects.filter(pk=catalog_food.pk))
        admin.mark_as_verified(request, CatalogFood.objects.filter(pk=catalog_food.pk))

        catalog_food.refresh_from_db()
        self.assertEqual(catalog_food.status, CatalogFood.STATUS_VERIFIED)
        self.assertEqual(catalog_food.reviewed_by, user)
        self.assertIsNotNone(catalog_food.reviewed_at)


class _DummyMessages:
    def add(self, level, message, extra_tags=""):
        return None


def _create_catalog_food(*, status: str = CatalogFood.STATUS_REVIEWED) -> CatalogFood:
    return CatalogFood.objects.create(
        display_name="Avena",
        canonical_name="avena",
        protein_g_per_100g=Decimal("16.900"),
        carbs_g_per_100g=Decimal("66.300"),
        fat_g_per_100g=Decimal("6.900"),
        status=status,
        source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
        data_quality_score=90,
    )


def _make_publishable(catalog_food: CatalogFood) -> None:
    CatalogFoodSource.objects.create(
        catalog_food=catalog_food,
        source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
        source_name="manual-curation",
        source_food_id=f"manual-{catalog_food.pk}",
        license_status=CatalogFoodSource.LICENSE_ALLOWED,
    )
    CatalogFoodPortion.objects.create(
        catalog_food=catalog_food,
        label="100 g",
        grams=Decimal("100.000"),
        is_default=True,
    )
