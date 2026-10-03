from ninja import Router

from mobile_api.ai_chats import chat_detail_payload
from mobile_api.api_support import require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.assistant import AIChatDetailEnvelope
from mobile_api.schema_domains.assistant_chat_edits import AIChatRenameInput
from mobile_api.schemas import ErrorEnvelope
from notas.application.ai_intake.chat_history import rename_chat
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE

router = Router()


@router.patch(
    "/ai/chats/{chat_id}/name",
    operation_id="mobile_api_api_rename_ai_chat",
    auth=mobile_bearer,
    response={200: AIChatDetailEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def rename_ai_chat(request, chat_id: int, payload: AIChatRenameInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        chat = rename_chat(user=request.auth.user, chat_id=chat_id, name=payload.name)
    except ValueError as exc:
        code = str(exc)
        raise MobileAPIError(
            code=code,
            message="AI chat was not found." if code == "ai_chat_not_found" else "The chat name is invalid.",
            status_code=404 if code == "ai_chat_not_found" else 422,
        ) from exc
    return success(chat_detail_payload(request.auth.user, chat.id))
