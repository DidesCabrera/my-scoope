from django.urls import NoReverseMatch, reverse

from notas.application.services.access.capabilities import get_capabilities
from notas.presentation.config.viewmodel_config import (
    DAILYPLAN_VIEWMODE_SHARED_LIST,
    MEAL_VIEWMODE_SHARED_LIST,
)


# ==================================================
# 1. DEFINICIÓN DECLARATIVA DE ACCIONES
# ==================================================

SHARE_ACTION_DEFINITIONS = {
    "unshare_dailyplan": {
        "label": "Quitar",
        "method": "post",
        "get_url": lambda share: reverse(
            "dailyplan_unshare",
            args=[share.id],
        ),
    },
    "unshare_meal": {
        "label": "Quitar",
        "method": "post",
        "get_url": lambda share: reverse(
            "meal_unshare",
            args=[share.id],
        ),
    },
}


# ==================================================
# 2. ACCIONES PERMITIDAS POR VIEWMODE
# ==================================================

SHARE_ACTIONS_BY_VIEWMODE = {
    DAILYPLAN_VIEWMODE_SHARED_LIST: [
        "unshare_dailyplan",
    ],
    MEAL_VIEWMODE_SHARED_LIST: [
        "unshare_meal",
    ],
}


# ==================================================
# 3. RESOLVER PRINCIPAL
# ==================================================

def resolve_share_actions(share, user, viewmode):
    caps = get_capabilities(user)
    actions = []

    allowed_keys = SHARE_ACTIONS_BY_VIEWMODE.get(viewmode, [])

    for key in allowed_keys:
        definition = SHARE_ACTION_DEFINITIONS.get(key)
        if not definition:
            continue

        capability_name = definition.get("capability")
        if capability_name:
            if not caps or not hasattr(caps, capability_name):
                continue
            if not getattr(caps, capability_name)():
                continue

        try:
            url = definition["get_url"](share)
        except NoReverseMatch:
            continue

        actions.append(
            {
                "key": key,
                "label": definition["label"],
                "url": url,
                "method": definition["method"],
                "group": definition.get("group", "primary"),
                "icon": definition.get("icon"),
                "order": definition.get("order", 100),
                "is_back": definition.get("is_back", False),
            }
        )

    return actions