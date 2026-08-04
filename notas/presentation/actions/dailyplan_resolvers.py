from django.urls import NoReverseMatch, reverse

from notas.application.services.access.capabilities import get_capabilities
from notas.presentation.config.viewmodel_config import *
from notas.presentation.routing.dailyplan import dailyplan_configure_url, dailyplan_url

# ==================================================
# 1. ENTITY ACTION DEFINITIONS
# ==================================================

DAILYPLAN_ENTITY_ACTION_DEFINITIONS = {
    "detail": {
        "label": "Ver",
        "method": "get",
        "icon": "chevron-right",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "get_url": lambda dp, context=None: dailyplan_url(dp),
    },

    "shared_detail": {
        "label": "Ver",
        "method": "get",
        "icon": "chevron-right",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "get_url": lambda dp, context=None: reverse(
            "dailyplan_shared_detail", args=[dp.id]
        ),
    },

    "draft_detail": {
        "label": "Ver Draft",
        "method": "get",
        "icon": "chevron-right",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "get_url": lambda dp, context=None: reverse(
            "dailyplan_draft_detail", args=[dp.id]
        ),
    },

    "explore_detail": {
        "label": "Ver",
        "method": "get",
        "icon": "chevron-right",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "get_url": lambda dp, context=None: reverse(
            "dailyplan_explore_detail", args=[dp.id]
        ),
    },

    "configure": {
        "label": "Configurar",
        "method": "get",
        "icon": "settings",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "menu",
        "get_url": lambda dp, context=None: dailyplan_configure_url(dp),
        "capability": "can_access_distribution_settings",
    },

    "fork": {
        "label": "Duplicar",
        "method": "post",
        "icon": "copy",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "menu",
        "get_url": lambda dp, context=None: reverse(
            "dailyplan_fork", args=[dp.id]
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
        "get_url": lambda dp, context=None: reverse(
            "dailyplan_fork", args=[dp.id]
        ),
        "capability": "can_fork",
    },

    "fork_explore": {
        "label": "Guardar en Personal",
        "method": "post",
        "icon": "bookmark",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "get_url": lambda dp, context=None: reverse(
            "dailyplan_fork", args=[dp.id]
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
        "get_url": lambda dp, context=None: reverse(
            "dailyplan_save", args=[dp.id]
        ),
        "capability": "can_fork",
    },

    "save_my_list": {
        "label": "Guardar en Personal",
        "method": "post",
        "icon": "bookmark",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "menu",
        "get_url": lambda dp, context=None: reverse(
            "dailyplan_save", args=[dp.id]
        ),
        "capability": "can_fork",
    },

    "copy": {
        "label": "Copiar",
        "method": "post",
        "icon": "trash-2",
        "order": 90,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda dp, context=None: reverse(
            "dailyplan_copy", args=[dp.id]
        ),
        "capability": "can_copy",
    },

    "delete": {
        "label": "Borrar",
        "method": "post",
        "icon": "trash-2",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "menu",
        "get_url": lambda dp, context=None: reverse(
            "dailyplan_delete", args=[dp.id]
        ),
        "capability": "is_admin",
    },

    "share": {
        "label": "Compartir",
        "method": "get",
        "icon": "send",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "menu",
        "get_url": lambda dp, context=None: reverse(
            "dailyplan_share", args=[dp.id]
        ),
    },

    "remove": {
        "label": "Remover",
        "method": "post",
        "icon": "trash-2",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "menu",
        "get_url": lambda dp, context=None: reverse(
            "dailyplan_remove", args=[dp.id]
        ),
    },

    "list_remove": {
        "label": "Eliminar",
        "method": "post",
        "icon": "trash-2",
        "order": 90,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda dp, context=None: reverse(
            "dailyplan_remove", args=[dp.id]
        ),
    },

    "unshare": {
        "label": "Quitar",
        "method": "post",
        "icon": "trash-2",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "menu",
        "get_url": lambda share_id, context=None: reverse(
            "dailyplan_unshare", args=[share_id]
        ),
    },

    "edit": {
        "label": "Editar",
        "method": "post",
        "icon": "pencil",
        "order": 90,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda dp, context=None: reverse(
            "dailyplan_edit", args=[dp.id]
        ),
    },

    "draft_edit": {
        "label": "Retomar",
        "method": "post",
        "icon": "pencil",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "menu",
        "get_url": lambda dp, context=None: reverse(
            "dailyplan_draft_edit", args=[dp.id]
        ),
    },

    "back_detail": {
        "label": "Finalizar",
        "method": "get",
        "icon": "check",
        "order": 90,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "get_url": lambda dp, context=None: dailyplan_url(dp),
    },

    "back_to_list": {
        "label": "Volver",
        "method": "post",
        "icon": "chevron-left",
        "order": 90,
        "is_back": True,
        "desktop_position": "inline",
        "mobile_position": "hidden",
        "get_url": lambda dp, context=None: reverse("dailyplan_list"),
    },

    "back_to_explore_list": {
        "label": "Salir",
        "method": "post",
        "icon": "chevron-left",
        "order": 90,
        "is_back": True,
        "desktop_position": "inline",
        "mobile_position": "hidden",
        "get_url": lambda dp, context=None: reverse("dailyplan_explore_list"),
    },

    "back_to_shared_list": {
        "label": "Salir",
        "method": "post",
        "icon": "chevron-left",
        "order": 90,
        "is_back": True,
        "desktop_position": "inline",
        "mobile_position": "hidden",
        "get_url": lambda dp, context=None: reverse("dailyplan_shared_list"),
    },

    "back_to_draft_list": {
        "label": "Salir",
        "method": "post",
        "icon": "chevron-left",
        "order": 90,
        "is_back": True,
        "desktop_position": "inline",
        "mobile_position": "hidden",
        "get_url": lambda dp, context=None: reverse("dailyplan_draft_list"),
    },

    "rename": {
        "label": "Renombrar",
        "method": "get",
        "icon": "pencil",
        "order": 40,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda dp, context=None: reverse(
            "dailyplan_rename", args=[dp.id]
        ),
    },

}


# ==================================================
# 2. ENTITY ACTIONS BY VIEWMODE
# ==================================================

DAILYPLAN_ENTITY_ACTIONS_BY_VIEWMODE = {
    DAILYPLAN_VIEWMODE_PERSONAL_LIST: [
        "list_fork",
        "list_remove",
        "detail",
    ],

    DAILYPLAN_VIEWMODE_PERSONAL_DETAIL: [
        "back_to_list",
        "rename",
        "configure",
        "fork",
        "share",
        "remove",
    ],

    DAILYPLAN_VIEWMODE_EXPLORE_LIST: [
        "save",
        "explore_detail",
    ],

    DAILYPLAN_VIEWMODE_EXPLORE_DETAIL: [
        "back_to_explore_list",
        "fork_explore",
    ],

    DAILYPLAN_VIEWMODE_SHARED_LIST: [
        "save_my_list",
        "shared_detail",
    ],

    DAILYPLAN_VIEWMODE_SHARED_DETAIL: [
        "save_my_list",
        "unshare",
        "back_to_shared_list",
    ],

    DAILYPLAN_VIEWMODE_DRAFT_LIST: [
        "draft_edit",
        "remove",
    ],

    DAILYPLAN_VIEWMODE_DRAFT_DETAIL: [
        "draft_edit",
        "remove",
        "back_to_draft_list",
    ],

    DAILYPLAN_VIEWMODE_DRAFT_EDIT: [
        "configure",
        "back_to_draft_list",
    ],

    DAILYPLAN_VIEWMODE_CONFIGURE: [
        "back_detail",
    ],
}


# ==================================================
# 3. PAGE ACTION DEFINITIONS
# ==================================================

DAILYPLAN_PAGE_ACTION_DEFINITIONS = {
    "create": {
        "label": "Crear",
        "method": "get",
        "icon": "plus",
        "order": 10,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "get_url": lambda user, context=None: reverse("dailyplan_create"),
    },

    "enter_reorder_mode": {
        "label": "Reordenar Planes",
        "method": "get",
        "icon": "list-ordered",
        "order": 20,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda user, context=None: reverse("dailyplan_list") + "?mode=reorder",
    },

    "compare": {
        "label": "Comparar Planes",
        "method": "get",
        "icon": "columns-3",
        "order": 25,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda user, context=None: reverse("dailyplan_comparator"),
    },

    "enter_delete_mode": {
        "label": "Eliminar Planes",
        "method": "get",
        "icon": "trash-2",
        "order": 30,
        "desktop_position": "menu",
        "mobile_position": "menu",
        "get_url": lambda user, context=None: reverse("dailyplan_list") + "?mode=delete",
    },

    "save_list_order": {
        "label": "Guardar Orden",
        "method": "button",
        "icon": "check",
        "order": 10,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "extra_class": "js-list-reorder-save",
        "get_url": lambda user, context=None: reverse("dailyplan_list_reorder"),
    },

    "exit_delete_mode": {
        "label": "Cerrar",
        "method": "get",
        "icon": "check",
        "order": 10,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "get_url": lambda user, context=None: reverse("dailyplan_list"),
    },

    "bulk_delete": {
        "label": "Eliminar seleccionados",
        "method": "post",
        "icon": "trash-2",
        "order": 20,
        "desktop_position": "inline",
        "mobile_position": "inline",
        "disabled": True,
        "extra_class": "js-list-bulk-delete-submit",
        "get_url": lambda user, context=None: reverse("dailyplan_list_bulk_delete"),
    },
}


# ==================================================
# 4. PAGE ACTIONS BY VIEWMODE
# ==================================================

DAILYPLAN_PAGE_ACTIONS_BY_VIEWMODE = {
    DAILYPLAN_VIEWMODE_PERSONAL_LIST: [
        "create",
        "enter_reorder_mode",
        "compare",
        "enter_delete_mode",
    ],
    DAILYPLAN_VIEWMODE_EXPLORE_LIST: [],
    DAILYPLAN_VIEWMODE_SHARED_LIST: [],
    DAILYPLAN_VIEWMODE_DRAFT_LIST: [],
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
                "disabled": definition.get("disabled", False),
                "extra_class": definition.get("extra_class", ""),
            }
        )

    return actions


# ==================================================
# 6. ENTITY RESOLVER
# ==================================================

def resolve_dailyplan_entity_actions(dailyplan, user, viewmode):
    caps = get_capabilities(user)
    allowed_keys = DAILYPLAN_ENTITY_ACTIONS_BY_VIEWMODE.get(viewmode, [])

    return _build_actions_from_definitions(
        definitions=DAILYPLAN_ENTITY_ACTION_DEFINITIONS,
        allowed_keys=allowed_keys,
        subject=dailyplan,
        caps=caps,
    )


# ==================================================
# 7. PAGE RESOLVER
# ==================================================

def resolve_dailyplan_page_actions(user, viewmode, list_mode="list"):
    if viewmode == DAILYPLAN_VIEWMODE_PERSONAL_LIST and list_mode == "reorder":
        allowed_keys = ["save_list_order"]
    elif viewmode == DAILYPLAN_VIEWMODE_PERSONAL_LIST and list_mode == "delete":
        allowed_keys = ["exit_delete_mode", "bulk_delete"]
    else:
        allowed_keys = DAILYPLAN_PAGE_ACTIONS_BY_VIEWMODE.get(viewmode, [])

    return _build_actions_from_definitions(
        definitions=DAILYPLAN_PAGE_ACTION_DEFINITIONS,
        allowed_keys=allowed_keys,
        subject=user,
        caps=None,
    )


# ==================================================
# 8. COMPATIBILITY ALIAS
# ==================================================

def resolve_dailyplan_actions(dailyplan, user, viewmode):
    return resolve_dailyplan_entity_actions(dailyplan, user, viewmode)