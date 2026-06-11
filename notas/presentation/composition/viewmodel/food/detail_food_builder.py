from notas.presentation.viewmodels.content.food.detail_food_vm import *
from notas.presentation.composition.viewmodel.components.builder_headers import build_food_header

from notas.presentation.config.icons import CONTENT_ICON_REGISTRY
from notas.presentation.resolvers.title_resolvers import resolve_category_badge
from notas.application.services.food_imports.localized_names import resolve_food_display_name
from notas.presentation.composition.viewmodel.food.list_foods_builder import _build_food_badges
from notas.application.services.nutrition.weight import get_current_weight


def build_food_detail_vm(food, user, viewmode):

    main_entity_icon = CONTENT_ICON_REGISTRY.get("food")
    main_entity_label = "Food"

    # ==================================================
    # HEADER
    # ==================================================

    header = build_food_header(
        food=food,
        user=user,
        viewmode=viewmode
    )

    # ==================================================
    # Freeze MEAL aggregates (cached if available)
    # ==================================================

    food_total_kcal = food.total_kcal
    food_protein = food.protein
    food_carbs = food.carbs
    food_fat = food.fat

    food_kcal_protein = food.kcal_protein
    food_kcal_carbs = food.kcal_carbs
    food_kcal_fat = food.kcal_fat

    food_alloc = {
        "protein": food.alloc["protein"],
        "carbs": food.alloc["carbs"],
        "fat": food.alloc["fat"],
    }

    current_weight = get_current_weight(user)
    food_ppk = (
        float(food_protein) / float(current_weight)
        if current_weight and food_protein
        else 0
    )

    # ==================================================
    # MAIN CARD
    # ==================================================


    main = MainCardUI(
        main_id=food.id,

        titulo=TitleUI(
            name=resolve_food_display_name(food),
            label=main_entity_label,
            icon=main_entity_icon,
            category=getattr(food, "category", None),
            category_badge=resolve_category_badge(getattr(food, "category", None)),
            badges=_build_food_badges(food, user, include_unit=False),
        ),

        kpis=KPIUI(
            ppk=food_ppk,
            body_weight=float(current_weight or 0),
            tot_kcal=food_total_kcal,

            g_protein=food_protein,
            g_carbs=food_carbs,
            g_fat=food_fat,

            kcal_protein=food_kcal_protein,
            kcal_carbs=food_kcal_carbs,
            kcal_fat=food_kcal_fat,

            alloc_protein=food_alloc["protein"],
            alloc_carbs=food_alloc["carbs"],
            alloc_fat=food_alloc["fat"],
        )
    )

    return FoodDetailVM(
        header=header,
        main_card=main,
    )
