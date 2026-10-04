from typing import Any

from ninja import Router

from mobile_api.api_support import comparison_error, require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.comparison_edits import rename_comparison
from mobile_api.comparisons import saved_comparison_detail_payload
from mobile_api.schema_domains.comparison_edits import SavedComparisonRenameInput
from mobile_api.schema_domains.comparisons import SavedComparisonDetailEnvelope
from mobile_api.schemas import ErrorEnvelope
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE

router = Router(auth=mobile_bearer)


@router.patch(
    "/comparisons/saved/{comparison_id}/name",
    response={200: SavedComparisonDetailEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
    operation_id="mobile_api_api_rename_mobile_saved_comparison",
)
def rename_mobile_saved_comparison(request: Any, comparison_id: int, payload: SavedComparisonRenameInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        comparison = rename_comparison(request.auth.user, comparison_id=comparison_id, name=payload.name)
    except ValueError as exc:
        raise comparison_error(exc) from exc
    return success(saved_comparison_detail_payload(request.auth.user, comparison.id))
