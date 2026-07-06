from dataclasses import asdict, dataclass
from typing import Iterable

from django.db.models import QuerySet

from notas.application.queries.read_boundaries import get_readable_food_queryset
from notas.domain.constants.nutrition import (
    CARBS_KCAL_PER_GRAM,
    FAT_KCAL_PER_GRAM,
    PROTEIN_KCAL_PER_GRAM,
)


DEFAULT_FOOD_CATALOG_LIMIT = 50
MAX_FOOD_CATALOG_LIMIT = 200


@dataclass(frozen=True)
class FoodCatalogItemDTO:
    food_id: int
    name: str
    protein: float
    carbs: float
    fat: float
    kcal_per_100g: float
    unit: str
    source: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class FoodCatalogDTO:
    foods: list[FoodCatalogItemDTO]
    count: int
    limit: int
    search: str | None

    def as_dict(self) -> dict:
        return {
            "foods": [
                food.as_dict()
                for food in self.foods
            ],
            "count": self.count,
            "limit": self.limit,
            "search": self.search,
        }


def list_food_catalog_for_planning(
    user,
    search: str | None = None,
    limit: int = DEFAULT_FOOD_CATALOG_LIMIT,
) -> FoodCatalogDTO:
    """
    Returns a read-only catalog of operational foods available for AI/MCP planning.

    Despite the historical function name, this query reads only ``notas.Food``.
    It must not import or expose ``food_catalog.CatalogFood``.

    Visibility follows the existing read boundary:
    - system foods;
    - foods created by the current user.

    It excludes private foods created by other users.
    """
    safe_limit = _normalize_limit(limit)
    normalized_search = _normalize_search(search)

    queryset = get_readable_food_queryset(user).order_by("name", "id")

    queryset = _apply_search(
        queryset=queryset,
        search=normalized_search,
    )

    foods = [
        _build_food_catalog_item(
            food=food,
            user=user,
        )
        for food in queryset[:safe_limit]
    ]

    return FoodCatalogDTO(
        foods=foods,
        count=len(foods),
        limit=safe_limit,
        search=normalized_search,
    )


def _apply_search(
    queryset: QuerySet,
    search: str | None,
) -> QuerySet:
    if not search:
        return queryset

    return queryset.filter(name__icontains=search)


def _build_food_catalog_item(
    food,
    user,
) -> FoodCatalogItemDTO:
    protein = float(food.protein)
    carbs = float(food.carbs)
    fat = float(food.fat)

    kcal_per_100g = (
        protein * PROTEIN_KCAL_PER_GRAM
        + carbs * CARBS_KCAL_PER_GRAM
        + fat * FAT_KCAL_PER_GRAM
    )

    return FoodCatalogItemDTO(
        food_id=food.id,
        name=food.name,
        protein=protein,
        carbs=carbs,
        fat=fat,
        kcal_per_100g=kcal_per_100g,
        unit="g",
        source=_resolve_food_source(
            food=food,
            user=user,
        ),
    )


def _resolve_food_source(
    food,
    user,
) -> str:
    if food.is_global or food.created_by_id is None:
        return "system"

    if food.created_by_id == user.id:
        return "user"

    return "unknown"



def _normalize_search(search: str | None) -> str | None:
    if search is None:
        return None

    if not isinstance(search, str):
        return None

    normalized = search.strip()

    return normalized or None


def _normalize_limit(limit: int) -> int:
    if isinstance(limit, bool):
        return DEFAULT_FOOD_CATALOG_LIMIT

    if not isinstance(limit, int):
        return DEFAULT_FOOD_CATALOG_LIMIT

    if limit <= 0:
        return DEFAULT_FOOD_CATALOG_LIMIT

    return min(limit, MAX_FOOD_CATALOG_LIMIT)