from __future__ import annotations

from ninja import NinjaAPI
from ninja.errors import AuthenticationError
from ninja.errors import ValidationError as NinjaValidationError

from mobile_api.api_support import success as _success
from mobile_api.errors import MobileAPIError, error_envelope
from mobile_api.routes.assistant import router as assistant_router
from mobile_api.routes.billing import router as billing_router
from mobile_api.routes.calendarization import router as calendarization_router
from mobile_api.routes.calendarization_edits import router as calendarization_edits_router
from mobile_api.routes.comparisons import router as comparisons_router
from mobile_api.routes.composition import router as composition_router
from mobile_api.routes.identity import router as identity_router
from mobile_api.routes.label_capture import router as label_capture_router
from mobile_api.routes.libraries import router as libraries_router
from mobile_api.routes.proposals import router as proposals_router
from mobile_api.schemas import HealthEnvelope

api = NinjaAPI(
    title="My Scoope Consumer API",
    version="1.0.0",
    description="Versioned screen-oriented API for the My Scoope consumer mobile client.",
    urls_namespace="mobile_api_v1",
)


@api.exception_handler(MobileAPIError)
def handle_mobile_api_error(request, exc):
    return api.create_response(request, error_envelope(exc), status=exc.status_code)


@api.exception_handler(NinjaValidationError)
def handle_validation_error(request, exc):
    error = MobileAPIError(
        code="request_validation_failed",
        message="Request payload or parameters are invalid.",
        status_code=422,
        details={"errors": exc.errors},
    )
    return api.create_response(request, error_envelope(error), status=422)


@api.exception_handler(AuthenticationError)
def handle_authentication_error(request, exc):
    error = MobileAPIError(
        code="mobile_auth_required",
        message="A valid mobile bearer token is required.",
        status_code=401,
    )
    return api.create_response(request, error_envelope(error), status=401)


@api.get("/health", auth=None, response={200: HealthEnvelope})
def health(request):
    return _success({"status": "ok", "api_version": "v1"})


api.add_router("", identity_router)
api.add_router("", billing_router)
api.add_router("", calendarization_router)
api.add_router("", calendarization_edits_router)
api.add_router("", proposals_router)
api.add_router("", comparisons_router)
api.add_router("", label_capture_router)
api.add_router("", libraries_router)
api.add_router("", composition_router)
api.add_router("", assistant_router)
