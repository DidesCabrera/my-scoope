from django.urls import NoReverseMatch, reverse

from notas.presentation.viewmodels.base_vm import BreadcrumbItem
from notas.presentation.navigation.app_registry import APP_NAVIGATION


NAV_ROOT_ALIASES = {
    "dailyplan_meal": "dailyplan",
}


def resolve_navigation_root(entity: str) -> str:
    return NAV_ROOT_ALIASES.get(entity, entity)


def safe_reverse(url_name: str | None) -> str | None:
    if not url_name:
        return None

    try:
        return reverse(url_name)
    except NoReverseMatch:
        return None


def resolve_object_url(obj) -> str | None:
    if obj is None:
        return None

    for attr_name in (
        "get_absolute_url",
        "dailyplan_url",
        "meal_url",
        "food_url",
        "profile_url",
    ):
        attr = getattr(obj, attr_name, None)

        if callable(attr):
            try:
                url = attr()
                if url:
                    return url
            except Exception:
                pass

    return None


def iter_nav_items():
    for section in APP_NAVIGATION:
        for group in section.groups:
            for item in group.items:
                yield section, group, item

def iter_nav_groups():
    for section in APP_NAVIGATION:
        for group in section.groups:
            yield section, group

def find_active_nav_item(viewmode):
    current_nav_root = resolve_navigation_root(viewmode.entity)
    current_scope = viewmode.scope

    for section, group, item in iter_nav_items():
        if item.nav_root == current_nav_root and item.scope == current_scope:
            return {
                "section": section,
                "group": group,
                "item": item,
                "kind": "item",
            }

    for section, group in iter_nav_groups():
        if (
            group.is_link
            and group.nav_root == current_nav_root
            and group.scope == current_scope
        ):
            return {
                "section": section,
                "group": group,
                "item": None,
                "kind": "group",
            }

    return None

def build_sidebar_vm(viewmode):
    active = find_active_nav_item(viewmode)
    active_group_key = active["group"].key if active else None

    sections_vm = []

    for section in APP_NAVIGATION:
        section_vm = {
            "key": section.key,
            "label": section.label,
            "groups": [],
        }

        for group in section.groups:
            if not group.show_in_sidebar:
                continue

            items_vm = []
            group_is_active = group.key == active_group_key
            group_is_link = group.is_link

            for item in group.items:
                if not item.show_in_sidebar:
                    continue

                is_active = (
                    active is not None
                    and active["kind"] == "item"
                    and active["item"] is not None
                    and item.key == active["item"].key
                )

                items_vm.append(
                    {
                        "key": item.key,
                        "label": item.label,
                        "icon": item.icon,
                        "url": safe_reverse(item.url_name) or "#",
                        "url_name": item.url_name,
                        "is_active": is_active,
                        "nav_root": item.nav_root,
                        "scope": item.scope,
                    }
                )

            section_vm["groups"].append(
                {
                    "key": group.key,
                    "label": group.label,
                    "icon": group.icon,
                    "is_active": group_is_active,
                    "is_open": group_is_active and not group_is_link,
                    "is_link": group_is_link,
                    "url": safe_reverse(group.url_name) or "#",
                    "url_name": group.url_name,
                    "nav_root": group.nav_root,
                    "scope": group.scope,
                    "items": items_vm,

                    "action_url": safe_reverse(group.action_url_name) if group.action_url_name else None,
                    "action_url_name": group.action_url_name,
                    "action_icon": group.action_icon,
                    "action_label": group.action_label,
                }
            )

        if section_vm["groups"]:
            sections_vm.append(section_vm)

    return sections_vm


def build_breadcrumb_vm(viewmode, parents=None, instance=None):
    breadcrumb = []

    active = find_active_nav_item(viewmode)
    if active:
        group = active["group"]
        item = active["item"]

        if item is not None:
            if item.scope != "explore":
                breadcrumb.append(
                    BreadcrumbItem(
                        label=group.label,
                        url=None,
                    )
                )
            breadcrumb.append(
                BreadcrumbItem(
                    label=item.label,
                    url=safe_reverse(item.url_name),
                )
            )
        elif group.is_link:
            breadcrumb.append(
                BreadcrumbItem(
                    label=group.label,
                    url=safe_reverse(group.url_name),
                )
            )

    if parents:
        for parent in parents:
            breadcrumb.append(
                BreadcrumbItem(
                    label=str(parent),
                    url=resolve_object_url(parent),
                    kind=getattr(parent, "kind", None),
                )
            )

    if instance:
        breadcrumb.append(
            BreadcrumbItem(
                label=str(instance),
                url=None,
            )
        )

    return breadcrumb


def build_navigation_meta(viewmode):
    active = find_active_nav_item(viewmode)
    nav_root = resolve_navigation_root(viewmode.entity)

    if not active:
        return {
            "nav_root": nav_root,
            "icon": None,
            "page_icon": None,
            "section_label": None,
            "default_title": "",
            "default_root": "",
        }

    section = active["section"]
    group = active["group"]
    item = active["item"]

    if item is not None:
        header_icon = item.page_icon if item.scope == "explore" and item.page_icon else item.icon

        return {
            "nav_root": nav_root,
            "icon": header_icon,
            "page_icon": item.page_icon or item.icon,
            "section_label": section.label,
            "default_title": item.label,
            "default_root": group.label,
        }

    return {
        "nav_root": nav_root,
        "icon": group.icon,
        "page_icon": group.page_icon or group.icon,
        "section_label": section.label,
        "default_title": group.label,
        "default_root": section.label,
    }



def build_back_url(viewmode, parents=None, breadcrumb=None, back_config=None):
    if back_config:
        back_type = back_config.get("type")

        if back_type == "none":
            return None

        if back_type == "parent":
            if parents:
                for parent in reversed(list(parents)):
                    parent_url = resolve_object_url(parent)
                    if parent_url:
                        return parent_url
            return None

        if back_type == "nav_item":
            active = find_active_nav_item(viewmode)
            if active:
                item = active.get("item")
                if item is not None:
                    return safe_reverse(item.url_name)

                group = active.get("group")
                if group and group.is_link:
                    return safe_reverse(group.url_name)
            return None

        if back_type == "url":
            return back_config.get("value")

        if back_type == "url_name":
            return safe_reverse(back_config.get("value"))

        if back_type == "object":
            return resolve_object_url(back_config.get("value"))

    if viewmode.mode == "list":
        return None

    if parents:
        parents_list = list(parents)

        for parent in reversed(parents_list):
            parent_url = resolve_object_url(parent)
            if parent_url:
                return parent_url

    active = find_active_nav_item(viewmode)
    if active:
        item = active["item"]

        if item is not None:
            item_url = safe_reverse(item.url_name)
            if item_url:
                return item_url

        group = active["group"]
        if group.is_link:
            group_url = safe_reverse(group.url_name)
            if group_url:
                return group_url

    if breadcrumb and len(breadcrumb) >= 2:
        return breadcrumb[-2].url

    return None



    