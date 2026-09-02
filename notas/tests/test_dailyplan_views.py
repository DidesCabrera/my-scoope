from datetime import time

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from notas.domain.models import DailyPlan, DailyPlanMeal, Meal

User = get_user_model()


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class DailyPlanViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@test.com",
            password="12345678",
        )

        self.client = Client()
        self.client.login(
            username="felipe",
            password="12345678",
        )

    def test_dailyplan_create_creates_draft_dailyplan(self):
        response = self.client.post(
            reverse("dailyplan_create"),
            data={
                "name": "New plan",
            },
        )

        self.assertEqual(response.status_code, 302)

        dailyplan = DailyPlan.objects.get(name="New plan")

        self.assertEqual(dailyplan.created_by, self.user)
        self.assertTrue(dailyplan.is_draft)

    def test_dailyplan_rename_updates_name(self):
        dailyplan = DailyPlan.objects.create(
            name="Old plan name",
            created_by=self.user,
            is_draft=False,
        )

        response = self.client.post(
            reverse("dailyplan_rename", args=[dailyplan.id]),
            data={
                "name": "New plan name",
            },
        )

        self.assertEqual(response.status_code, 302)

        dailyplan.refresh_from_db()
        self.assertEqual(dailyplan.name, "New plan name")

    def test_dailyplan_remove_deletes_dailyplan(self):
        dailyplan = DailyPlan.objects.create(
            name="Plan to remove",
            created_by=self.user,
            is_draft=False,
        )

        response = self.client.post(
            reverse("dailyplan_remove", args=[dailyplan.id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(DailyPlan.objects.filter(id=dailyplan.id).exists())

    def test_dailyplan_meal_hour_is_visible_in_menu_and_meal_titles_only(self):
        dailyplan = DailyPlan.objects.create(
            name="Plan con horarios",
            created_by=self.user,
            is_draft=False,
        )
        meal = Meal.objects.create(
            name="Desayuno",
            created_by=self.user,
            is_draft=False,
        )
        DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal,
            hour=time(7, 5),
            order=1,
        )

        response = self.client.get(reverse("dailyplan_detail", args=[dailyplan.id]))

        self.assertEqual(response.status_code, 200)
        table_item = response.context["vm"]["content"]["main_card"]["table"]["items"][0]
        menu_item = response.context["vm"]["content"]["main_card"]["menu"]["meals"][0]
        child_title = response.context["vm"]["content"]["child_cards"][0]["titulo"]
        menu_html = render_to_string(
            "components/grid_meals_menu.html",
            {"menu": response.context["vm"]["content"]["main_card"]["menu"]},
        )
        active_menu_html = render_to_string(
            "components/grid_calendarized_meals_menu.html",
            {
                "meals": [
                    {
                        "name": "Desayuno",
                        "hour": "07:05",
                        "foods": ["Avena"],
                        "detail_url": "/meal/1/",
                    }
                ]
            },
        )
        self.assertEqual(table_item["rel"]["hour"], "07:05")
        self.assertEqual(menu_item["hour"], "07:05")
        self.assertEqual(child_title["structural_indicators"]["hour"], "07:05")
        for rendered_menu in (menu_html, active_menu_html):
            self.assertIn("data-grid-meal-identity", rendered_menu)
            self.assertIn('class="data-grid-meal-time">07:05</span>', rendered_menu)
            self.assertNotIn("data-grid-meal-hour", rendered_menu)

        for template_name in (
            "components/grid_meals.html",
            "components/grid_meals_edit.html",
            "components/grid_meals_mobile_alloc.html",
            "components/grid_meals_mobile_calories.html",
            "components/grid_meals_mobile_edit.html",
            "components/grid_meals_mobile_macros.html",
        ):
            rendered_panel = render_to_string(
                template_name,
                {"items": [table_item], "dailyplan_id": dailyplan.id},
            )
            self.assertNotIn("data-grid-meal-time", rendered_panel)

        self.assertContains(response, 'class="data-grid-meal-time"', count=1)
        self.assertContains(response, "structural-item--time", count=1)
        self.assertContains(response, 'data-lucide="clock"', count=1)
        self.assertEqual(
            response.context["vm"]["content"]["child_cards"][0]["titulo"][
                "structural_indicators"
            ]["hour"],
            "07:05",
        )

    def test_dailyplan_list_menu_displays_meal_hour_and_refreshes_old_cache(self):
        dailyplan = DailyPlan.objects.create(
            name="Plan visible en la lista",
            created_by=self.user,
            is_draft=False,
            summary_cache={
                "version": 2,
                "menu": [
                    {
                        "meal_name": "Desayuno",
                        "foods": [],
                    }
                ],
            },
        )
        meal = Meal.objects.create(
            name="Desayuno",
            created_by=self.user,
            is_draft=False,
        )
        DailyPlanMeal.objects.create(
            dailyplan=dailyplan,
            meal=meal,
            hour=time(7, 5),
            order=1,
        )

        response = self.client.get(reverse("dailyplan_list"))

        self.assertEqual(response.status_code, 200)
        menu_item = response.context["vm"]["content"]["child_cards"][0]["menu"][
            "meals"
        ][0]
        self.assertEqual(menu_item["hour"], "07:05")
        self.assertContains(response, 'class="data-grid-meal-time">07:05</span>')

        dailyplan.refresh_from_db()
        self.assertEqual(dailyplan.summary_cache["version"], 3)
        self.assertEqual(dailyplan.summary_cache["menu"][0]["hour"], "07:05")

    def test_dailyplan_fork_creates_new_plan_for_logged_user(self):
        author = User.objects.create_user(
            username="author",
            email="author@test.com",
            password="12345678",
        )

        meal = Meal.objects.create(
            name="Original meal",
            created_by=author,
            is_draft=False,
            is_public=True,
            is_forkable=True,
            is_copiable=False,
        )

        original = DailyPlan.objects.create(
            name="Original plan",
            created_by=author,
            is_draft=False,
            is_public=True,
            is_forkable=True,
            is_copiable=False,
        )

        original.dailyplan_meals.create(
            meal=meal,
            order=1,
        )

        response = self.client.post(
            reverse("dailyplan_fork", args=[original.id])
        )

        self.assertEqual(response.status_code, 302)

        forked = DailyPlan.objects.exclude(id=original.id).get()

        self.assertEqual(forked.created_by, self.user)
        self.assertEqual(forked.forked_from, original)
        self.assertEqual(forked.original_author, author)
        self.assertEqual(forked.dailyplan_meals.count(), 1)

        forked_dpm = forked.dailyplan_meals.first()
        self.assertNotEqual(forked_dpm.meal.id, meal.id)
        self.assertEqual(forked_dpm.meal.forked_from, meal)

    def test_dailyplan_configure_redirects_when_user_has_no_distribution_access(self):
        dailyplan = DailyPlan.objects.create(
            name="Config plan",
            created_by=self.user,
            is_draft=False,
        )

        response = self.client.get(
            reverse("dailyplan_configure", args=[dailyplan.id])
        )

        self.assertEqual(response.status_code, 302)

        dailyplan.refresh_from_db()
        self.assertFalse(dailyplan.is_public)
        self.assertTrue(dailyplan.is_forkable)
        self.assertFalse(dailyplan.is_copiable)
