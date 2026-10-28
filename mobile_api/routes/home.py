from ninja import Router

from mobile_api.api_support import success
from mobile_api.auth import mobile_bearer
from mobile_api.home import home_payload, home_summary_payload
from mobile_api.schema_domains.home import HomeEnvelope, HomeSummaryEnvelope
from mobile_api.schemas import ErrorEnvelope

router = Router(auth=mobile_bearer)


@router.get(
    "/home",
    operation_id="mobile_api_api_home",
    response={200: HomeEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def home(request):
    return success(home_payload(request.auth.user))


@router.get(
    "/home/summary",
    operation_id="mobile_api_api_home_summary",
    response={200: HomeSummaryEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def home_summary(request):
    return success(home_summary_payload(request.auth.user))
