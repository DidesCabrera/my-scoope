from dataclasses import dataclass

from django.db import transaction
from django.db.models import Max

from notas.domain.models import Food


@dataclass(frozen=True)
class FoodCreateResult:
    food: Food


@dataclass(frozen=True)
class FoodUpdateResult:
    food: Food


@dataclass(frozen=True)
class FoodDeleteResult:
    food_id: int


@dataclass(frozen=True)
class FoodBulkCreateResult:
    foods: list[Food]

    @property
    def created_count(self) -> int:
        return len(self.foods)


def _next_food_list_order(user) -> int:
    current_max = (
        Food.objects
        .filter(created_by=user, is_active=True)
        .aggregate(max_order=Max("list_order"))
        .get("max_order")
    )
    return (current_max or 0) + 1


@transaction.atomic
def create_food(
    *,
    user,
    name,
    protein,
    carbs,
    fat,
) -> FoodCreateResult:
    food = Food.objects.create(
        name=(name or "").strip(),
        protein=protein,
        carbs=carbs,
        fat=fat,
        created_by=user,
        list_order=_next_food_list_order(user),
    )

    return FoodCreateResult(
        food=food,
    )


@transaction.atomic
def update_food(
    *,
    food: Food,
    name,
    protein,
    carbs,
    fat,
) -> FoodUpdateResult:
    food.name = (name or "").strip()
    food.protein = protein
    food.carbs = carbs
    food.fat = fat

    food.save(
        update_fields=[
            "name",
            "protein",
            "carbs",
            "fat",
        ]
    )

    return FoodUpdateResult(
        food=food,
    )


@transaction.atomic
def delete_food(
    *,
    food: Food,
) -> FoodDeleteResult:
    food_id = food.id
    food.is_active = False
    food.save(update_fields=["is_active"])

    return FoodDeleteResult(food_id=food_id)


@transaction.atomic
def bulk_create_foods(
    *,
    user,
    rows,
) -> FoodBulkCreateResult:
    foods = []
    next_order = _next_food_list_order(user)

    for offset, row in enumerate(rows):
        food = Food.objects.create(
            name=(row["name"] or "").strip(),
            protein=row["protein"],
            carbs=row["carbs"],
            fat=row["fat"],
            created_by=user,
            list_order=next_order + offset,
        )
        foods.append(food)

    return FoodBulkCreateResult(
        foods=foods,
    )
