from django.urls import reverse, NoReverseMatch

from notas.application.services.access.capabilities import get_capabilities
from notas.presentation.config.viewmodel_config import *
from notas.presentation.navigation.program_context import append_query



def _context_query_dict(context):
    query = (context or {}).get("query") if isinstance(context, dict) else ""
    params = {}
    for item in str(query).split("&"):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        if key and value:
            params[key] = value
    return params


def _contextual_dailyplan_meal_detail_url(dpm, context=None):
    return append_query(
        reverse(
            "dailyplan_meal_detail",
            args=[dpm.dailyplan.id, dpm.id],
        ),
        **_context_query_dict(context),
    )

# ==================================================
# 1. ENTITY ACTION DEFINITIONS
# ==================================================

DAILYPLAN_MEAL_ACTION_DEFINITIONS = {
    "detail": {
        "label": "Ver",
        "method": "get",
        "icon": "pencil",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "get_url": lambda dpm, context=None: _contextual_dailyplan_meal_detail_url(dpm, context),
    },

    "replace": {
        "label": "Cambiar",
        "method": "get",
        "icon": "repeat",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "menu",
        "get_url": lambda dpm, context=None: (
            reverse(
                "dailyplan_detail",
                args=[dpm.dailyplan.id],
            )
            + f"?edit_meal={dpm.id}&select_meal={dpm.meal.id}"
        ),
        "capability": "can_edit_own_content",
    },

    "remove": {
        "label": "Quitar",
        "method": "post",
        "icon": "trash-2",
        "order": 90,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda dpm, context=None: reverse(
            "remove_meal",
            args=[dpm.dailyplan.id, dpm.id],
        ),
        "capability": "can_edit_own_content",
    },

    "back_dp_detail": {
        "label": "Volver",
        "method": "get",
        "icon": "chevron-left",
        "order": 90,
        "is_back": True,
        "desktop_position": "inline",
        "mobile_position": "hidden",
        "get_url": lambda dpm, context=None: reverse(
            "dailyplan_detail",
            args=[dpm.dailyplan.id],
        ),
    },

    "back_dpm_detail": {
        "label": "Finalizar",
        "method": "get",
        "icon": "check",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "get_url": lambda dpm, context=None: _contextual_dailyplan_meal_detail_url(dpm, context),
    },

    "edit": {
        "label": "Editar",
        "method": "get",
        "icon": "settings-2",
        "order": 90,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda dpm, context=None: reverse(
            "dailyplan_meal_edit",
            args=[dpm.dailyplan.id, dpm.id],
        ),
        "capability": "can_edit_own_content",
    },

    "rename": {
        "label": "Renombrar",
        "method": "get",
        "icon": "pencil",
        "order": 40,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda dpm, context=None: (
            reverse("meal_rename", args=[dpm.meal.id])
            + "?return_to="
            + reverse(
                "dailyplan_meal_detail",
                args=[dpm.dailyplan.id, dpm.id],
            )
        ),
        "capability": "can_edit_own_content",
    },

    "save_to_library": {
        "label": "Guardar en Mi librería",
        "method": "post",
        "icon": "bookmark-plus",
        "order": 50,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda dpm, context=None: reverse(
            "dailyplanmeal_save_to_library",
            args=[dpm.dailyplan.id, dpm.id],
        ),
        "capability": "can_edit_own_content",
    },

    "share": {
        "label": "Compartir",
        "method": "get",
        "icon": "send",
        "order": 55,
        "desktop_position": "inline",
        "mobile_position": "menu",
        "get_url": lambda dpm, context=None: reverse(
            "dailyplanmeal_share",
            args=[dpm.dailyplan.id, dpm.id],
        ),
        "capability": "can_edit_own_content",
    },

}

# ==================================================
# 2. ACTIONS BY VIEWMODE
# ==================================================

DAILYPLAN_MEAL_ACTIONS_BY_VIEWMODE = {
    DAILYPLAN_MEAL_VIEWMODE_LIST: [
        "detail",
    ],

    DAILYPLAN_MEAL_VIEWMODE_DETAIL: [
        "back_dp_detail",
        "rename",
        "share",
        "save_to_library",
        "replace",
        "edit",
        "remove",
    ],

    DAILYPLAN_MEAL_VIEWMODE_DRAFT_DEEP_EDIT: [
        "back_dpm_detail",
    ],

    DAILYPLAN_VIEWMODE_PERSONAL_DETAIL: [
        "remove",
        "detail",
    ],

    DAILYPLAN_VIEWMODE_EXPLORE_DETAIL: [],
    DAILYPLAN_VIEWMODE_SHARED_DETAIL: [],
    DAILYPLAN_VIEWMODE_DRAFT_DETAIL: [
        "remove",
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
    context=None,
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
                url = get_url(subject, context)
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
# 4. RESOLVER PRINCIPAL
# ==================================================

def resolve_dailyplan_meal_actions(dpm, user, viewmode, context=None):
    """
    Devuelve una lista de acciones disponibles para un DailyPlanMeal,
    según viewmode + capabilities del usuario.
    """
    caps = get_capabilities(user)
    allowed_keys = DAILYPLAN_MEAL_ACTIONS_BY_VIEWMODE.get(viewmode, [])

    return _build_actions_from_definitions(
        definitions=DAILYPLAN_MEAL_ACTION_DEFINITIONS,
        allowed_keys=allowed_keys,
        subject=dpm,
        caps=caps,
        context=context,
    )