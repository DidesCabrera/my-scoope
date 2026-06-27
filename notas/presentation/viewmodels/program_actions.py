from __future__ import annotations

from dataclasses import asdict

from django.urls import reverse

from notas.domain.models import Program
from notas.presentation.composition.viewmodel.components.builder_headers import build_page_header
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm


def action(
    *,
    key,
    label,
    url,
    method="get",
    icon="chevron-right",
    order=90,
    desktop_position="inline",
    mobile_position="inline",
    is_back=False,
    disabled=False,
    extra_class="",
):
    return {
        "key": key,
        "label": label,
        "url": url,
        "method": method,
        "icon": icon,
        "order": order,
        "desktop_position": desktop_position,
        "mobile_position": mobile_position,
        "is_back": is_back,
        "disabled": disabled,
        "extra_class": extra_class,
    }


def program_list_actions(list_mode="list"):
    if list_mode == "reorder":
        return [
            action(
                key="save_list_order",
                label="Guardar Orden",
                url=reverse("program_list_reorder"),
                method="button",
                icon="check",
                order=10,
                extra_class="js-list-reorder-save",
            )
        ]

    if list_mode == "delete":
        return [
            action(
                key="exit_delete_mode",
                label="Cerrar",
                url=reverse("program_list"),
                icon="check",
                order=10,
            ),
            action(
                key="bulk_delete",
                label="Eliminar seleccionados",
                url=reverse("program_list_bulk_delete"),
                method="post",
                icon="trash-2",
                order=20,
                disabled=True,
                extra_class="js-list-bulk-delete-submit",
            ),
        ]

    return [
        action(
            key="create",
            label="Crear",
            url=reverse("program_create"),
            icon="plus",
            order=10,
        ),
        action(
            key="enter_reorder_mode",
            label="Reordenar Programas",
            url=f"{reverse('program_list')}?mode=reorder",
            icon="list-ordered",
            order=20,
            desktop_position="menu",
            mobile_position="menu",
        ),
        action(
            key="enter_delete_mode",
            label="Eliminar Programas",
            url=f"{reverse('program_list')}?mode=delete",
            icon="trash-2",
            order=30,
            desktop_position="menu",
            mobile_position="menu",
        ),
    ]


def program_detail_actions(program, user):
    actions = [
        action(
            key="back_to_list",
            label="Volver",
            url=reverse("program_list"),
            method="get",
            icon="chevron-left",
            order=10,
            is_back=True,
            mobile_position="hidden",
        ),
    ]

    is_owner = program.created_by_id == user.id

    if is_owner:
        actions.extend([
            action(
                key="rename",
                label="Renombrar",
                url=reverse("program_rename", args=[program.id]),
                icon="pencil",
                order=30,
                desktop_position="menu",
                mobile_position="menu",
            ),
            action(
                key="configure",
                label="Configurar",
                url=reverse("configure_program", args=[program.id]),
                icon="settings",
                order=40,
                mobile_position="menu",
            ),
            action(
                key="share",
                label="Compartir",
                url=reverse("program_share", args=[program.id]),
                icon="send",
                order=50,
                mobile_position="menu",
            ),
        ])

    if is_owner or program.is_forkable:
        actions.append(
            action(
                key="fork",
                label="Duplicar",
                url=reverse("fork_program", args=[program.id]),
                method="post",
                icon="copy",
                order=60,
                desktop_position="menu",
                mobile_position="menu",
            )
        )

    if is_owner or program.is_copiable:
        actions.append(
            action(
                key="copy",
                label="Copiar limpio",
                url=reverse("copy_program", args=[program.id]),
                method="post",
                icon="copy-plus",
                order=70,
                desktop_position="menu",
                mobile_position="menu",
            )
        )

    if is_owner:
        actions.append(
            action(
                key="remove",
                label="Eliminar",
                url=reverse("program_remove", args=[program.id]),
                method="post",
                icon="trash-2",
                order=80,
                desktop_position="menu",
                mobile_position="menu",
            )
        )

    return actions


def program_week_detail_actions(program, user, week_number):
    actions = [
        action(
            key="back_program",
            label="Volver",
            url=f"{reverse('program_detail', args=[program.id])}#week-{week_number}",
            icon="chevron-left",
            order=10,
            is_back=True,
        )
    ]

    if program.created_by_id == user.id:
        actions.append(
            action(
                key="duplicate_week",
                label="Duplicar semana",
                url=reverse("program_duplicate_week", args=[program.id, week_number]),
                method="post",
                icon="copy",
                order=20,
                desktop_position="inline",
                mobile_position="menu",
            )
        )

        if program.normalized_duration_weeks > Program.MIN_DURATION_WEEKS:
            actions.append(
                action(
                    key="remove_week",
                    label="Eliminar semana",
                    url=reverse("program_remove_week", args=[program.id, week_number]),
                    method="post",
                    icon="trash-2",
                    order=30,
                    desktop_position="inline",
                    mobile_position="menu",
                )
            )

    return actions


def program_header(actions=None):
    return asdict(build_page_header(actions=actions or []))


def program_vm_context(viewmode, *, content, instance=None, parents=None, back_config=None):
    ui_vm = build_ui_vm(
        viewmode,
        instance=instance,
        parents=parents,
        back_config=back_config,
    )
    return {
        "vm": {
            "ui": asdict(ui_vm),
            "content": content,
        }
    }
