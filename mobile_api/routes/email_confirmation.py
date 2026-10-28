from typing import Literal

from allauth.account.models import EmailConfirmationHMAC
from ninja import Router, Schema

from mobile_api.api_support import success
from mobile_api.errors import MobileAPIError
from mobile_api.schemas import ErrorEnvelope

router = Router()


class EmailConfirmationInput(Schema):
    key: str


class EmailConfirmationEnvelope(Schema):
    ok: Literal[True] = True
    data: dict
    error: None = None


@router.post(
    "/auth/confirm-email",
    operation_id="mobile_api_confirm_email",
    auth=None,
    response={200: EmailConfirmationEnvelope, 400: ErrorEnvelope},
)
def confirm_email(request, payload: EmailConfirmationInput):
    confirmation = EmailConfirmationHMAC.from_key(payload.key)
    if confirmation is None or confirmation.confirm(request) is None:
        raise MobileAPIError(
            code="email_confirmation_invalid",
            message="The email confirmation link is invalid or expired.",
            status_code=400,
        )
    return success({})
