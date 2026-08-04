from dataclasses import asdict, dataclass

from django.db.models import Case, IntegerField, Q, QuerySet, Value, When

from notas.domain.models import Food

DEFAULT_GLOBAL_FOOD_LIMIT = 50
MAX_GLOBAL_FOOD_LIMIT = 200


@dataclass(frozen=True)
class GlobalFoodListItemDTO:
    id: int
    name: str
    canonical_name: str
    food_group: str
    food_subgroup: str
    visibility: str
    is_verified: bool
    data_quality_score: int
    protein: float
    carbs: float
    fat: float
    total_kcal: float
    source: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class GlobalFoodListDTO:
    foods: list[GlobalFoodListItemDTO]
    count: int
    limit: int
    search: str | None
    include_extended: bool

    def as_dict(self) -> dict:
        return {
            "foods": [
                food.as_dict()
                for food in self.foods
            ],
            "count": self.count,
            "limit": self.limit,
            "search": self.search,
            "include_extended": self.include_extended,
        }


def get_visible_global_food_queryset(
    *,
    include_extended: bool = True,
) -> QuerySet:
    """
    Return global foods that may be exposed to product surfaces.

    This query intentionally excludes:
    - user-created foods
    - inactive foods
    - hidden foods
    - rejected foods

    Visibility rule:
    - core is always included
    - extended is included only when include_extended=True
    """

    allowed_visibility = [Food.VISIBILITY_CORE]

    if include_extended:
        allowed_visibility.append(Food.VISIBILITY_EXTENDED)

    return (
        Food.objects
        .filter(
            is_global=True,
            is_active=True,
            visibility__in=allowed_visibility,
        )
        .annotate(
            visibility_priority=Case(
                When(visibility=Food.VISIBILITY_CORE, then=Value(0)),
                When(visibility=Food.VISIBILITY_EXTENDED, then=Value(1)),
                default=Value(9),
                output_field=IntegerField(),
            ),
            verified_priority=Case(
                When(is_verified=True, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
        )
        .order_by(
            "visibility_priority",
            "verified_priority",
            "name",
            "id",
        )
        .distinct()
    )


def list_global_foods(
    *,
    search: str | None = None,
    limit: int = DEFAULT_GLOBAL_FOOD_LIMIT,
    include_extended: bool = True,
) -> GlobalFoodListDTO:
    """
    Return visible global foods as DTOs.

    This is the read contract that future picker/catalog surfaces should use
    before integrating global foods into the UI.
    """

    safe_limit = _normalize_limit(limit)
    normalized_search = _normalize_search(search)

    foods = get_visible_global_food_queryset(
        include_extended=include_extended,
    )

    foods = _apply_global_food_search(
        queryset=foods,
        search=normalized_search,
    )

    items = [
        build_global_food_list_item_dto(food)
        for food in foods[:safe_limit]
    ]

    return GlobalFoodListDTO(
        foods=items,
        count=len(items),
        limit=safe_limit,
        search=normalized_search,
        include_extended=include_extended,
    )


def search_global_foods(
    *,
    search: str,
    limit: int = DEFAULT_GLOBAL_FOOD_LIMIT,
    include_extended: bool = True,
) -> list[GlobalFoodListItemDTO]:
    """
    Convenience wrapper for search-only use cases.
    """

    result = list_global_foods(
        search=search,
        limit=limit,
        include_extended=include_extended,
    )

    return result.foods


def build_global_food_list_item_dto(food: Food) -> GlobalFoodListItemDTO:
    return GlobalFoodListItemDTO(
        id=food.id,
        name=food.name,
        canonical_name=food.canonical_name,
        food_group=food.food_group,
        food_subgroup=food.food_subgroup,
        visibility=food.visibility,
        is_verified=food.is_verified,
        data_quality_score=food.data_quality_score,
        protein=float(food.protein),
        carbs=float(food.carbs),
        fat=float(food.fat),
        total_kcal=float(food.total_kcal),
        source=_resolve_source(food),
    )


def _apply_global_food_search(
    *,
    queryset: QuerySet,
    search: str | None,
) -> QuerySet:
    if not search:
        return queryset

    return queryset.filter(
        Q(name__icontains=search)
        | Q(canonical_name__icontains=search)
        | Q(aliases__name__icontains=search)
        | Q(aliases__normalized_name__icontains=search)
    )


def _resolve_source(food: Food) -> str:
    if hasattr(food, "source_metadata"):
        return food.source_metadata.source

    return "global"


def _normalize_search(search: str | None) -> str | None:
    if search is None:
        return None

    if not isinstance(search, str):
        return None

    normalized = search.strip()

    return normalized or None


def _normalize_limit(limit: int) -> int:
    if isinstance(limit, bool):
        return DEFAULT_GLOBAL_FOOD_LIMIT

    if not isinstance(limit, int):
        return DEFAULT_GLOBAL_FOOD_LIMIT

    if limit <= 0:
        return DEFAULT_GLOBAL_FOOD_LIMIT

    return min(limit, MAX_GLOBAL_FOOD_LIMIT)