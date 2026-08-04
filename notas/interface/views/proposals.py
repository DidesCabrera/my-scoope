from dataclasses import dataclass

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from notas.application.ai_intake.dailyplan_generator import (
    DailyPlanGeneratorError,
    generate_dailyplan_proposal_from_brief_proposal,
)
from notas.application.proposals.contracts import (
    CREATE_DAILYPLAN_INTENT,
    CREATE_MEAL_INTENT,
    resolve_proposal_intent,
)
from notas.application.proposals.subject_context_warnings import (
    proposal_requires_external_subject_ack,
)
from notas.application.queries.proposal_queries import (
    get_available_proposal_queryset,
    get_proposal_detail,
    list_user_proposals,
)
from notas.application.services.commands.proposal_commands import (
    apply_approved_create_dailyplan_proposal,
    apply_approved_create_meal_proposal,
    approve_proposal,
    cancel_proposal,
    delete_proposal,
    reject_proposal,
)
from notas.presentation.composition.viewmodel.components.builder_headers import (
    build_page_header,
)
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import (
    PROPOSAL_VIEWMODE_DETAIL,
    PROPOSAL_VIEWMODE_LIST,
)
from notas.presentation.proposals.entity_page import (
    ProposalEntityDetailContentVM,
    build_proposal_entity_content,
)
from notas.presentation.proposals.list_page import (
    ProposalListContentVM,
    build_proposal_list_actions,
    normalize_proposal_list_mode,
    proposal_safe_return_to,
    resolve_proposal_list_status_filter,
)
from notas.presentation.proposals.proposal_review_viewmodels import (
    build_proposal_review_vm,
)
from notas.presentation.viewmodels.base_vm import BaseVM


@dataclass
class ProposalDetailContentVM:
    header: object
    proposal: dict
    proposal_review: dict


@dataclass(frozen=True)
class BreadcrumbParent:
    label: str
    url: str

    def __str__(self):
        return self.label

    def get_absolute_url(self):
        return self.url


def _proposal_request_status_filter(request):
    return resolve_proposal_list_status_filter(
        get_status=request.GET.get("status"),
        post_status=request.POST.get("status"),
    )


def _proposal_return_to(request, *, mode: str | None = None) -> str:
    return proposal_safe_return_to(
        status_filter=_proposal_request_status_filter(request),
        mode=mode,
    )


def _proposal_detail_parent(proposal: dict):
    return BreadcrumbParent(
        label=proposal.get("title") or "Propuesta",
        url=reverse("proposal_detail", args=[proposal["id"]]),
    )


def _get_proposal_model_for_action(user, proposal_id: int):
    return get_object_or_404(
        get_available_proposal_queryset(user),
        pk=proposal_id,
    )


def _build_detail_actions(proposal: dict):
    return [
        {
            "key": "delete",
            "label": "Eliminar propuesta",
            "url": reverse("proposal_delete", args=[proposal["id"]]),
            "method": "post",
            "icon": "trash-2",
            "order": 30,
            "desktop_position": "menu",
            "mobile_position": "menu",
        },
    ]


@login_required
def proposal_list(request):
    status_filter = _proposal_request_status_filter(request)
    list_mode = normalize_proposal_list_mode(request.GET.get("mode"))
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
            actions=build_proposal_list_actions(status_filter, list_mode),
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
        return redirect(_proposal_return_to(request, mode="delete"))

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

    return redirect(_proposal_return_to(request, mode="delete"))


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

    return redirect(_proposal_return_to(request))


@login_required
@require_POST
def proposal_generate_dailyplan(request, proposal_id):
    source_proposal = _get_proposal_model_for_action(
        request.user,
        proposal_id,
    )

    try:
        result = generate_dailyplan_proposal_from_brief_proposal(
            user=request.user,
            source_proposal=source_proposal,
        )
    except DailyPlanGeneratorError as exc:
        messages.error(
            request,
            _dailyplan_generator_error_message(str(exc)),
        )
        return redirect(
            "proposal_detail",
            proposal_id=proposal_id,
        )

    messages.success(
        request,
        "Propuesta de DailyPlan creada desde el brief nutricional.",
    )
    return redirect(
        "proposal_detail",
        proposal_id=result.proposal.id,
    )


def _dailyplan_generator_error_message(error_code: str) -> str:
    messages_by_code = {
        "dailyplan_generator_not_allowed": "No tienes permisos para generar un plan desde esta propuesta.",
        "dailyplan_generator_source_payload_invalid": "La propuesta no contiene un payload válido para generar un plan.",
        "dailyplan_generator_source_must_be_nutrition_brief": "Solo se puede generar un DailyPlan desde propuestas de tipo NutritionBrief.",
        "dailyplan_generator_source_not_active": "La propuesta base ya no está activa para generar un plan.",
        "dailyplan_generator_brief_not_found": "No se encontró el NutritionBrief dentro de la propuesta.",
        "dailyplan_generator_only_supports_daily_plan_briefs": "Este generador inicial solo soporta briefs de Plan diario; Programas quedan para un patch posterior.",
        "dailyplan_generator_requires_at_least_three_readable_foods": "Necesitas al menos tres alimentos disponibles para generar una propuesta inicial.",
        "dailyplan_generator_food_candidates_not_found": "No se encontraron alimentos suficientes que respeten las exclusiones del brief.",
    }
    return messages_by_code.get(
        error_code,
        f"No se pudo generar la propuesta de DailyPlan: {error_code}",
    )


@login_required
def proposal_detail(request, proposal_id):
    get_available_proposal_queryset(request.user).filter(
        pk=proposal_id,
        is_read=False,
    ).update(is_read=True)

    proposal = get_proposal_detail(
        request.user,
        proposal_id,
    ).as_dict()

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
    get_available_proposal_queryset(request.user).filter(
        pk=proposal_id,
        is_read=False,
    ).update(is_read=True)

    proposal = get_proposal_detail(
        request.user,
        proposal_id,
    ).as_dict()

    proposal_review = build_proposal_review_vm(
        proposal,
    ).as_dict()

    entity_content = build_proposal_entity_content(
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

    intent = resolve_proposal_intent(proposal.proposed_payload)

    if (
        proposal_requires_external_subject_ack(proposal)
        and request.POST.get("ack_external_subject_ppk_warning") != "1"
    ):
        messages.error(
            request,
            "Antes de aplicar esta propuesta externa debes confirmar que entiendes que el PPK se recalculará con tu ficha personal.",
        )
        return redirect(
            "proposal_detail",
            proposal_id=proposal_id,
        )

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