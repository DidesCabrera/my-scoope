from ninja import Router

from mobile_api.ai_chats import commit_chat_preferences
from mobile_api.api_support import require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.assistant_memory import AIClientMemoryCommitResultEnvelope
from mobile_api.schemas import ErrorEnvelope
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE

router = Router()


@router.post(
    "/ai/chats/{chat_id}/preferences/commit",
    operation_id="mobile_api_api_commit_ai_chat_preferences",
    auth=mobile_bearer,
    response={200: AIClientMemoryCommitResultEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope},
)
def commit_ai_chat_preferences(request, chat_id: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        result = commit_chat_preferences(request.auth.user, chat_id)
    except ValueError as exc:
        code = str(exc)
        status = 404 if code == "ai_chat_not_found" else 409
        raise MobileAPIError(
            code=code,
            message="The preference draft is no longer available.",
            status_code=status,
        ) from exc
    return success(result)
