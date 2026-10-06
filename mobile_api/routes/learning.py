from ninja import Router

from mobile_api.api_support import success
from mobile_api.auth import mobile_bearer
from mobile_api.schema_domains.learning import LearningCatalogEnvelope
from notas.application.learning_catalog import catalog_payload

router = Router()


@router.get(
    "/learning",
    operation_id="mobile_api_routes_learning_learning_catalog",
    auth=mobile_bearer,
    response={200: LearningCatalogEnvelope},
)
def learning_catalog(request):
    return success(catalog_payload())
