from django.contrib.auth import get_user_model
from django.test import TestCase

from notas.application.queries.food_picker_queries import (
    DEFAULT_FOOD_PICKER_LIMIT,
    MAX_FOOD_PICKER_LIMIT,
    PICKER_SOURCE_GLOBAL,
    PICKER_SOURCE_USER,
    get_food_picker_queryset,
    list_food_picker_items,
    search_food_picker_items,
)
from notas.domain.models import (
    Food,
    FoodAlias,
    FoodLocalizedName,
    FoodSourceMetadata,
)

User = get_user_model()


class FoodPickerQueryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@test.com",
            password="12345678",
        )

        self.other_user = User.objects.create_user(
            username="other",
            email="other@test.com",
            password="12345678",
        )

        self.user_food = Food.objects.create(
            name="User Egg",
            canonical_name="user egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
            is_global=False,
            is_active=True,
            visibility=Food.VISIBILITY_EXTENDED,
            data_quality_score=10,
        )

        self.other_user_food = Food.objects.create(
            name="Other User Food",
            canonical_name="other user food",
            protein=1,
            carbs=1,
            fat=1,
            created_by=self.other_user,
            is_global=False,
            is_active=True,
            visibility=Food.VISIBILITY_EXTENDED,
            data_quality_score=10,
        )

        self.core_global_food = Food.objects.create(
            name="Global Oats Core",
            canonical_name="global oats core",
            protein=16.9,
            carbs=66.3,
            fat=6.9,
            created_by=None,
            is_global=True,
            is_verified=True,
            is_active=True,
            visibility=Food.VISIBILITY_CORE,
            data_quality_score=90,
        )

        FoodSourceMetadata.objects.create(
            food=self.core_global_food,
            source=FoodSourceMetadata.SOURCE_USDA,
            source_food_id="1001",
            source_dataset="foundation_foods",
            source_version="2026-04",
        )

        FoodAlias.objects.create(
            food=self.core_global_food,
            name="Avena",
            normalized_name="avena",
            language="es",
            country="CL",
        )

        self.extended_global_food = Food.objects.create(
            name="Global Chicken Extended",
            canonical_name="global chicken extended",
            protein=31,
            carbs=0,
            fat=3.6,
            created_by=None,
            is_global=True,
            is_verified=False,
            is_active=True,
            visibility=Food.VISIBILITY_EXTENDED,
            data_quality_score=75,
        )

        self.lower_quality_extended_global_food = Food.objects.create(
            name="Global Banana Extended",
            canonical_name="global banana extended",
            protein=1,
            carbs=23,
            fat=0.3,
            created_by=None,
            is_global=True,
            is_verified=False,
            is_active=True,
            visibility=Food.VISIBILITY_EXTENDED,
            data_quality_score=65,
        )

        self.hidden_global_food = Food.objects.create(
            name="Hidden Banana",
            canonical_name="hidden banana",
            protein=1,
            carbs=23,
            fat=0.3,
            created_by=None,
            is_global=True,
            is_active=True,
            visibility=Food.VISIBILITY_HIDDEN,
        )

        self.rejected_global_food = Food.objects.create(
            name="Rejected Food",
            canonical_name="rejected food",
            protein=1,
            carbs=1,
            fat=1,
            created_by=None,
            is_global=True,
            is_active=True,
            visibility=Food.VISIBILITY_REJECTED,
        )

        self.inactive_global_food = Food.objects.create(
            name="Inactive Global Food",
            canonical_name="inactive global food",
            protein=1,
            carbs=1,
            fat=1,
            created_by=None,
            is_global=True,
            is_active=False,
            visibility=Food.VISIBILITY_CORE,
        )

    def test_food_picker_queryset_includes_user_and_visible_global_foods(self):
        foods = list(get_food_picker_queryset(self.user))

        self.assertIn(self.user_food, foods)
        self.assertIn(self.core_global_food, foods)
        self.assertIn(self.extended_global_food, foods)

    def test_food_picker_queryset_excludes_private_foods_from_other_users(self):
        foods = list(get_food_picker_queryset(self.user))

        self.assertNotIn(self.other_user_food, foods)

    def test_food_picker_queryset_excludes_hidden_rejected_and_inactive_global_foods(self):
        foods = list(get_food_picker_queryset(self.user))

        self.assertNotIn(self.hidden_global_food, foods)
        self.assertNotIn(self.rejected_global_food, foods)
        self.assertNotIn(self.inactive_global_food, foods)

    def test_food_picker_queryset_orders_user_foods_before_global_foods(self):
        foods = list(get_food_picker_queryset(self.user))

        self.assertEqual(foods[0], self.user_food)

    def test_food_picker_queryset_orders_core_global_before_extended_global(self):
        foods = list(get_food_picker_queryset(self.user))

        core_index = foods.index(self.core_global_food)
        extended_index = foods.index(self.extended_global_food)

        self.assertLess(core_index, extended_index)

    def test_food_picker_queryset_orders_higher_quality_extended_before_lower_quality(self):
        foods = list(get_food_picker_queryset(self.user))

        higher_quality_index = foods.index(self.extended_global_food)
        lower_quality_index = foods.index(self.lower_quality_extended_global_food)

        self.assertLess(higher_quality_index, lower_quality_index)

    def test_list_food_picker_items_returns_enriched_contract(self):
        result = list_food_picker_items(user=self.user)

        data = result.as_dict()

        self.assertEqual(data["count"], 4)
        self.assertEqual(data["limit"], DEFAULT_FOOD_PICKER_LIMIT)
        self.assertIsNone(data["search"])

        first_item = data["foods"][0]

        self.assertIn("id", first_item)
        self.assertIn("name", first_item)
        self.assertIn("display_name", first_item)
        self.assertIn("protein", first_item)
        self.assertIn("carbs", first_item)
        self.assertIn("fat", first_item)
        self.assertIn("total_kcal", first_item)
        self.assertIn("alloc", first_item)
        self.assertIn("picker_source", first_item)
        self.assertIn("picker_label", first_item)
        self.assertIn("is_user_food", first_item)
        self.assertIn("is_global_food", first_item)
        self.assertIn("is_verified", first_item)
        self.assertIn("visibility", first_item)
        self.assertIn("data_quality_score", first_item)
        self.assertIn("source", first_item)
        self.assertIn("search_text", first_item)

    def test_list_food_picker_items_marks_user_food(self):
        result = list_food_picker_items(
            user=self.user,
            search="User Egg",
        )

        item = result.foods[0]

        self.assertEqual(item.picker_source, PICKER_SOURCE_USER)
        self.assertEqual(item.picker_label, "Tu alimento")
        self.assertTrue(item.is_user_food)
        self.assertFalse(item.is_global_food)
        self.assertEqual(item.source, PICKER_SOURCE_USER)

    def test_list_food_picker_items_marks_global_food(self):
        result = list_food_picker_items(
            user=self.user,
            search="oats",
        )

        item = result.foods[0]

        self.assertEqual(item.picker_source, PICKER_SOURCE_GLOBAL)
        self.assertEqual(item.picker_label, "Global")
        self.assertFalse(item.is_user_food)
        self.assertTrue(item.is_global_food)
        self.assertTrue(item.is_verified)
        self.assertEqual(item.visibility, Food.VISIBILITY_CORE)
        self.assertEqual(item.source, FoodSourceMetadata.SOURCE_USDA)

    def test_list_food_picker_items_searches_by_alias(self):
        result = list_food_picker_items(
            user=self.user,
            search="avena",
        )

        self.assertEqual(result.count, 1)
        self.assertEqual(result.foods[0].name, "Global Oats Core")

    def test_search_food_picker_items_returns_items(self):
        foods = search_food_picker_items(
            user=self.user,
            search="chicken",
        )

        self.assertEqual(len(foods), 1)
        self.assertEqual(foods[0].name, "Global Chicken Extended")

    def test_list_food_picker_items_respects_limit(self):
        result = list_food_picker_items(
            user=self.user,
            limit=1,
        )

        self.assertEqual(result.count, 1)
        self.assertEqual(result.limit, 1)

    def test_list_food_picker_items_normalizes_invalid_limit(self):
        result = list_food_picker_items(
            user=self.user,
            limit=0,
        )

        self.assertEqual(result.limit, DEFAULT_FOOD_PICKER_LIMIT)

    def test_list_food_picker_items_caps_limit(self):
        result = list_food_picker_items(
            user=self.user,
            limit=999,
        )

        self.assertEqual(result.limit, MAX_FOOD_PICKER_LIMIT)

    def test_list_food_picker_items_finds_usda_food_by_spanish_alias(self):
        result = list_food_picker_items(
            user=self.user,
            search="avena",
        )

        self.assertEqual(result.count, 1)
        self.assertEqual(result.foods[0].name, self.core_global_food.name)

    def test_promoted_core_global_foods_are_prioritized_in_picker(self):
        self.extended_global_food.visibility = Food.VISIBILITY_CORE
        self.extended_global_food.is_verified = True
        self.extended_global_food.save(
            update_fields=[
                "visibility",
                "is_verified",
            ]
        )

        result = list_food_picker_items(
            user=self.user,
        )

        global_items = [
            food
            for food in result.foods
            if food.is_global_food
        ]

        self.assertEqual(global_items[0].visibility, Food.VISIBILITY_CORE)
        self.assertTrue(global_items[0].is_verified)

    def test_list_food_picker_items_includes_search_text_with_aliases(self):
        result = list_food_picker_items(
            user=self.user,
            search="avena",
        )

        item = result.foods[0]

        self.assertIn("global oats core", item.search_text)
        self.assertIn("avena", item.search_text)

    def test_list_food_picker_items_uses_name_as_display_name_without_localized_name(self):
        result = list_food_picker_items(
            user=self.user,
            search="chicken",
        )

        item = result.foods[0]

        self.assertEqual(item.name, "Global Chicken Extended")
        self.assertEqual(item.display_name, "Global Chicken Extended")

    def test_list_food_picker_items_uses_primary_localized_name_as_display_name(self):
        FoodLocalizedName.objects.create(
            food=self.core_global_food,
            name="Avena",
            normalized_name="avena",
            language="es",
            country="CL",
            is_primary=True,
        )

        result = list_food_picker_items(
            user=self.user,
            search="oats",
        )

        item = result.foods[0]

        self.assertEqual(item.name, "Global Oats Core")
        self.assertEqual(item.display_name, "Avena")

    def test_list_food_picker_items_searches_by_localized_name(self):
        FoodLocalizedName.objects.create(
            food=self.extended_global_food,
            name="Pechuga de pollo cocida",
            normalized_name="pechuga de pollo cocida",
            language="es",
            country="CL",
            is_primary=True,
        )

        result = list_food_picker_items(
            user=self.user,
            search="pechuga",
        )

        self.assertEqual(result.count, 1)
        self.assertEqual(result.foods[0].name, "Global Chicken Extended")
        self.assertEqual(result.foods[0].display_name, "Pechuga de pollo cocida")



    def test_core_seed_localized_name_is_used_as_display_name(self):
        FoodLocalizedName.objects.create(
            food=self.extended_global_food,
            name="Pechuga de pollo cocida",
            normalized_name="pechuga de pollo cocida",
            language="es",
            country="CL",
            is_primary=True,
        )

        result = list_food_picker_items(
            user=self.user,
            search="chicken",
        )

        item = result.foods[0]

        self.assertEqual(item.name, "Global Chicken Extended")
        self.assertEqual(item.display_name, "Pechuga de pollo cocida")


    def test_list_food_picker_items_includes_localized_names_in_search_text(self):
        FoodLocalizedName.objects.create(
            food=self.extended_global_food,
            name="Pechuga de pollo cocida",
            normalized_name="pechuga de pollo cocida",
            language="es",
            country="CL",
            is_primary=True,
        )

        result = list_food_picker_items(
            user=self.user,
            search="pechuga",
        )

        item = result.foods[0]

        self.assertIn("pechuga de pollo cocida", item.search_text)