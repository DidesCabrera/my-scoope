from ninja import Router

from mobile_api.api_support import success
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.proposals import ProposalListEnvelope
from mobile_api.schemas import ErrorEnvelope
from mobile_api.selectors_proposals import chat_proposal_list_payload

router = Router()


@router.get(
    "/ai/chats/{chat_id}/proposals",
    operation_id="mobile_api_api_ai_chat_proposals",
    auth=mobile_bearer,
    response={200: ProposalListEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def ai_chat_proposals(request, chat_id: int, offset: int = 0, limit: int = 30):
    payload = chat_proposal_list_payload(request.auth.user, chat_id, offset=offset, limit=limit)
    if payload is None:
        raise MobileAPIError(code="ai_chat_not_found", message="AI chat was not found.", status_code=404)
    return success(payload)
