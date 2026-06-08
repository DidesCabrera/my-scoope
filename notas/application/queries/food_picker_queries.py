from dataclasses import asdict, dataclass

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Case, IntegerField, Q, QuerySet, Value, When

from notas.application.services.food_imports.localized_names import (
    resolve_food_display_name,
)
from notas.domain.models import Food, MealFood


PICKER_SOURCE_USER = "user"
PICKER_SOURCE_GLOBAL = "global"
PICKER_SOURCE_SYSTEM = "system"

DEFAULT_FOOD_PICKER_LIMIT = 80
MAX_FOOD_PICKER_LIMIT = 250


@dataclass(frozen=True)
class FoodPickerItemDTO:
    id: int
    name: str
    display_name: str
    protein: float
    carbs: float
    fat: float
    total_kcal: float
    alloc: dict
    picker_source: str
    picker_label: str
    is_user_food: bool
    is_global_food: bool
    is_verified: bool
    visibility: str
    data_quality_score: int
    source: str
    search_text: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class FoodPickerListDTO:
    foods: list[FoodPickerItemDTO]
    count: int
    limit: int
    search: str | None

    def as_dict(self) -> dict:
        return {
            "foods": [food.as_dict() for food in self.foods],
            "count": self.count,
            "limit": self.limit,
            "search": self.search,
        }


def get_food_picker_queryset(user) -> QuerySet:
    """
    Return foods available for food picker surfaces.

    Includes:
    - foods created by the current user;
    - active global visible foods;
    - active legacy system foods created without user, if visible.

    Excludes:
    - private foods from other users;
    - inactive global/system foods;
    - hidden global/system foods;
    - rejected global/system foods.

    Ordering rule:
    1. user foods
    2. core global/system foods
    3. extended global/system foods
    4. verified before non-verified
    5. higher quality score first
    6. name
    7. id
    """

    visible_global_values = [
        Food.VISIBILITY_CORE,
        Food.VISIBILITY_EXTENDED,
    ]

    return (
        Food.objects
        .filter(
            Q(created_by=user)
            | Q(
                Q(is_global=True) | Q(created_by__isnull=True),
                is_active=True,
                visibility__in=visible_global_values,
            )
        )
        .select_related("source_metadata")
        .prefetch_related(
            "aliases",
            "localized_names",
        )
        .annotate(
            picker_source_priority=Case(
                When(created_by=user, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
            picker_visibility_priority=Case(
                When(visibility=Food.VISIBILITY_CORE, then=Value(0)),
                When(visibility=Food.VISIBILITY_EXTENDED, then=Value(1)),
                default=Value(9),
                output_field=IntegerField(),
            ),
            picker_verified_priority=Case(
                When(is_verified=True, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
        )
        .distinct()
        .order_by(
            "picker_source_priority",
            "picker_visibility_priority",
            "picker_verified_priority",
            "-data_quality_score",
            "name",
            "id",
        )
    )


def list_food_picker_items(
    *,
    user,
    search: str | None = None,
    limit: int = DEFAULT_FOOD_PICKER_LIMIT,
) -> FoodPickerListDTO:
    """
    Return food picker items as DTOs.

    This is the contract that picker payload builders and JSON endpoints
    should use when they need enriched metadata for UI labels/badges/display.
    """

    safe_limit = _normalize_limit(limit)
    normalized_search = _normalize_search(search)

    foods = get_food_picker_queryset(user)

    foods = _apply_food_picker_search(
        queryset=foods,
        search=normalized_search,
    )

    items = [
        build_food_picker_item_dto(
            food=food,
            user=user,
        )
        for food in foods[:safe_limit]
    ]

    return FoodPickerListDTO(
        foods=items,
        count=len(items),
        limit=safe_limit,
        search=normalized_search,
    )


def search_food_picker_items(
    *,
    user,
    search: str,
    limit: int = DEFAULT_FOOD_PICKER_LIMIT,
) -> list[FoodPickerItemDTO]:
    result = list_food_picker_items(
        user=user,
        search=search,
        limit=limit,
    )

    return result.foods


def get_food_picker_item_by_id(
    *,
    user,
    food_id: int,
) -> FoodPickerItemDTO | None:
    """
    Return one food item for picker edit flows.

    The normal picker queryset intentionally excludes hidden/inactive/rejected
    global foods. However, a user may already have one of those foods inside a
    meal created before the catalog visibility changed. In that case, editing
    the existing MealFood still needs a complete DTO to render the picker
    preview.
    """

    food = (
        get_food_picker_queryset(user)
        .filter(id=food_id)
        .first()
    )

    if food is None and _user_uses_food_in_owned_meal(
        user=user,
        food_id=food_id,
    ):
        food = (
            Food.objects
            .filter(id=food_id)
            .select_related("source_metadata")
            .prefetch_related(
                "aliases",
                "localized_names",
            )
            .first()
        )

    if food is None:
        return None

    return build_food_picker_item_dto(
        food=food,
        user=user,
    )


def _user_uses_food_in_owned_meal(
    *,
    user,
    food_id: int,
) -> bool:
    return MealFood.objects.filter(
        food_id=food_id,
        meal__created_by=user,
    ).exists()


def build_food_picker_item_dto(
    *,
    food: Food,
    user,
) -> FoodPickerItemDTO:
    picker_source = resolve_food_picker_source(
        food=food,
        user=user,
    )

    return FoodPickerItemDTO(
        id=food.id,
        name=food.name,
        display_name=resolve_food_picker_display_name(food),
        protein=float(food.protein),
        carbs=float(food.carbs),
        fat=float(food.fat),
        total_kcal=float(food.total_kcal),
        alloc=food.alloc,
        picker_source=picker_source,
        picker_label=resolve_food_picker_label(picker_source),
        is_user_food=picker_source == PICKER_SOURCE_USER,
        is_global_food=picker_source in {
            PICKER_SOURCE_GLOBAL,
            PICKER_SOURCE_SYSTEM,
        },
        is_verified=food.is_verified,
        visibility=food.visibility,
        data_quality_score=food.data_quality_score,
        source=_resolve_source(food),
        search_text=build_food_picker_search_text(food),
    )


def resolve_food_picker_display_name(food: Food) -> str:
    return resolve_food_display_name(food)


def build_food_picker_search_text(food: Food) -> str:
    parts = [
        food.name,
        food.canonical_name,
    ]

    prefetched_aliases = getattr(food, "_prefetched_objects_cache", {}).get("aliases")

    if prefetched_aliases is not None:
        aliases = prefetched_aliases
    else:
        aliases = food.aliases.all()

    for alias in aliases:
        parts.append(alias.name)
        parts.append(alias.normalized_name)

    prefetched_localized_names = getattr(
        food,
        "_prefetched_objects_cache",
        {},
    ).get("localized_names")

    if prefetched_localized_names is not None:
        localized_names = prefetched_localized_names
    else:
        localized_names = food.localized_names.all()

    for localized_name in localized_names:
        parts.append(localized_name.name)
        parts.append(localized_name.normalized_name)

    return " ".join(
        str(part).strip().lower()
        for part in parts
        if part
    )




def resolve_food_picker_source(
    *,
    food: Food,
    user,
) -> str:
    if food.created_by_id == user.id:
        return PICKER_SOURCE_USER

    if food.is_global:
        return PICKER_SOURCE_GLOBAL

    if food.created_by_id is None:
        return PICKER_SOURCE_SYSTEM

    return PICKER_SOURCE_USER


def resolve_food_picker_label(picker_source: str) -> str:
    if picker_source == PICKER_SOURCE_USER:
        return "Tu alimento"

    if picker_source == PICKER_SOURCE_GLOBAL:
        return "Global"

    if picker_source == PICKER_SOURCE_SYSTEM:
        return "Sistema"

    return "Alimento"


def _apply_food_picker_search(
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
        | Q(localized_names__name__icontains=search)
        | Q(localized_names__normalized_name__icontains=search)
    )


def _resolve_source(food: Food) -> str:
    try:
        metadata = food.source_metadata
    except ObjectDoesNotExist:
        metadata = None

    if metadata is not None:
        return metadata.source

    if food.is_global:
        return PICKER_SOURCE_GLOBAL

    if food.created_by_id is None:
        return PICKER_SOURCE_SYSTEM

    return PICKER_SOURCE_USER


def _normalize_search(search: str | None) -> str | None:
    if search is None:
        return None

    if not isinstance(search, str):
        return None

    normalized = search.strip()

    return normalized or None


def _normalize_limit(limit: int) -> int:
    if isinstance(limit, bool):
        return DEFAULT_FOOD_PICKER_LIMIT

    if not isinstance(limit, int):
        return DEFAULT_FOOD_PICKER_LIMIT

    if limit <= 0:
        return DEFAULT_FOOD_PICKER_LIMIT

    return min(limit, MAX_FOOD_PICKER_LIMIT)