from ninja import Router

from accounts.services.identity import rename_username
from mobile_api.api_support import require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.identity import SessionEnvelope
from mobile_api.schema_domains.identity_edits import UsernameRenameInput
from mobile_api.schemas import ErrorEnvelope
from mobile_api.selectors_identity import session_payload
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_ACCOUNT

router = Router()


@router.patch(
    "/account/username",
    operation_id="mobile_api_api_rename_account_username",
    auth=mobile_bearer,
    response={200: SessionEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
)
def rename_account_username(request, payload: UsernameRenameInput):
    require_scope(request.auth, MOBILE_SCOPE_ACCOUNT)
    try:
        rename_username(user=request.auth.user, username=payload.username)
    except ValueError as exc:
        code = str(exc)
        raise MobileAPIError(
            code=code,
            message="The username could not be updated.",
            status_code=422,
        ) from exc
    return success(session_payload(request.auth))
