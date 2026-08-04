from django.core.management.base import BaseCommand

from notas.application.services.nutrition.food_aggregation import build_meal_foods_projection
from notas.domain.models import Meal


class Command(BaseCommand):
    help = "Recalculate cached nutrition values for all meals"

    def handle(self, *args, **options):

        meals = Meal.objects.prefetch_related("meal_food_set__food")
        total = meals.count()

        self.stdout.write(f"Recalculating {total} meals...\n")

        for i, meal in enumerate(meals, start=1):

            protein = meal.protein
            carbs = meal.carbs
            fat = meal.fat

            kcal_protein = meal.kcal_protein
            kcal_carbs = meal.kcal_carbs
            kcal_fat = meal.kcal_fat
            total_kcal = meal.total_kcal

            alloc = meal.alloc

            foods_projection = build_meal_foods_projection(meal)

            Meal.objects.filter(id=meal.id).update(
                protein_cached=protein,
                carbs_cached=carbs,
                fat_cached=fat,

                kcal_protein_cached=kcal_protein,
                kcal_carbs_cached=kcal_carbs,
                kcal_fat_cached=kcal_fat,
                total_kcal_cached=total_kcal,

                alloc_protein_cached=alloc["protein"],
                alloc_carbs_cached=alloc["carbs"],
                alloc_fat_cached=alloc["fat"],

                foods_aggregation_cached=foods_projection,
            )

            if i % 25 == 0:
                self.stdout.write(f"{i}/{total} meals processed")

        self.stdout.write(self.style.SUCCESS("\nBackfill complete ✅"))
