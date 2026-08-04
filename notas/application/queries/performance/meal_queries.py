from django.db.models import ExpressionWrapper, F, FloatField, Sum

from notas.domain.constants.nutrition import (
    CARBS_KCAL_PER_GRAM,
    FAT_KCAL_PER_GRAM,
    PROTEIN_KCAL_PER_GRAM,
)
from notas.domain.models import Meal


def meals_with_kcal():
    return (
        Meal.objects
        .prefetch_related("meal_food_set", "meal_food_set__food")
        .annotate(
            total_kcal_sql=Sum(
                ExpressionWrapper(
                    (F("meal_food_set__quantity") / 100.0)
                    * (
                        F("meal_food_set__food__protein")
                        * PROTEIN_KCAL_PER_GRAM
                        + F("meal_food_set__food__carbs")
                        * CARBS_KCAL_PER_GRAM
                        + F("meal_food_set__food__fat")
                        * FAT_KCAL_PER_GRAM
                    ),
                    output_field=FloatField(),
                )
            )
        )
    )
