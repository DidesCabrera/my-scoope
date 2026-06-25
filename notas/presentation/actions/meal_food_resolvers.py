from django.urls import NoReverseMatch, reverse

from notas.application.services.access.capabilities import get_capabilities
from notas.presentation.routing.food import food_list_url, food_url
from notas.presentation.config.viewmodel_config import (
    MEAL_FOOD_VIEWMODE_DETAIL,
    MEAL_FOOD_VIEWMODE_DRAFT_DEEP_EDIT,
    MEAL_FOOD_VIEWMODE_LIST,
    MEAL_FOOD_VIEWMODE_PERSONAL_DEEP_EDIT,
)


# ==================================================
# 1. ENTITY ACTION DEFINITIONS
# ==================================================

MEAL_FOOD_ACTION_DEFINITIONS = {
    "detail": {
        "label": "View",
        "method": "get",
        "icon": "chevron-right",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "get_url": lambda food: food_url(food),
    },
    "cancel": {
        "label": "Cancel",
        "method": "get",
        "icon": "x",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "get_url": lambda food: food_list_url(),
    },
    "delete": {
        "label": "Delete",
        "method": "post",
        "icon": "trash-2",
        "order": 90,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda food: reverse(
            "food_delete",
            args=[food.id],
        ),
    },
    "edit": {
        "label": "Edit",
        "method": "get",
        "icon": "pencil",
        "order": 90,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda food: reverse(
            "food_edit",
            args=[food.id],
        ),
    },
    "save": {
        "label": "Save",
        "method": "post",
        "icon": "check",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "get_url": lambda food: reverse(
            "food_detail",
            args=[food.id],
        ),
    },
}


# ==================================================
# 2. ACTIONS BY VIEWMODE
# ==================================================

MEAL_FOOD_ACTIONS_BY_VIEWMODE = {
    MEAL_FOOD_VIEWMODE_LIST: [
        "detail",
    ],
    MEAL_FOOD_VIEWMODE_DETAIL: [
        "detail",
        "edit",
        "delete",
    ],
    MEAL_FOOD_VIEWMODE_PERSONAL_DEEP_EDIT: [
        "save",
        "cancel",
    ],
    MEAL_FOOD_VIEWMODE_DRAFT_DEEP_EDIT: [
        "save",
        "cancel",
    ],
}


# ==================================================
# 3. INTERNAL BUILDER
# ==================================================

def _build_actions_from_definitions(
    *,
    definitions,
    allowed_keys,
    subject,
    caps=None,
):
    actions = []

    for key in allowed_keys:
        definition = definitions.get(key)
        if not definition:
            continue

        capability_name = definition.get("capability")
        if capability_name:
            if not caps or not hasattr(caps, capability_name):
                continue
            if not getattr(caps, capability_name)():
                continue

        try:
            url = definition["get_url"](subject)
        except NoReverseMatch:
            continue

        actions.append(
            {
                "key": key,
                "label": definition["label"],
                "url": url,
                "method": definition["method"],
                "icon": definition.get("icon"),
                "order": definition.get("order", 100),
                "is_back": definition.get("is_back", False),
                "desktop_position": definition.get("desktop_position", "inline"),
                "mobile_position": definition.get("mobile_position", "inline"),
            }
        )

    return actions


# ==================================================
# 4. RESOLVER PRINCIPAL
# ==================================================

def resolve_meal_food_actions(food, user, viewmode):
    """
    Devuelve una lista de acciones disponibles para un food
    renderizado en el contexto meal_food, según viewmode
    + capabilities del usuario.
    """
    caps = get_capabilities(user)
    allowed_keys = MEAL_FOOD_ACTIONS_BY_VIEWMODE.get(viewmode, [])

    return _build_actions_from_definitions(
        definitions=MEAL_FOOD_ACTION_DEFINITIONS,
        allowed_keys=allowed_keys,
        subject=food,
        caps=caps,
    )