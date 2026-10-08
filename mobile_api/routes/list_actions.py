from typing import Any

from ninja import Router

from mobile_api.api_support import require_scope, success
from mobile_api.assistant_list_actions import bulk_delete_chats, bulk_delete_proposals
from mobile_api.auth import mobile_bearer
from mobile_api.schema_domains.list_actions import ListActionResultEnvelope, ListBulkDeleteInput
from mobile_api.schemas import ErrorEnvelope
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE

router = Router(auth=mobile_bearer)


@router.post(
    "/ai/chats/bulk-delete",
    operation_id="mobile_api_api_bulk_delete_ai_chats",
    response={200: ListActionResultEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def delete_ai_chats(request, payload: ListBulkDeleteInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(bulk_delete_chats(request.auth.user, payload.item_ids))


@router.post(
    "/proposals/bulk-delete",
    response={200: ListActionResultEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
    operation_id="mobile_api_api_bulk_delete_proposals",
)
def delete_proposals(request: Any, payload: ListBulkDeleteInput) -> dict[str, Any]:
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    return success(bulk_delete_proposals(request.auth.user, payload.item_ids))
