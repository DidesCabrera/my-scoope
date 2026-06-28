from dataclasses import dataclass

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from notas.application.ai_intake.chat_history import (
    AI_NUTRITION_CHAT_SESSION_KEY,
    mark_chat_proposal_created,
    sync_chat_from_conversation,
)
from notas.application.ai_intake.nutrition_brief import (
    AI_NUTRITION_BRIEF_SESSION_KEY,
    AI_NUTRITION_CONVERSATION_SESSION_KEY,
    build_brief_from_form,
    build_conversation_from_brief,
    build_intake_result,
    build_intake_result_from_brief,
    deserialize_brief,
    deserialize_conversation,
    serialize_brief,
    serialize_conversation,
    start_or_continue_conversation,
)
from notas.application.ai_intake.proposal_from_brief import (
    create_nutrition_brief_proposal,
)
from notas.domain.models import AiNutritionChat
from notas.presentation.composition.viewmodel.components.builder_headers import build_page_header
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import (
    CHAT_VIEWMODE_DETAIL,
    CHAT_VIEWMODE_LIST,
    HOME_VIEWMODE,
)
from notas.presentation.viewmodels.base_vm import BaseVM


@dataclass
class AiNutritionIntakeContentVM:
    header: object
    result: object | None
    conversation: object | None
    prompt: str = ""


@dataclass
class AiNutritionBriefEditContentVM:
    header: object
    result: object
    conversation: object | None
    prompt: str = ""


@dataclass(frozen=True)
class AiNutritionChatListItemVM:
    title: str
    subtitle: str
    preview: str
    status_label: str
    url: str


@dataclass(frozen=True)
class AiNutritionChatListContentVM:
    header: object
    chats: list[AiNutritionChatListItemVM]
    item_count: int


def _is_async_request(request) -> bool:
    return (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or "application/json" in request.headers.get("accept", "")
        or request.POST.get("is_async") == "1"
    )


def _build_intake_content(*, result, conversation, prompt: str = "") -> AiNutritionIntakeContentVM:
    return AiNutritionIntakeContentVM(
        header=_build_intake_header(has_result=result is not None),
        result=result,
        conversation=conversation,
        prompt=prompt,
    )


def _render_chat_thread_json(request, *, result, conversation, prompt: str = "") -> JsonResponse:
    content_vm = _build_intake_content(
        result=result,
        conversation=conversation,
        prompt=prompt,
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


def _build_intake_header(*, has_result: bool):
    actions = []

    if has_result:
        actions.append(
            {
                "key": "edit_nutrition_brief",
                "label": "Editar Brief Nutricional Manualmente",
                "url": reverse("ai_nutrition_brief_edit"),
                "method": "get",
                "icon": "sliders-horizontal",
                "order": 20,
                "desktop_position": "menu",
                "mobile_position": "menu",
            }
        )

    return build_page_header(title="Asistente nutricional", actions=actions)


@require_http_methods(["GET", "POST"])
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
                conversation = start_or_continue_conversation(
                    message=message,
                    existing_payload=existing_payload,
                )
            except ValueError:
                if _is_async_request(request):
                    return JsonResponse(
                        {"error": "conversation_message_required"},
                        status=400,
                    )
                messages.error(request, "Escribe una respuesta para continuar el asistente nutricional.")
                return redirect("ai_nutrition_intake")

            _sync_session_from_conversation(
                request,
                conversation,
                existing_chat_id=existing_chat_id,
            )
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
            except ValueError as exc:
                if str(exc) == "nutrition_brief_has_pending_questions":
                    messages.error(
                        request,
                        "Completa los datos mínimos pendientes antes de crear la propuesta.",
                    )
                else:
                    messages.error(request, f"No se pudo crear la propuesta: {exc}")
                return redirect("ai_nutrition_intake")

            mark_chat_proposal_created(
                user=request.user,
                chat_id=request.session.get(AI_NUTRITION_CHAT_SESSION_KEY),
                proposal=proposal_result.proposal,
            )
            _clear_active_chat_session(request)
            messages.success(request, "Propuesta creada desde el brief nutricional.")
            return redirect("proposal_detail", proposal_id=proposal_result.proposal.id)

    else:
        prompt = (request.GET.get("prompt") or "").strip()
        if prompt:
            conversation = start_or_continue_conversation(
                message=prompt,
                existing_payload=None,
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

    content_vm = _build_intake_content(
        result=result,
        conversation=conversation,
        prompt=prompt,
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
    content_vm = AiNutritionBriefEditContentVM(
        header=build_page_header(
            title="Editar Brief Nutricional",
            actions=[
                {
                    "key": "back_ai_intake",
                    "label": "Volver al chat",
                    "url": reverse("ai_nutrition_intake"),
                    "method": "get",
                    "icon": "arrow-left",
                    "order": 10,
                    "desktop_position": "inline",
                    "mobile_position": "inline",
                }
            ],
        ),
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
    chats = [
        AiNutritionChatListItemVM(
            title=chat.title,
            subtitle=chat.updated_at.strftime("%d/%m/%Y %H:%M"),
            preview=chat.last_message_preview or "Sin mensajes guardados.",
            status_label=chat.get_status_display(),
            url=reverse("ai_nutrition_chat_detail", args=[chat.id]),
        )
        for chat in AiNutritionChat.objects.filter(user=request.user).order_by("-updated_at", "-id")
    ]

    content_vm = AiNutritionChatListContentVM(
        header=build_page_header(title="Chats"),
        chats=chats,
        item_count=len(chats),
    )

    base_vm = BaseVM(
        ui=build_ui_vm(CHAT_VIEWMODE_LIST),
        content=content_vm,
    )

    return render(request, "notas/ai_chats/list.html", base_vm.as_context())


@login_required
def ai_nutrition_chat_detail(request, chat_id):
    chat = get_object_or_404(AiNutritionChat, id=chat_id, user=request.user)
    conversation = _load_chat_into_session(request, chat)
    result = conversation.result

    content_vm = _build_intake_content(
        result=result,
        conversation=conversation,
        prompt=result.prompt,
    )

    base_vm = BaseVM(
        ui=build_ui_vm(CHAT_VIEWMODE_DETAIL, instance=chat),
        content=content_vm,
    )

    return render(request, "notas/ai_intake.html", base_vm.as_context())
