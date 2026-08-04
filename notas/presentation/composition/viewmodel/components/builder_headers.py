from notas.presentation.actions.dailyplan_meal_resolvers import resolve_dailyplan_meal_actions
from notas.presentation.actions.dailyplan_resolvers import resolve_dailyplan_entity_actions
from notas.presentation.actions.food_resolvers import resolve_food_entity_actions
from notas.presentation.actions.meal_resolvers import resolve_meal_entity_actions
from notas.presentation.viewmodels.components.header_vm import HeaderActionVM, HeaderVM


def _build_header_actions(actions_data):
    if not actions_data:
        return []

    return [
        HeaderActionVM(
            key=action["key"],
            label=action["label"],
            url=action["url"],
            method=action.get("method", "get"),
            icon=action.get("icon"),
            is_back=action.get("is_back", False),
            order=action.get("order", 0),
            desktop_position=action.get("desktop_position", "inline"),
            mobile_position=action.get("mobile_position", "inline"),
            disabled=action.get("disabled", False),
            extra_class=action.get("extra_class", ""),
        )
        for action in actions_data
    ]


def _sort_actions(actions):
    return sorted(actions, key=lambda action: action.order)


def _classify_header_actions(actions):
    desktop_inline_actions = []
    desktop_menu_actions = []
    mobile_inline_actions = []
    mobile_menu_actions = []

    for action in _sort_actions(actions):
        if action.desktop_position == "inline":
            desktop_inline_actions.append(action)
        elif action.desktop_position == "menu":
            desktop_menu_actions.append(action)

        if action.mobile_position == "inline":
            mobile_inline_actions.append(action)
        elif action.mobile_position == "menu":
            mobile_menu_actions.append(action)

    return {
        "desktop_inline_actions": desktop_inline_actions,
        "desktop_menu_actions": desktop_menu_actions,
        "mobile_inline_actions": mobile_inline_actions,
        "mobile_menu_actions": mobile_menu_actions,
    }


def build_page_header(*, actions=None, title=""):
    header_actions = _build_header_actions(actions or [])
    classified = _classify_header_actions(header_actions)

    return HeaderVM(
        title=title,
        actions=header_actions,
        desktop_inline_actions=classified["desktop_inline_actions"],
        desktop_menu_actions=classified["desktop_menu_actions"],
        mobile_inline_actions=classified["mobile_inline_actions"],
        mobile_menu_actions=classified["mobile_menu_actions"],
    )


def build_food_header(*, food, user, viewmode):
    actions = resolve_food_entity_actions(
        food,
        user,
        viewmode,
    )
    header_actions = _build_header_actions(actions)
    classified = _classify_header_actions(header_actions)

    return HeaderVM(
        title=food.name,
        actions=header_actions,
        desktop_inline_actions=classified["desktop_inline_actions"],
        desktop_menu_actions=classified["desktop_menu_actions"],
        mobile_inline_actions=classified["mobile_inline_actions"],
        mobile_menu_actions=classified["mobile_menu_actions"],
    )


def build_meal_header(*, meal, user, viewmode):
    actions = resolve_meal_entity_actions(
        meal,
        user,
        viewmode,
    )
    header_actions = _build_header_actions(actions)
    classified = _classify_header_actions(header_actions)

    return HeaderVM(
        title=meal.name,
        actions=header_actions,
        desktop_inline_actions=classified["desktop_inline_actions"],
        desktop_menu_actions=classified["desktop_menu_actions"],
        mobile_inline_actions=classified["mobile_inline_actions"],
        mobile_menu_actions=classified["mobile_menu_actions"],
    )


def build_dailyplan_meal_header(*, dpm, user, viewmode):
    meal = dpm.meal
    actions = resolve_dailyplan_meal_actions(
        dpm,
        user,
        viewmode,
    )
    header_actions = _build_header_actions(actions)
    classified = _classify_header_actions(header_actions)

    return HeaderVM(
        title=meal.name,
        actions=header_actions,
        desktop_inline_actions=classified["desktop_inline_actions"],
        desktop_menu_actions=classified["desktop_menu_actions"],
        mobile_inline_actions=classified["mobile_inline_actions"],
        mobile_menu_actions=classified["mobile_menu_actions"],
    )


def build_dailyplan_header(*, dailyplan, user, viewmode):
    actions = resolve_dailyplan_entity_actions(
        dailyplan,
        user,
        viewmode,
    )
    header_actions = _build_header_actions(actions)
    classified = _classify_header_actions(header_actions)

    return HeaderVM(
        title="",
        actions=header_actions,
        desktop_inline_actions=classified["desktop_inline_actions"],
        desktop_menu_actions=classified["desktop_menu_actions"],
        mobile_inline_actions=classified["mobile_inline_actions"],
        mobile_menu_actions=classified["mobile_menu_actions"],
    )