from django.urls import reverse, NoReverseMatch

from notas.application.services.access.capabilities import get_capabilities
from notas.interface.routing.meal import meal_url, meal_configure_url, meal_list_url
from notas.presentation.config.viewmodel_config import *


# ==================================================
# 1. ENTITY ACTION DEFINITIONS
# ==================================================

MEAL_ENTITY_ACTION_DEFINITIONS = {
    "detail": {
        "label": "Ver",
        "method": "get",
        "icon": "chevron-right",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "get_url": lambda meal, context=None: meal_url(meal),
    },

    "explore_detail": {
        "label": "Ver",
        "method": "get",
        "icon": "chevron-right",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "get_url": lambda meal, context=None: reverse(
            "meal_explore_detail", args=[meal.id]
        ),
    },

    "cancel": {
        "label": "Cancelar",
        "method": "get",
        "icon": "chevron-right",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "get_url": lambda meal, context=None: meal_list_url(),
    },

    "configure": {
        "label": "Configurar",
        "method": "get",
        "icon": "settings",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "menu",
        "get_url": lambda meal, context=None: meal_configure_url(meal),
        #"capability": "can_access_distribution_settings",
    },

    "fork": {
        "label": "Duplicar",
        "method": "post",
        "icon": "copy",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "menu",
        "get_url": lambda meal, context=None: reverse(
            "meal_fork", args=[meal.id]
        ),
        "capability": "can_fork",
    },

    "list_fork": {
        "label": "Duplicar",
        "method": "post",
        "icon": "copy",
        "order": 80,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda meal, context=None: reverse(
            "meal_fork", args=[meal.id]
        ),
        "capability": "can_fork",
    },

    "save": {
        "label": "Guardar",
        "method": "post",
        "icon": "bookmark",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "menu",
        "get_url": lambda meal, context=None: reverse(
            "meal_save", args=[meal.id]
        ),
        "capability": "can_fork",
    },

    "fork_explore": {
        "label": "Guardar en Personal",
        "method": "post",
        "icon": "bookmark",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "menu",
        "get_url": lambda meal, context=None: reverse(
            "meal_save", args=[meal.id]
        ),
        "capability": "can_fork",
    },

    "copy": {
        "label": "Copy",
        "method": "post",
        "icon": "chevron-right",
        "order": 90,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda meal, context=None: reverse(
            "meal_copy", args=[meal.id]
        ),
        "capability": "can_copy",
    },

    "add_to_dailyplan": {
        "label": "Agregar a Plan",
        "method": "get",
        "icon": "clipboard-plus",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "menu",
        "get_url": lambda meal, context=None: reverse(
            "add_meal_from_list", args=[meal.id]
        ),
    },

    "delete": {
        "label": "Eliminar",
        "method": "post",
        "icon": "trash-2",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "menu",
        "get_url": lambda meal, context=None: reverse(
            "meal_delete", args=[meal.id]
        ),
    },

    "deep_edit": {
        "label": "Editar",
        "method": "post",
        "icon": "pencil",
        "order": 90,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda meal, context=None: reverse(
            "meal_detail", args=[meal.id]
        ),
    },

    "back_detail": {
        "label": "Finalizar",
        "method": "post",
        "icon": "check",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "get_url": lambda meal, context=None: reverse(
            "meal_detail", args=[meal.id]
        ),
    },

    "finish_for_dailyplan": {
        "label": "Guardar y volver",
        "method": "post",
        "icon": "check",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "get_url": lambda meal, context=None: reverse(
            "meal_detail", args=[meal.id]
        ),
    },

    "back_to_list": {
        "label": "Volver",
        "method": "post",
        "icon": "chevron-left",
        "order": 90,
        "is_back": True,
        "desktop_position": "inline",
        "mobile_position": "hidden",
        "get_url": lambda meal, context=None: reverse("meal_list"),
    },

    "back_to_explore_list": {
        "label": "Volver",
        "method": "post",
        "icon": "chevron-left",
        "order": 90,
        "is_back": True,
        "desktop_position": "inline",
        "mobile_position": "hidden",
        "get_url": lambda meal, context=None: reverse("meal_explore_list"),
    },

    "remove": {
        "label": "Eliminar",
        "method": "post",
        "icon": "trash-2",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "menu",
        "get_url": lambda meal, context=None: reverse(
            "meal_remove", args=[meal.id]
        ),
    },

    "list_remove": {
        "label": "Eliminar",
        "method": "post",
        "icon": "trash-2",
        "order": 90,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda meal, context=None: reverse(
            "meal_remove", args=[meal.id]
        ),
    },

    "delete_draft": {
        "label": "Eliminar",
        "method": "post",
        "icon": "trash-2",
        "order": 90,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda meal, context=None: reverse(
            "meal_draft_delete", args=[meal.id]
        ),
    },

    "share": {
        "label": "Compartir",
        "method": "post",
        "icon": "send",
        "order": 90,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda meal, context=None: reverse(
            "meal_share", args=[meal.id]
        ),
    },

    "rename": {
        "label": "Renombrar",
        "method": "get",
        "icon": "pencil",
        "order": 40,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda meal, context=None: reverse(
            "meal_rename", args=[meal.id]
        ),
    },
}


# ==================================================
# 2. ENTITY ACTIONS BY VIEWMODE
# ==================================================

MEAL_ENTITY_ACTIONS_BY_VIEWMODE = {
    MEAL_VIEWMODE_PERSONAL_LIST: [
        "list_fork",
        "list_remove",
        "detail",
        # "share",
    ],

    MEAL_VIEWMODE_PERSONAL_DETAIL: [
        "back_to_list",
        "rename",
        "configure",
        "fork",
        "add_to_dailyplan",
        "remove",
    ],

    MEAL_VIEWMODE_EXPLORE_LIST: [
        "save",
        "explore_detail",
    ],

    MEAL_VIEWMODE_EXPLORE_DETAIL: [
        "back_to_explore_list",
        "save",
    ],

    MEAL_VIEWMODE_SHARED_LIST: [
        "detail",
    ],

    MEAL_VIEWMODE_DRAFT_LIST: [
        "delete_draft",
    ],

    MEAL_VIEWMODE_SHARED_DETAIL: [
    ],

    MEAL_VIEWMODE_PERSONAL_EDIT_FROM_DAILYPLAN: [
        "rename",
        "configure",
        "remove",
        "finish_for_dailyplan",
    ],


    MEAL_VIEWMODE_CONFIGURE: [
        "back_detail",
    ],

    MEAL_VIEWMODE_CREATE: [
        "cancel",
    ],

    MEAL_VIEWMODE_DAILYPLAN: [
        "detail",
    ],
}


# ==================================================
# 3. PAGE ACTION DEFINITIONS
# ==================================================

MEAL_PAGE_ACTION_DEFINITIONS = {
    "create": {
        "label": "Crear",
        "method": "get",
        "icon": "plus",
        "order": 10,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "get_url": lambda user, context=None: reverse("meal_create"),
    },
}


# ==================================================
# 4. PAGE ACTIONS BY VIEWMODE
# ==================================================

MEAL_PAGE_ACTIONS_BY_VIEWMODE = {
    MEAL_VIEWMODE_PERSONAL_LIST: [
        "create",
    ],
    MEAL_VIEWMODE_EXPLORE_LIST: [],
    MEAL_VIEWMODE_SHARED_LIST: [],
    MEAL_VIEWMODE_DRAFT_LIST: [],
}


# ==================================================
# 5. INTERNAL BUILDERS
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
            get_url = definition["get_url"]

            try:
                url = get_url(subject, None)
            except TypeError:
                url = get_url(subject)

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
# 6. ENTITY RESOLVER
# ==================================================

def resolve_meal_entity_actions(meal, user, viewmode):
    caps = get_capabilities(user)
    allowed_keys = MEAL_ENTITY_ACTIONS_BY_VIEWMODE.get(viewmode, [])

    return _build_actions_from_definitions(
        definitions=MEAL_ENTITY_ACTION_DEFINITIONS,
        allowed_keys=allowed_keys,
        subject=meal,
        caps=caps,
    )


# ==================================================
# 7. PAGE RESOLVER
# ==================================================

def resolve_meal_page_actions(user, viewmode):
    allowed_keys = MEAL_PAGE_ACTIONS_BY_VIEWMODE.get(viewmode, [])

    return _build_actions_from_definitions(
        definitions=MEAL_PAGE_ACTION_DEFINITIONS,
        allowed_keys=allowed_keys,
        subject=user,
        caps=None,
    )


# ==================================================
# 8. COMPATIBILITY ALIAS
# ==================================================

def resolve_meal_actions(meal, user, viewmode):
    return resolve_meal_entity_actions(meal, user, viewmode)