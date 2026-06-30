"""Context builders for DailyPlan interface views.

These helpers keep HTTP views focused on request/session/redirect concerns while
presentation owns the UI composition contracts rendered by templates.
"""

from __future__ import annotations

from typing import Any

from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import (
    DAILYPLAN_VIEWMODE_CONFIGURE,
    DAILYPLAN_VIEWMODE_CREATE,
    PROGRAM_VIEWMODE_PERSONAL_DETAIL,
)
from notas.presentation.navigation.program_context import (
    compact_program_breadcrumbs,
    day_plan_parent,
    get_program_day_for_user,
    program_parent,
    week_parent,
)
from notas.presentation.viewmodels.base_vm import BaseVM
from notas.presentation.viewmodels.dailyplans import (
    build_dailyplan_configure_vm,
    build_dailyplan_detail_vm,
    build_dailyplan_list_vm,
)


def build_dailyplan_list_context(page: Any) -> dict[str, Any]:
    content_vm = build_dailyplan_list_vm(
        page.list_content_data,
        page_actions=page.page_actions,
        list_mode=page.list_mode,
    )

    return BaseVM(
        ui=build_ui_vm(page.viewmode),
        content=content_vm,
    ).as_context()


def build_dailyplan_detail_context(
    *,
    page: Any,
    user: Any,
    program_day_id: Any = None,
    include_picker: bool = False,
) -> dict[str, Any]:
    content_vm = build_dailyplan_detail_vm(page.detail_content_data)
    program_day = get_program_day_for_user(user, program_day_id)

    if program_day and program_day.dailyplan_id == page.dailyplan.id:
        ui_vm = build_ui_vm(
            PROGRAM_VIEWMODE_PERSONAL_DETAIL,
            parents=[
                program_parent(program_day),
                week_parent(program_day),
            ],
            instance=day_plan_parent(program_day),
            back_config={
                "type": "url",
                "value": week_parent(program_day).url,
            },
        )
        compact_program_breadcrumbs(ui_vm)
    else:
        ui_vm = build_ui_vm(
            page.viewmode,
            instance=page.dailyplan,
        )

    context = BaseVM(
        ui=ui_vm,
        content=content_vm,
    ).as_context()

    if include_picker:
        context.update(
            {
                "meal_picker_data_json": page.meal_picker_data_json,
                "meal_picker_context": page.meal_picker_context_json,
                "program_context_query": page.program_context_query,
                "selected_meal_id": page.selected_meal_id,
                "editing_dailyplanmeal_id": page.editing_dailyplanmeal_id,
            }
        )

    return context


def build_dailyplan_create_context() -> dict[str, Any]:
    return BaseVM(
        ui=build_ui_vm(DAILYPLAN_VIEWMODE_CREATE),
        content=None,
    ).as_context()


def build_dailyplan_configure_context(*, dailyplan: Any, user: Any) -> dict[str, Any]:
    content_vm = build_dailyplan_configure_vm(
        dailyplan,
        user,
        DAILYPLAN_VIEWMODE_CONFIGURE,
    DAILYPLAN_VIEWMODE_CREATE,
    )

    return BaseVM(
        ui=build_ui_vm(
            DAILYPLAN_VIEWMODE_CONFIGURE,
    DAILYPLAN_VIEWMODE_CREATE,
            instance=dailyplan,
        ),
        content=content_vm,
    ).as_context()
