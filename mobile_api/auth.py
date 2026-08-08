from __future__ import annotations

from dataclasses import dataclass

from ninja.security import HttpBearer

from mobile_api.errors import MobileAPIError
from notas.application.services.mcp_user_tokens import validate_mcp_user_token
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_READ


@dataclass(frozen=True)
class MobileAuthContext:
    user: object
    token: object


class MobileBearer(HttpBearer):
    def authenticate(self, request, token):
        validation = validate_mcp_user_token(token, required_scopes=[MOBILE_SCOPE_READ])
        if not validation.ok:
            status_code = 403 if validation.error.code == "mcp_user_token_missing_scope" else 401
            raise MobileAPIError(
                code=validation.error.code,
                message=validation.error.message,
                details=validation.error.details,
                status_code=status_code,
            )
        request.user = validation.user
        return MobileAuthContext(user=validation.user, token=validation.token)


mobile_bearer = MobileBearer()
