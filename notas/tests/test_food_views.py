import io
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from openpyxl import Workbook

from notas.domain.models import Food

User = get_user_model()


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class FoodViewTests(TestCase):

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

    def build_excel_file(self, rows):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Foods"

        worksheet.append(["name", "protein", "carbs", "fat"])

        for row in rows:
            worksheet.append(row)

        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        buffer.name = "foods.xlsx"
        return buffer

    def test_food_list_returns_200_and_shows_user_foods(self):
        food = Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )

        response = self.client.get(
            reverse("food_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Egg")
        self.assertIn("vm", response.context)

    def test_food_detail_returns_200(self):
        food = Food.objects.create(
            name="Rice",
            protein=2,
            carbs=30,
            fat=1,
            created_by=self.user,
        )

        response = self.client.get(
            reverse("food_detail", args=[food.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rice")

    def test_food_create_creates_food(self):
        response = self.client.post(
            reverse("food_create"),
            data={
                "name": "Chicken breast",
                "protein": "31",
                "carbs": "0",
                "fat": "3.6",
            },
        )

        self.assertEqual(response.status_code, 302)

        food = Food.objects.get(name="Chicken breast")
        self.assertEqual(food.created_by, self.user)
        self.assertEqual(food.protein, 31)
        self.assertEqual(food.carbs, 0)
        self.assertEqual(food.fat, 3.6)

    def test_food_edit_updates_food(self):
        food = Food.objects.create(
            name="Old name",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )

        response = self.client.post(
            reverse("food_edit", args=[food.id]),
            data={
                "name": "New name",
                "protein": "12",
                "carbs": "3",
                "fat": "6",
            },
        )

        self.assertEqual(response.status_code, 302)

        food.refresh_from_db()
        self.assertEqual(food.name, "New name")
        self.assertEqual(food.protein, 12)
        self.assertEqual(food.carbs, 3)
        self.assertEqual(food.fat, 6)

    def test_food_edit_only_allows_owner(self):
        other_user = User.objects.create_user(
            username="other",
            email="other@test.com",
            password="12345678",
        )

        food = Food.objects.create(
            name="Protected food",
            protein=10,
            carbs=2,
            fat=5,
            created_by=other_user,
        )

        response = self.client.get(
            reverse("food_edit", args=[food.id])
        )

        self.assertEqual(response.status_code, 404)

    def test_import_foods_creates_multiple_foods_from_excel(self):
        excel_file = self.build_excel_file(
            [
                ["Egg", 10, 2, 5],
                ["Rice", 2, 30, 1],
            ]
        )

        response = self.client.post(
            reverse("import_foods"),
            data={
                "file": excel_file,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Food.objects.filter(name="Egg", created_by=self.user).exists())
        self.assertTrue(Food.objects.filter(name="Rice", created_by=self.user).exists())

    def test_import_foods_rejects_missing_required_columns(self):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Foods"

        worksheet.append(["name", "protein", "fat"])
        worksheet.append(["Egg", 10, 5])

        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        buffer.name = "invalid_foods.xlsx"

        response = self.client.post(
            reverse("import_foods"),
            data={
                "file": buffer,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Food.objects.count(), 0)

    def test_download_food_template_returns_excel_file(self):
        response = self.client.get(
            reverse("download_food_template")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn(
            'attachment; filename="food_import_template.xlsx"',
            response["Content-Disposition"],
        )

    def test_foods_json_returns_serialized_foods(self):
        food = Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )

        response = self.client.get(
            reverse("foods_json")
        )

        self.assertEqual(response.status_code, 200)

        payload = json.loads(response.content)

        self.assertIsInstance(payload, list)
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["id"], food.id)
        self.assertEqual(payload[0]["name"], "Egg")
        self.assertEqual(payload[0]["protein"], 10)
        self.assertEqual(payload[0]["carbs"], 2)
        self.assertEqual(payload[0]["fat"], 5)

    def test_food_edit_prefills_form_with_current_values(self):
        food = Food.objects.create(
            name="Egg",
            protein=10,
            carbs=2,
            fat=5,
            created_by=self.user,
        )

        response = self.client.get(
            reverse("food_edit", args=[food.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Egg"', html=False)
        self.assertContains(response, 'value="10.0"', html=False)
        self.assertContains(response, 'value="2.0"', html=False)
        self.assertContains(response, 'value="5.0"', html=False)
