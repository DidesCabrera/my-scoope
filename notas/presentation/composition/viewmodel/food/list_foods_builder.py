from notas.presentation.viewmodels.content.food.list_food_vm import *
from notas.presentation.config.viewmodel_config import ALLOC_PCT_OUTSIDE_THRESHOLD
from notas.presentation.composition.viewmodel.components.builder_headers import build_page_header
from notas.presentation.actions.food_resolvers import resolve_food_entity_actions
from notas.presentation.config.icons import CONTENT_ICON_REGISTRY
from notas.presentation.resolvers.title_resolvers import resolve_category_badge
from notas.application.services.food_imports.localized_names import resolve_food_display_name
from notas.application.services.nutrition.weight import get_current_weight


_SOURCE_LABELS = {
    "usda": "USDA",
    "open_food_facts": "Open Food Facts",
    "latinfoods": "LATINFOODS",
    "inta_chile": "INTA Chile",
    "manual": "Manual",
    "global": "Global",
    "system": "Sistema",
    "user": "Usuario",
}


def _normalize_source_label(source):
    if not source:
        return ""

    normalized = str(source).lower()
    if normalized in _SOURCE_LABELS:
        return _SOURCE_LABELS[normalized]

    return str(source).replace("_", " ").title()


def _build_food_badges(food, user, include_unit=True):
    badges = []

    if include_unit:
        badges.append(FoodBadgeUI(label="100g", modifier="unit"))

    if food.created_by_id == getattr(user, "id", None):
        badges.append(FoodBadgeUI(label="Tu alimento", modifier="user"))
    elif food.is_global:
        badges.append(FoodBadgeUI(label="Global", modifier="global"))
    elif food.created_by_id is None:
        badges.append(FoodBadgeUI(label="Sistema", modifier="system"))

    if food.is_verified:
        badges.append(FoodBadgeUI(label="Verificado", modifier="verified"))

    source_label = _normalize_source_label(getattr(food, "source", ""))
    if source_label and source_label not in {"Usuario", "Global", "Sistema"}:
        badges.append(FoodBadgeUI(label=source_label, modifier="source"))

    if food.visibility == "core":
        badges.append(FoodBadgeUI(label="Core", modifier="core"))

    return badges


def build_food_list_vm(foods, user, viewmode, page_actions=None, list_mode="list"):
    child_cards = []
    current_weight = get_current_weight(user)

    for food in foods:
        protein_per_100g = float(food.protein or 0)
        ppk = (
            protein_per_100g / float(current_weight)
            if current_weight and protein_per_100g
            else 0
        )

        alloc = food.alloc

        child_card = ChildCardUI(
            child_id=food.id,

            titulo=TitleUI(
                name=resolve_food_display_name(food),
                label="Food",
                icon=CONTENT_ICON_REGISTRY.get("food"),
                category=getattr(food, "category", None),
                category_badge=resolve_category_badge(getattr(food, "category", None)),
                badges=_build_food_badges(food, user),
            ),

            kpis=KPIUI(
                ppk=ppk,
                tot_kcal=float(food.total_kcal),
                g_protein=protein_per_100g,
                g_carbs=float(food.carbs),
                g_fat=float(food.fat),
                kcal_protein=protein_per_100g * 4,
                kcal_carbs=float(food.carbs) * 4,
                kcal_fat=float(food.fat) * 9,
                alloc_protein=float(alloc["protein"]),
                alloc_carbs=float(alloc["carbs"]),
                alloc_fat=float(alloc["fat"]),
                pct_outside_protein=(
                    float(alloc["protein"]) < ALLOC_PCT_OUTSIDE_THRESHOLD
                ),
                pct_outside_carbs=(
                    float(alloc["carbs"]) < ALLOC_PCT_OUTSIDE_THRESHOLD
                ),
                pct_outside_fat=(
                    float(alloc["fat"]) < ALLOC_PCT_OUTSIDE_THRESHOLD
                ),
            ),

            metadata=MetadataUI(
                owner=str(food.created_by),
                author=str(getattr(food, "original_author", "")),
                fork_from=str(food.forked_from) if getattr(food, "forked_from", None) else None,
            ),

            actions=resolve_food_entity_actions(
                food,
                user,
                viewmode,
            ),
        )

        child_cards.append(child_card)

    return FoodListVM(
        header=build_page_header(actions=page_actions or []),
        child_cards=child_cards,
        list_mode=list_mode,
    )
