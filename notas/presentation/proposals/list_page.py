from dataclasses import dataclass

from django.urls import reverse


@dataclass
class ProposalListContentVM:
    header: object
    proposals: list[dict]
    list_mode: str = "list"


def normalize_proposal_status_filter(raw_status: str | None) -> str | None:
    status = (raw_status or "all").strip()

    if status in {"pending_review", "rejected", "applied"}:
        return status

    return None


def resolve_proposal_list_status_filter(*, get_status: str | None, post_status: str | None) -> str | None:
    return normalize_proposal_status_filter(get_status or post_status)


def normalize_proposal_list_mode(raw_mode: str | None) -> str:
    mode = (raw_mode or "list").strip()
    return mode if mode in {"list", "reorder", "delete"} else "list"


def proposal_list_url(*, mode: str | None = None, status_filter: str | None = None) -> str:
    base_url = reverse("proposal_list")
    params = []

    if mode and mode != "list":
        params.append(f"mode={mode}")

    if status_filter:
        params.append(f"status={status_filter}")

    if not params:
        return base_url

    return f"{base_url}?{'&'.join(params)}"


def proposal_safe_return_to(*, status_filter: str | None, mode: str | None = None) -> str:
    return proposal_list_url(mode=mode, status_filter=status_filter)


def build_proposal_list_actions(active_filter: str | None, list_mode: str) -> list[dict]:
    if list_mode == "reorder":
        return [
            {
                "key": "save_list_order",
                "label": "Guardar Orden",
                "url": reverse("proposal_list_reorder"),
                "method": "button",
                "icon": "check",
                "order": 10,
                "desktop_position": "inline",
                "mobile_position": "inline",
                "extra_class": "js-list-reorder-save",
            },
        ]

    if list_mode == "delete":
        return [
            {
                "key": "exit_delete_mode",
                "label": "Cerrar",
                "url": proposal_list_url(status_filter=active_filter),
                "method": "get",
                "icon": "check",
                "order": 10,
                "desktop_position": "inline",
                "mobile_position": "inline",
            },
            {
                "key": "bulk_delete",
                "label": "Eliminar seleccionadas",
                "url": (
                    reverse("proposal_list_bulk_delete")
                    + (f"?status={active_filter}" if active_filter else "")
                ),
                "method": "post",
                "icon": "trash-2",
                "order": 20,
                "desktop_position": "inline",
                "mobile_position": "inline",
                "disabled": True,
                "extra_class": "js-list-bulk-delete-submit",
            },
        ]

    actions = [
        {
            "key": "enter_reorder_mode",
            "label": "Reordenar Propuestas",
            "url": proposal_list_url(mode="reorder", status_filter=active_filter),
            "method": "get",
            "icon": "list-ordered",
            "order": 10,
            "desktop_position": "menu",
            "mobile_position": "menu",
        },
        {
            "key": "enter_delete_mode",
            "label": "Eliminar Propuestas",
            "url": proposal_list_url(mode="delete", status_filter=active_filter),
            "method": "get",
            "icon": "trash-2",
            "order": 20,
            "desktop_position": "menu",
            "mobile_position": "menu",
        },
    ]

    actions.extend(_build_proposal_list_filter_actions(active_filter))
    return actions


def _build_proposal_list_filter_actions(active_filter: str | None) -> list[dict]:
    base_url = reverse("proposal_list")

    filters = [
        {
            "key": "filter_pending_review",
            "label": "Ver solo pendientes de revisión",
            "url": proposal_list_url(status_filter="pending_review"),
            "icon": "clock",
            "status_filter": "pending_review",
            "order": 100,
        },
        {
            "key": "filter_applied",
            "label": "Ver solo aplicadas",
            "url": proposal_list_url(status_filter="applied"),
            "icon": "check",
            "status_filter": "applied",
            "order": 110,
        },
        {
            "key": "filter_rejected",
            "label": "Ver solo rechazadas",
            "url": proposal_list_url(status_filter="rejected"),
            "icon": "x",
            "status_filter": "rejected",
            "order": 115,
        },
        {
            "key": "filter_all",
            "label": "Ver todas",
            "url": base_url,
            "icon": "list",
            "status_filter": None,
            "order": 120,
        },
    ]

    return [
        {
            "key": item["key"],
            "label": item["label"],
            "url": item["url"],
            "method": "get",
            "icon": item["icon"],
            "order": item["order"],
            "desktop_position": "menu",
            "mobile_position": "menu",
            "extra_class": (
                "is-active"
                if item["status_filter"] == active_filter
                else ""
            ),
        }
        for item in filters
    ]
