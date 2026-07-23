import uuid
from dataclasses import replace

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods

from ai_assistant.application.chat_engines import ChatEngineRequest
from ai_assistant.application.prepared_actions import (
    cancel_prepared_action,
    commit_prepared_action,
)
from ai_assistant.application.tools import (
    TOOL_COMMIT_PROFILE_UPDATE,
    execute_profile_commit_tool,
)
from ai_assistant.domain import AssistantToolRequest, AssistantToolStatus
from core.rate_limits import limit_ai_assistant_turn
from notas.application.ai_intake.chat_engine import get_nutrition_intake_chat_engine
from notas.application.ai_intake.chat_history import (
    AI_NUTRITION_CHAT_SESSION_KEY,
    mark_chat_proposal_created,
    sync_chat_from_conversation,
)
from notas.application.ai_intake.dailyplan_generator import (
    DailyPlanGeneratorError,
    generate_dailyplan_proposal_from_brief_proposal,
)
from notas.application.ai_intake.nutrition_brief import (
    AI_NUTRITION_BRIEF_SESSION_KEY,
    AI_NUTRITION_CONVERSATION_SESSION_KEY,
    build_brief_from_form,
    build_conversation_from_brief,
    build_intake_result,
    append_profile_update_confirmation_message,
    build_intake_result_from_brief,
    deserialize_brief,
    deserialize_conversation,
    serialize_brief,
    serialize_conversation,
    NutritionConversationState,
)
from notas.application.ai_intake.profile_draft_update import (
    apply_profile_update_result_to_brief,
    build_profile_draft_payload_from_brief,
    profile_update_result_from_tool_data,
)
from notas.application.ai_intake.proposal_from_brief import (
    create_nutrition_brief_proposal,
)
from notas.application.ai_intake.plan_iteration import (
    create_iterated_dailyplan_proposal,
    should_iterate_generated_plan,
)
from notas.domain.models import AiNutritionChat
from notas.presentation.pages.ai_intake_page import (
    append_generated_plan_message,
    append_iterated_plan_message,
    build_brief_edit_content,
    build_chat_list_content,
    build_intake_content,
)
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import (
    CHAT_VIEWMODE_DETAIL,
    CHAT_VIEWMODE_LIST,
    HOME_VIEWMODE,
)
from notas.presentation.viewmodels.base_vm import BaseVM


def _continue_chat_with_active_engine(*, request, message: str, existing_payload=None, existing_chat_id=None):
    turn_result = get_nutrition_intake_chat_engine().continue_chat(
        ChatEngineRequest(
            message=message,
            existing_payload=existing_payload,
            user_id=getattr(request.user, "id", None),
            metadata={
                "surface": "ai_nutrition_intake",
                "tool_user": request.user,
                "conversation_id": str(existing_chat_id or ""),
                "turn_id": uuid.uuid4().hex,
                "action_type": "assistant.ai_nutrition_intake.preview",
            },
        )
    )
    return turn_result.state


def _is_async_request(request) -> bool:
    return (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or "application/json" in request.headers.get("accept", "")
        or request.POST.get("is_async") == "1"
    )


def _render_chat_thread_json(request, *, result, conversation, prompt: str = "") -> JsonResponse:
    content_vm = build_intake_content(
        result=result,
        conversation=conversation,
        prompt=prompt,
        active_chat=_get_active_chat(request),
    )
    base_vm = BaseVM(
        ui=build_ui_vm(CHAT_VIEWMODE_DETAIL),
        content=content_vm,
    )
    return JsonResponse(
        {
            "thread_html": render_to_string(
                "notas/_ai_chat_thread.html",
                base_vm.as_context(),
                request=request,
            ),
            "is_ready_for_proposal": bool(result and result.is_ready_for_proposal),
            "engine_status": content_vm.engine_status or {},
        }
    )


def _sync_session_from_conversation(request, conversation, *, existing_chat_id=None) -> AiNutritionChat:
    chat = sync_chat_from_conversation(
        user=request.user,
        conversation=conversation,
        existing_chat_id=existing_chat_id,
    )
    request.session[AI_NUTRITION_CONVERSATION_SESSION_KEY] = serialize_conversation(conversation)
    request.session[AI_NUTRITION_BRIEF_SESSION_KEY] = serialize_brief(conversation.result.brief)
    request.session[AI_NUTRITION_CHAT_SESSION_KEY] = chat.id
    request.session.modified = True
    return chat


def _load_chat_into_session(request, chat: AiNutritionChat):
    conversation = deserialize_conversation(chat.conversation_payload)
    if not conversation:
        raise Http404("Chat no encontrado")

    request.session[AI_NUTRITION_CONVERSATION_SESSION_KEY] = chat.conversation_payload
    request.session[AI_NUTRITION_BRIEF_SESSION_KEY] = chat.brief_payload
    request.session[AI_NUTRITION_CHAT_SESSION_KEY] = chat.id
    request.session.modified = True
    return conversation


def _clear_active_chat_session(request) -> None:
    request.session.pop(AI_NUTRITION_BRIEF_SESSION_KEY, None)
    request.session.pop(AI_NUTRITION_CONVERSATION_SESSION_KEY, None)
    request.session.pop(AI_NUTRITION_CHAT_SESSION_KEY, None)
    request.session.modified = True


def _update_prepared_action_card_status(
    request,
    *,
    public_id,
    status: str,
) -> None:
    conversation = deserialize_conversation(
        request.session.get(AI_NUTRITION_CONVERSATION_SESSION_KEY)
    )
    if conversation is None:
        return
    action_id = str(public_id)
    messages_updated = False
    updated_messages = []
    for message in conversation.messages:
        card = message.prepared_action_card
        if isinstance(card, dict) and str(card.get("id")) == action_id:
            updated_messages.append(
                replace(message, prepared_action_card={**card, "status": status})
            )
            messages_updated = True
        else:
            updated_messages.append(message)
    if not messages_updated:
        return
    updated_conversation = NutritionConversationState(
        messages=updated_messages,
        result=conversation.result,
    )
    _sync_session_from_conversation(
        request,
        updated_conversation,
        existing_chat_id=request.session.get(AI_NUTRITION_CHAT_SESSION_KEY),
    )


def _get_active_chat(request) -> AiNutritionChat | None:
    if request is None or not getattr(request, "user", None) or not request.user.is_authenticated:
        return None

    chat_id = request.session.get(AI_NUTRITION_CHAT_SESSION_KEY)
    if not chat_id:
        return None

    try:
        return AiNutritionChat.objects.select_related("proposal").get(
            id=chat_id,
            user=request.user,
        )
    except (AiNutritionChat.DoesNotExist, TypeError, ValueError):
        return None


@require_http_methods(["GET", "POST"])
@limit_ai_assistant_turn
@login_required
def ai_nutrition_intake(request):
    prompt = ""
    result = None
    conversation = None

    if request.method == "POST":
        action = request.POST.get("action") or "analyze_prompt"

        if action in {"analyze_prompt", "continue_conversation"}:
            message_field = "message" if action == "continue_conversation" else "prompt"
            message = (
                request.POST.get(message_field)
                or request.POST.get("message")
                or request.POST.get("prompt")
                or ""
            ).strip()
            if not message:
                if _is_async_request(request):
                    return JsonResponse(
                        {"error": "conversation_message_required"},
                        status=400,
                    )
                messages.error(request, "Escribe una respuesta para continuar el asistente nutricional.")
                return redirect("ai_nutrition_intake")

            existing_payload = None
            existing_chat_id = None
            if action == "continue_conversation":
                existing_payload = request.session.get(AI_NUTRITION_CONVERSATION_SESSION_KEY)
                existing_chat_id = request.session.get(AI_NUTRITION_CHAT_SESSION_KEY)

            try:
                conversation = _continue_chat_with_active_engine(
                    request=request,
                    message=message,
                    existing_payload=existing_payload,
                    existing_chat_id=existing_chat_id,
                )
            except ValueError:
                if _is_async_request(request):
                    return JsonResponse(
                        {"error": "conversation_message_required"},
                        status=400,
                    )
                messages.error(request, "Escribe una respuesta para continuar el asistente nutricional.")
                return redirect("ai_nutrition_intake")

            chat = _sync_session_from_conversation(
                request,
                conversation,
                existing_chat_id=existing_chat_id,
            )

            if should_iterate_generated_plan(chat=chat, message=message):
                try:
                    iteration_result = create_iterated_dailyplan_proposal(
                        user=request.user,
                        brief=conversation.result.brief,
                        previous_proposal=chat.proposal,
                        user_message=message,
                    )
                    conversation = append_iterated_plan_message(
                        conversation,
                        user_message=message,
                        previous_proposal=chat.proposal,
                        proposal=iteration_result.proposal,
                    )
                    _sync_session_from_conversation(
                        request,
                        conversation,
                        existing_chat_id=chat.id,
                    )
                    mark_chat_proposal_created(
                        user=request.user,
                        chat_id=chat.id,
                        proposal=iteration_result.proposal,
                    )
                except DailyPlanGeneratorError as exc:
                    messages.error(request, f"No se pudo actualizar la propuesta: {exc}")

            if _is_async_request(request):
                return _render_chat_thread_json(
                    request,
                    result=conversation.result,
                    conversation=conversation,
                    prompt=conversation.result.prompt,
                )
            return redirect("ai_nutrition_intake")

        if action == "reset_brief":
            _clear_active_chat_session(request)
            messages.success(request, "Brief nutricional reiniciado.")
            return redirect("home_view")

        if action == "update_profile_from_draft":
            brief = deserialize_brief(request.session.get(AI_NUTRITION_BRIEF_SESSION_KEY))
            conversation = deserialize_conversation(
                request.session.get(AI_NUTRITION_CONVERSATION_SESSION_KEY)
            )
            if not brief or not conversation:
                messages.error(request, "Primero completa una ficha en el chat.")
                return redirect("ai_nutrition_intake")

            tool_result = execute_profile_commit_tool(
                AssistantToolRequest(
                    tool_name=TOOL_COMMIT_PROFILE_UPDATE,
                    arguments={
                        "profile_draft": build_profile_draft_payload_from_brief(brief),
                    },
                    request_id="profile_card_approval",
                    reason="User clicked the profile card approval button in the chat UI.",
                    metadata={
                        "approved_by_user": True,
                        "approval_source": "profile_card_button",
                        "surface": "ai_nutrition_intake",
                    },
                ),
                user=request.user,
            )
            if tool_result.status != AssistantToolStatus.OK:
                messages.error(request, "No pude actualizar la ficha personal desde este chat.")
                return redirect("ai_nutrition_intake")

            update_result = profile_update_result_from_tool_data(tool_result.data)
            updated_brief = apply_profile_update_result_to_brief(brief, update_result)
            conversation = append_profile_update_confirmation_message(
                conversation,
                brief=updated_brief,
                assistant_text=update_result.user_message,
            )
            _sync_session_from_conversation(
                request,
                conversation,
                existing_chat_id=request.session.get(AI_NUTRITION_CHAT_SESSION_KEY),
            )
            if update_result.has_updates:
                messages.success(request, "Ficha personal actualizada.")
            else:
                messages.info(request, "No había cambios nuevos para guardar en tu ficha personal.")
            return redirect("ai_nutrition_intake")

        if action == "create_proposal":
            brief = deserialize_brief(request.session.get(AI_NUTRITION_BRIEF_SESSION_KEY))
            if not brief:
                messages.error(request, "Primero crea o guarda un brief nutricional.")
                return redirect("ai_nutrition_intake")

            try:
                proposal_result = create_nutrition_brief_proposal(
                    user=request.user,
                    brief=brief,
                )
                generated_result = generate_dailyplan_proposal_from_brief_proposal(
                    user=request.user,
                    source_proposal=proposal_result.proposal,
                )
            except DailyPlanGeneratorError as exc:
                messages.error(request, f"No se pudo generar el DailyPlan inicial: {exc}")
                return redirect("ai_nutrition_intake")
            except ValueError as exc:
                if str(exc) == "nutrition_brief_has_pending_questions":
                    messages.error(
                        request,
                        "Completa los datos mínimos pendientes antes de crear la propuesta.",
                    )
                else:
                    messages.error(request, f"No se pudo crear la propuesta: {exc}")
                return redirect("ai_nutrition_intake")

            conversation = deserialize_conversation(
                request.session.get(AI_NUTRITION_CONVERSATION_SESSION_KEY)
            ) or build_conversation_from_brief(brief=brief)
            conversation = append_generated_plan_message(
                conversation,
                proposal=generated_result.proposal,
            )
            _sync_session_from_conversation(
                request,
                conversation,
                existing_chat_id=request.session.get(AI_NUTRITION_CHAT_SESSION_KEY),
            )
            mark_chat_proposal_created(
                user=request.user,
                chat_id=request.session.get(AI_NUTRITION_CHAT_SESSION_KEY),
                proposal=generated_result.proposal,
            )
            messages.success(request, "Propuesta de DailyPlan creada en el chat.")
            return redirect("ai_nutrition_intake")

    else:
        prompt = (request.GET.get("prompt") or "").strip()
        if prompt:
            conversation = _continue_chat_with_active_engine(
                request=request,
                message=prompt,
                existing_payload=None,
                existing_chat_id=None,
            )
            _sync_session_from_conversation(request, conversation, existing_chat_id=None)
            return redirect("ai_nutrition_intake")

        conversation = deserialize_conversation(
            request.session.get(AI_NUTRITION_CONVERSATION_SESSION_KEY)
        )
        if conversation:
            result = conversation.result
            prompt = result.prompt
        else:
            brief = deserialize_brief(request.session.get(AI_NUTRITION_BRIEF_SESSION_KEY))
            if brief:
                result = build_intake_result_from_brief(brief)
                prompt = brief.raw_prompt
                conversation = build_conversation_from_brief(brief=brief)
            else:
                result = None

    if conversation and result is None:
        result = conversation.result
        prompt = result.prompt
    elif result and conversation is None:
        conversation = build_conversation_from_brief(brief=result.brief)
    elif not result and prompt:
        result = build_intake_result(prompt)

    content_vm = build_intake_content(
        result=result,
        conversation=conversation,
        prompt=prompt,
        active_chat=_get_active_chat(request),
    )

    base_vm = BaseVM(
        ui=build_ui_vm(CHAT_VIEWMODE_DETAIL if conversation else HOME_VIEWMODE),
        content=content_vm,
    )

    return render(
        request,
        "notas/ai_intake.html",
        base_vm.as_context(),
    )


@require_http_methods(["GET", "POST"])
@login_required
def ai_nutrition_brief_edit(request):
    brief = deserialize_brief(request.session.get(AI_NUTRITION_BRIEF_SESSION_KEY))
    conversation = deserialize_conversation(
        request.session.get(AI_NUTRITION_CONVERSATION_SESSION_KEY)
    )

    if not brief:
        messages.error(request, "Primero inicia una conversación para crear un brief nutricional.")
        return redirect("ai_nutrition_intake")

    if request.method == "POST":
        action = request.POST.get("action") or "update_brief"
        if action == "update_brief":
            brief = build_brief_from_form(request.POST)
            request.session[AI_NUTRITION_BRIEF_SESSION_KEY] = serialize_brief(brief)
            conversation = build_conversation_from_brief(
                brief=brief,
                existing_payload=request.session.get(AI_NUTRITION_CONVERSATION_SESSION_KEY),
            )
            request.session[AI_NUTRITION_CONVERSATION_SESSION_KEY] = serialize_conversation(conversation)
            request.session.modified = True
            _sync_session_from_conversation(
                request,
                conversation,
                existing_chat_id=request.session.get(AI_NUTRITION_CHAT_SESSION_KEY),
            )
            messages.success(request, "Brief nutricional actualizado.")
            return redirect("ai_nutrition_intake")

    result = build_intake_result_from_brief(brief)
    content_vm = build_brief_edit_content(
        result=result,
        conversation=conversation,
        prompt=brief.raw_prompt,
    )

    base_vm = BaseVM(
        ui=build_ui_vm(CHAT_VIEWMODE_DETAIL),
        content=content_vm,
    )

    return render(
        request,
        "notas/ai_intake_brief_edit.html",
        base_vm.as_context(),
    )


@login_required
def ai_nutrition_chat_list(request):
    active_chat_id = request.session.get(AI_NUTRITION_CHAT_SESSION_KEY)
    content_vm = build_chat_list_content(
        AiNutritionChat.objects.filter(user=request.user)
        .select_related("proposal")
        .order_by("-updated_at", "-id"),
        active_chat_id=active_chat_id,
    )

    base_vm = BaseVM(
        ui=build_ui_vm(CHAT_VIEWMODE_LIST),
        content=content_vm,
    )

    return render(request, "notas/ai_chats/list.html", base_vm.as_context())


@login_required
def ai_nutrition_chat_new(request):
    _clear_active_chat_session(request)
    return redirect("ai_nutrition_intake")


@login_required
def ai_nutrition_chat_detail(request, chat_id):
    chat = get_object_or_404(AiNutritionChat, id=chat_id, user=request.user)
    conversation = _load_chat_into_session(request, chat)
    result = conversation.result

    content_vm = build_intake_content(
        result=result,
        conversation=conversation,
        prompt=result.prompt,
        active_chat=_get_active_chat(request),
    )

    base_vm = BaseVM(
        ui=build_ui_vm(CHAT_VIEWMODE_DETAIL, instance=chat),
        content=content_vm,
    )

    return render(request, "notas/ai_intake.html", base_vm.as_context())


@login_required
@require_http_methods(["POST"])
def ai_prepared_action_commit(request, action_id):
    try:
        action = commit_prepared_action(
            user=request.user,
            public_id=action_id,
        )
    except ValueError as exc:
        messages.error(request, f"No se pudo aplicar la acción preparada: {exc}.")
        return redirect("ai_nutrition_intake")
    _update_prepared_action_card_status(
        request,
        public_id=action.public_id,
        status=action.status,
    )
    messages.success(request, "Acción confirmada y aplicada.")
    return redirect("ai_nutrition_intake")


@login_required
@require_http_methods(["POST"])
def ai_prepared_action_cancel(request, action_id):
    try:
        action = cancel_prepared_action(
            user=request.user,
            public_id=action_id,
        )
    except ValueError as exc:
        messages.error(request, f"No se pudo cancelar la acción preparada: {exc}.")
        return redirect("ai_nutrition_intake")
    _update_prepared_action_card_status(
        request,
        public_id=action.public_id,
        status=action.status,
    )
    messages.info(request, "Acción preparada cancelada sin realizar cambios.")
    return redirect("ai_nutrition_intake")
