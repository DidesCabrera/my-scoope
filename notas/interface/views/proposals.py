from dataclasses import dataclass

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from notas.application.queries.proposal_queries import (
    get_available_proposal_queryset,
    get_proposal_detail,
    list_user_proposals,
)
from notas.application.services.commands.proposal_commands import (
    approve_proposal,
    cancel_proposal,
    delete_proposal,
    reject_proposal,
    apply_approved_create_dailyplan_proposal,
    apply_approved_create_meal_proposal,
)
from notas.application.dto.proposal_payloads import (
    CREATE_DAILYPLAN_INTENT,
    CREATE_MEAL_INTENT,
)
from notas.presentation.composition.viewmodel.components.builder_headers import (
    build_page_header,
)
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import (
    PROPOSAL_VIEWMODE_DETAIL,
    PROPOSAL_VIEWMODE_LIST,
)
from notas.presentation.viewmodels.base_vm import BaseVM

from notas.presentation.proposals.proposal_review_viewmodels import (
    build_proposal_review_vm,
)

@dataclass
class ProposalListContentVM:
    header: object
    proposals: list[dict]
    list_mode: str = "list"


@dataclass
class ProposalDetailContentVM:
    header: object
    proposal: dict
    proposal_review: dict


@dataclass
class ProposalEntityDetailContentVM:
    header: object
    proposal: dict
    proposal_review: dict
    entity_kind: str
    entity_name: str
    main_card: dict
    child_cards: list
    structural_indicators: dict
    foods_aggregation: list


@dataclass(frozen=True)
class BreadcrumbParent:
    label: str
    url: str

    def __str__(self):
        return self.label

    def get_absolute_url(self):
        return self.url



def _get_proposal_list_status_filter(request):
    status = (
        request.GET.get("status")
        or request.POST.get("status")
        or "all"
    ).strip()

    if status in {"pending_review", "approved"}:
        return status

    return None


def _normalize_proposal_list_mode(request):
    mode = (request.GET.get("mode") or "list").strip()
    return mode if mode in {"list", "reorder", "delete"} else "list"


def _proposal_list_url(*, mode: str | None = None, status_filter: str | None = None):
    base_url = reverse("proposal_list")
    params = []

    if mode and mode != "list":
        params.append(f"mode={mode}")

    if status_filter:
        params.append(f"status={status_filter}")

    if not params:
        return base_url

    return f"{base_url}?{'&'.join(params)}"


def _proposal_safe_return_to(request, *, mode: str | None = None):
    status_filter = _get_proposal_list_status_filter(request)
    return _proposal_list_url(mode=mode, status_filter=status_filter)


def _build_proposal_list_actions(active_filter: str | None, list_mode: str):
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
                "url": _proposal_list_url(status_filter=active_filter),
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
            "url": _proposal_list_url(mode="reorder", status_filter=active_filter),
            "method": "get",
            "icon": "list-ordered",
            "order": 10,
            "desktop_position": "menu",
            "mobile_position": "menu",
        },
        {
            "key": "enter_delete_mode",
            "label": "Eliminar Propuestas",
            "url": _proposal_list_url(mode="delete", status_filter=active_filter),
            "method": "get",
            "icon": "trash-2",
            "order": 20,
            "desktop_position": "menu",
            "mobile_position": "menu",
        },
    ]

    actions.extend(_build_proposal_list_filter_actions(active_filter))
    return actions


def _build_proposal_list_filter_actions(active_filter: str | None):
    base_url = reverse("proposal_list")

    filters = [
        {
            "key": "filter_pending_review",
            "label": "Ver solo pendientes de revisión",
            "url": _proposal_list_url(status_filter="pending_review"),
            "icon": "clock",
            "status_filter": "pending_review",
            "order": 100,
        },
        {
            "key": "filter_approved",
            "label": "Ver solo aprobadas",
            "url": _proposal_list_url(status_filter="approved"),
            "icon": "check",
            "status_filter": "approved",
            "order": 110,
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

def _proposal_list_parent():
    return BreadcrumbParent(
        label="Propuestas",
        url=reverse("proposal_list"),
    )


def _proposal_detail_parent(proposal: dict):
    return BreadcrumbParent(
        label=proposal.get("title") or "Propuesta",
        url=reverse("proposal_detail", args=[proposal["id"]]),
    )


def _proposal_entity_name(proposal_review: dict) -> str:
    payload = proposal_review.get("payload") or {}

    if payload.get("is_create_meal") and payload.get("meal"):
        return payload["meal"].get("name") or "Comida propuesta"

    if payload.get("is_create_dailyplan") and payload.get("dailyplan"):
        return payload["dailyplan"].get("name") or "DailyPlan propuesto"

    return "Entidad propuesta"


def _proposal_entity_kind(proposal_review: dict) -> str:
    payload = proposal_review.get("payload") or {}

    if payload.get("is_create_meal") and payload.get("meal"):
        return "meal"

    if payload.get("is_create_dailyplan") and payload.get("dailyplan"):
        return "dailyplan"

    return "unsupported"


def _strip_proposal_entity_actions(card: dict | None) -> dict:
    if not isinstance(card, dict):
        return {}

    clean_card = dict(card)
    clean_card["actions"] = []
    return clean_card


def _build_dailyplan_child_cards_for_proposal_entity(proposal_review: dict) -> list[dict]:
    payload = proposal_review.get("payload") or {}
    dailyplan = payload.get("dailyplan") or {}
    child_cards = []

    for index, item in enumerate(dailyplan.get("meals") or [], start=1):
        meal = item.get("meal") or {}
        card = _strip_proposal_entity_actions(meal.get("card"))

        if not card:
            continue

        card.setdefault("id", f"proposal-dailyplan-meal-{index}")
        card.setdefault("main_id", card["id"])
        child_cards.append(card)

    return child_cards


def _build_proposal_entity_content(proposal: dict, proposal_review: dict):
    payload = proposal_review.get("payload") or {}
    entity_kind = _proposal_entity_kind(proposal_review)
    entity_name = _proposal_entity_name(proposal_review)

    if entity_kind == "meal":
        meal = payload.get("meal") or {}
        main_card = _strip_proposal_entity_actions(meal.get("card"))
        return {
            "entity_kind": entity_kind,
            "entity_name": entity_name,
            "main_card": main_card,
            "child_cards": [],
            "structural_indicators": {},
            "foods_aggregation": [],
        }

    if entity_kind == "dailyplan":
        dailyplan = payload.get("dailyplan") or {}
        main_card = _strip_proposal_entity_actions(dailyplan.get("card"))
        child_cards = _build_dailyplan_child_cards_for_proposal_entity(
            proposal_review,
        )
        structural_indicators = {
            "meals_count": len(child_cards),
            "foods_count": (
                main_card.get("titulo", {})
                .get("structural_indicators", {})
                .get("foods_count", 0)
            ),
        }

        foods = []
        seen = set()
        for child in child_cards:
            for food in child.get("foods_aggregation") or []:
                name = food.get("display_name")
                if not name or name in seen:
                    continue
                seen.add(name)
                foods.append(food)

        return {
            "entity_kind": entity_kind,
            "entity_name": entity_name,
            "main_card": main_card,
            "child_cards": child_cards,
            "structural_indicators": structural_indicators,
            "foods_aggregation": foods,
        }

    return {
        "entity_kind": entity_kind,
        "entity_name": entity_name,
        "main_card": {},
        "child_cards": [],
        "structural_indicators": {},
        "foods_aggregation": [],
    }


def _get_proposal_model_for_action(user, proposal_id: int):
    return get_object_or_404(
        get_available_proposal_queryset(user),
        pk=proposal_id,
    )


def _build_detail_actions(proposal: dict):
    if not proposal["is_reviewable"]:
        return []

    return [
        {
            "key": "approve",
            "label": "Aprobar propuesta",
            "url": reverse("proposal_approve", args=[proposal["id"]]),
            "method": "post",
            "icon": "check",
            "order": 10,
            "desktop_position": "inline",
            "mobile_position": "inline",
        },
        {
            "key": "reject",
            "label": "Rechazar propuesta",
            "url": reverse("proposal_reject", args=[proposal["id"]]),
            "method": "post",
            "icon": "x",
            "order": 20,
            "desktop_position": "inline",
            "mobile_position": "inline",
        },
        {
            "key": "cancel",
            "label": "Cancelar propuesta",
            "url": reverse("proposal_cancel", args=[proposal["id"]]),
            "method": "post",
            "icon": "ban",
            "order": 30,
            "desktop_position": "menu",
            "mobile_position": "menu",
        },
    ]


def _get_proposal_intent(proposal):
    payload = proposal.proposed_payload

    if not isinstance(payload, dict):
        return None

    intent = payload.get("intent")

    if isinstance(intent, str) and intent.strip():
        return intent.strip()

    return None


@login_required
def proposal_list(request):
    status_filter = _get_proposal_list_status_filter(request)
    list_mode = _normalize_proposal_list_mode(request)
    proposals = [
        proposal.as_dict()
        for proposal in list_user_proposals(
            request.user,
            status_filter=status_filter,
        )
    ]
    request.session["proposal_notification_seen_count"] = get_available_proposal_queryset(
        request.user,
    ).filter(is_read=False).count()

    content_vm = ProposalListContentVM(
        header=build_page_header(
            title="Propuestas",
            actions=_build_proposal_list_actions(status_filter, list_mode),
        ),
        proposals=proposals,
        list_mode=list_mode,
    )

    ui_vm = build_ui_vm(PROPOSAL_VIEWMODE_LIST)

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/proposals/list.html",
        base_vm.as_context(),
    )


@login_required
@require_POST
def proposal_list_reorder(request):
    ordered_ids = request.POST.getlist("order[]")

    if not ordered_ids:
        return HttpResponseBadRequest("No order received.")

    proposals = {
        proposal.id: proposal
        for proposal in get_available_proposal_queryset(request.user).filter(
            id__in=ordered_ids,
        )
    }

    for index, raw_id in enumerate(ordered_ids):
        try:
            proposal_id = int(raw_id)
        except (TypeError, ValueError):
            continue

        proposal = proposals.get(proposal_id)
        if not proposal:
            continue

        if proposal.list_order != index:
            proposal.list_order = index
            proposal.save(update_fields=["list_order"])

    return HttpResponse(status=204)


@login_required
@require_POST
def proposal_list_bulk_delete(request):
    selected_ids = request.POST.getlist("selected_ids[]")

    if not selected_ids:
        messages.info(request, "No seleccionaste propuestas para eliminar.")
        return redirect(_proposal_safe_return_to(request, mode="delete"))

    proposals = get_available_proposal_queryset(request.user).filter(
        id__in=selected_ids,
    )

    deleted_count = 0

    for proposal in proposals:
        try:
            delete_proposal(
                user=request.user,
                proposal=proposal,
            )
            deleted_count += 1
        except ValueError:
            continue

    if deleted_count:
        messages.success(request, f"{deleted_count} propuesta(s) eliminada(s).")
    else:
        messages.info(request, "No se eliminaron propuestas.")

    return redirect(_proposal_safe_return_to(request, mode="delete"))


@login_required
@require_POST
def proposal_delete(request, proposal_id):
    proposal = _get_proposal_model_for_action(
        request.user,
        proposal_id,
    )

    delete_proposal(
        user=request.user,
        proposal=proposal,
    )

    messages.success(request, "Propuesta eliminada.")

    return redirect(_proposal_safe_return_to(request))


@login_required
def proposal_detail(request, proposal_id):
    proposal = get_proposal_detail(
        request.user,
        proposal_id,
    ).as_dict()

    get_available_proposal_queryset(request.user).filter(
        pk=proposal_id,
        is_read=False,
    ).update(is_read=True)

    proposal_review = build_proposal_review_vm(
        proposal,
    ).as_dict()

    content_vm = ProposalDetailContentVM(
        header=build_page_header(
            title=proposal["title"],
            actions=_build_detail_actions(proposal),
        ),
        proposal=proposal,
        proposal_review=proposal_review,
    )

    ui_vm = build_ui_vm(
        PROPOSAL_VIEWMODE_DETAIL,
        instance=proposal["title"],
        back_config={
            "type": "nav_item",
        },
    )

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/proposals/detail.html",
        base_vm.as_context(),
    )


@login_required
def proposal_entity_detail(request, proposal_id):
    proposal = get_proposal_detail(
        request.user,
        proposal_id,
    ).as_dict()

    get_available_proposal_queryset(request.user).filter(
        pk=proposal_id,
        is_read=False,
    ).update(is_read=True)

    proposal_review = build_proposal_review_vm(
        proposal,
    ).as_dict()

    entity_content = _build_proposal_entity_content(
        proposal,
        proposal_review,
    )

    if entity_content["entity_kind"] == "unsupported":
        messages.error(
            request,
            "Esta propuesta no tiene una entidad propuesta disponible para revisar.",
        )
        return redirect(
            "proposal_detail",
            proposal_id=proposal_id,
        )

    content_vm = ProposalEntityDetailContentVM(
        header=build_page_header(
            title=entity_content["entity_name"],
            actions=[],
        ),
        proposal=proposal,
        proposal_review=proposal_review,
        entity_kind=entity_content["entity_kind"],
        entity_name=entity_content["entity_name"],
        main_card=entity_content["main_card"],
        child_cards=entity_content["child_cards"],
        structural_indicators=entity_content["structural_indicators"],
        foods_aggregation=entity_content["foods_aggregation"],
    )

    ui_vm = build_ui_vm(
        PROPOSAL_VIEWMODE_DETAIL,
        parents=[
            _proposal_detail_parent(proposal),
        ],
        instance=entity_content["entity_name"],
        back_config={
            "type": "parent",
        },
    )

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/proposals/entity_detail.html",
        base_vm.as_context(),
    )


@login_required
@require_POST
def proposal_approve(request, proposal_id):
    proposal = _get_proposal_model_for_action(
        request.user,
        proposal_id,
    )

    approve_proposal(
        user=request.user,
        proposal=proposal,
    )

    messages.success(request, "Propuesta aprobada.")

    return redirect(
        "proposal_detail",
        proposal_id=proposal.id,
    )


@login_required
@require_POST
def proposal_reject(request, proposal_id):
    proposal = _get_proposal_model_for_action(
        request.user,
        proposal_id,
    )

    reject_proposal(
        user=request.user,
        proposal=proposal,
    )

    messages.success(request, "Propuesta rechazada.")

    return redirect(
        "proposal_detail",
        proposal_id=proposal.id,
    )


@login_required
@require_POST
def proposal_cancel(request, proposal_id):
    proposal = _get_proposal_model_for_action(
        request.user,
        proposal_id,
    )

    cancel_proposal(
        user=request.user,
        proposal=proposal,
    )

    messages.success(request, "Propuesta cancelada.")

    return redirect(
        "proposal_detail",
        proposal_id=proposal.id,
    )


@login_required
def proposal_apply(request, proposal_id):
    if request.method != "POST":
        return redirect(
            "proposal_detail",
            proposal_id=proposal_id,
        )

    proposal = _get_proposal_model_for_action(
        request.user,
        proposal_id,
    )

    intent = _get_proposal_intent(proposal)

    try:
        if intent == CREATE_MEAL_INTENT:
            result = apply_approved_create_meal_proposal(
                user=request.user,
                proposal=proposal,
            )

            messages.success(
                request,
                f'Propuesta aplicada. Comida creada: "{result.meal.name}".',
            )

        elif intent == CREATE_DAILYPLAN_INTENT:
            result = apply_approved_create_dailyplan_proposal(
                user=request.user,
                proposal=proposal,
            )

            messages.success(
                request,
                f'Propuesta aplicada. DailyPlan creado: "{result.dailyplan.name}".',
            )

        else:
            messages.error(
                request,
                "Esta propuesta no tiene un tipo aplicable.",
            )

    except ValueError as exc:
        messages.error(
            request,
            f"No se pudo aplicar la propuesta: {exc}",
        )

    return redirect(
        "proposal_detail",
        proposal_id=proposal_id,
    )