from notas.presentation.viewmodels.base_vm import UI
from notas.presentation.navigation.nav_builders import (
    build_back_url,
    build_breadcrumb_vm,
    build_navigation_meta,
    build_sidebar_vm,
    resolve_navigation_root,
)


def build_ui_vm(viewmode, instance=None, parents=None, back_config=None):
    breadcrumb = build_breadcrumb_vm(
        viewmode,
        parents=parents,
        instance=instance,
    )

    meta = build_navigation_meta(viewmode)

    title = breadcrumb[-1].label if breadcrumb else meta["default_title"]

    is_inside = viewmode.mode != "list"

    root = ""
    if len(breadcrumb) >= 2:
        root = breadcrumb[-2].label
    elif is_inside:
        root = meta["default_root"]


    back_url = build_back_url(
        viewmode,
        parents=parents,
        breadcrumb=breadcrumb,
        back_config=back_config,
    )

    sidebar_sections = build_sidebar_vm(viewmode)

    return UI(
        viewmode=str(viewmode),
        entity=viewmode.entity,
        mode=viewmode.mode,
        scope=viewmode.scope,
        nav_root=resolve_navigation_root(viewmode.entity),
        icon=meta["icon"],
        page_icon=meta["page_icon"],
        breadcrumb=breadcrumb,
        section_label=meta["section_label"],
        title=title,
        root=root,
        is_inside=is_inside,
        back_url=back_url,
        sidebar_sections=sidebar_sections,
    )