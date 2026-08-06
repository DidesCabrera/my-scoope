import os
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from notas.application.services.mcp_user_tokens import (
    MCP_SCOPE_PROPOSALS_CREATE,
    MCP_SCOPE_READ,
)
from notas.application.services.oauth_authorization_codes import (
    OAUTH_CODE_CHALLENGE_METHOD_S256,
    create_oauth_authorization_code,
    issue_oauth_access_token_from_authorization_code,
    normalize_oauth_scopes,
)
from notas.application.services.oauth_device_sessions import (
    MOBILE_SCOPES,
    issue_mobile_tokens_from_authorization_code,
    rotate_mobile_refresh_token,
)
from notas.domain.models import OAuthClient

OAUTH_RESPONSE_TYPE_CODE = "code"
OAUTH_GRANT_TYPE_AUTHORIZATION_CODE = "authorization_code"
OAUTH_GRANT_TYPE_REFRESH_TOKEN = "refresh_token"


def _get_oauth_issuer_url(request) -> str:
    configured_issuer = os.getenv("MYSCOOPE_OAUTH_ISSUER_URL", "").strip()

    if configured_issuer:
        return configured_issuer.rstrip("/")

    return request.build_absolute_uri("/").rstrip("/")


def _oauth_error_response(
    *,
    code: str,
    message: str,
    status: int = 400,
    details: dict | None = None,
) -> JsonResponse:
    return JsonResponse(
        {
            "ok": False,
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            },
        },
        status=status,
    )


def _oauth_token_error_response(
    *,
    code: str,
    message: str,
    status: int = 400,
    details: dict | None = None,
) -> JsonResponse:
    return JsonResponse(
        {
            "error": code,
            "error_description": message,
            "details": details or {},
        },
        status=status,
    )


def _get_oauth_client(client_id: str):
    if not client_id:
        return None

    try:
        return OAuthClient.objects.get(client_id=client_id)
    except OAuthClient.DoesNotExist:
        return None


def _build_authorization_request_context(request):
    client_id = request.GET.get("client_id", "").strip()
    redirect_uri = request.GET.get("redirect_uri", "").strip()
    response_type = request.GET.get("response_type", "").strip()
    scope = request.GET.get("scope", "").strip()
    state = request.GET.get("state", "").strip()
    code_challenge = request.GET.get("code_challenge", "").strip()
    code_challenge_method = request.GET.get("code_challenge_method", "").strip()

    client = _get_oauth_client(client_id)

    requested_scopes = normalize_oauth_scopes(scope)

    return {
        "client": client,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": response_type,
        "scope": scope,
        "requested_scopes": requested_scopes,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    }


def _validate_authorization_request_context(context):
    client = context["client"]

    if client is None:
        return "oauth_client_not_found"

    if not client.is_active:
        return "oauth_client_inactive"

    if context["response_type"] != OAUTH_RESPONSE_TYPE_CODE:
        return "oauth_response_type_not_supported"

    if not context["redirect_uri"]:
        return "oauth_redirect_uri_required"

    if not client.allows_redirect_uri(context["redirect_uri"]):
        return "oauth_redirect_uri_not_allowed"

    if not context["requested_scopes"]:
        return "oauth_scope_required"

    if not client.allows_scopes(context["requested_scopes"]):
        return "oauth_scope_not_allowed"

    if not context["code_challenge"]:
        return "oauth_code_challenge_required"

    if context["code_challenge_method"] != OAUTH_CODE_CHALLENGE_METHOD_S256:
        return "oauth_code_challenge_method_not_supported"

    return None


def _oauth_error_message(error_code: str) -> str:
    messages = {
        "oauth_client_not_found": "OAuth client was not found.",
        "oauth_client_inactive": "OAuth client is inactive.",
        "oauth_response_type_not_supported": "OAuth response type is not supported.",
        "oauth_redirect_uri_required": "OAuth redirect URI is required.",
        "oauth_redirect_uri_not_allowed": "OAuth redirect URI is not allowed.",
        "oauth_scope_required": "OAuth scope is required.",
        "oauth_scope_not_allowed": "OAuth scope is not allowed.",
        "oauth_code_challenge_required": "OAuth code challenge is required.",
        "oauth_code_challenge_method_not_supported": "OAuth code challenge method is not supported.",
        "oauth_grant_type_not_supported": "OAuth grant type is not supported.",
        "oauth_client_required": "OAuth client_id is required.",
        "oauth_code_required": "OAuth authorization code is required.",
        "oauth_code_verifier_required": "OAuth code verifier is required.",
    }

    return messages.get(
        error_code,
        "OAuth request is invalid.",
    )


@require_GET
def oauth_authorization_server_metadata(request):
    issuer = _get_oauth_issuer_url(request)

    return JsonResponse(
        {
            "issuer": issuer,
            "authorization_endpoint": f"{issuer}{reverse('oauth_authorize')}",
            "token_endpoint": f"{issuer}{reverse('oauth_token')}",
            "scopes_supported": [
                MCP_SCOPE_READ,
                MCP_SCOPE_PROPOSALS_CREATE,
                *MOBILE_SCOPES,
            ],
            "response_types_supported": [
                OAUTH_RESPONSE_TYPE_CODE,
            ],
            "grant_types_supported": [
                OAUTH_GRANT_TYPE_AUTHORIZATION_CODE,
                OAUTH_GRANT_TYPE_REFRESH_TOKEN,
            ],
            "code_challenge_methods_supported": [
                OAUTH_CODE_CHALLENGE_METHOD_S256,
            ],
            "token_endpoint_auth_methods_supported": [
                "none",
            ],
        }
    )


@require_GET
@login_required
def oauth_authorize(request):
    context = _build_authorization_request_context(request)
    error_code = _validate_authorization_request_context(context)

    if error_code is not None:
        return _oauth_error_response(
            code=error_code,
            message=_oauth_error_message(error_code),
        )

    return render(
        request,
        "notas/oauth/authorize.html",
        {
            "client": context["client"],
            "client_id": context["client_id"],
            "redirect_uri": context["redirect_uri"],
            "response_type": context["response_type"],
            "scope": context["scope"],
            "requested_scopes": context["requested_scopes"],
            "state": context["state"],
            "code_challenge": context["code_challenge"],
            "code_challenge_method": context["code_challenge_method"],
        },
    )


@require_POST
@login_required
def oauth_authorize_consent(request):
    client_id = request.POST.get("client_id", "").strip()
    redirect_uri = request.POST.get("redirect_uri", "").strip()
    response_type = request.POST.get("response_type", "").strip()
    scope = request.POST.get("scope", "").strip()
    state = request.POST.get("state", "").strip()
    code_challenge = request.POST.get("code_challenge", "").strip()
    code_challenge_method = request.POST.get("code_challenge_method", "").strip()

    client = _get_oauth_client(client_id)
    requested_scopes = normalize_oauth_scopes(scope)

    context = {
        "client": client,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": response_type,
        "scope": scope,
        "requested_scopes": requested_scopes,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    }

    error_code = _validate_authorization_request_context(context)

    if error_code is not None:
        return _oauth_error_response(
            code=error_code,
            message=_oauth_error_message(error_code),
        )

    try:
        created = create_oauth_authorization_code(
            user=request.user,
            client=client,
            redirect_uri=redirect_uri,
            scopes=requested_scopes,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )
    except ValueError as exc:
        error_code = str(exc)

        return _oauth_error_response(
            code=error_code,
            message=_oauth_error_message(error_code),
        )

    redirect_params = {
        "code": created.raw_code,
    }

    if state:
        redirect_params["state"] = state

    separator = "&" if "?" in redirect_uri else "?"

    return redirect(
        f"{redirect_uri}{separator}{urlencode(redirect_params)}"
    )


@csrf_exempt
@require_POST
def oauth_token(request):
    grant_type = request.POST.get("grant_type", "").strip()
    client_id = request.POST.get("client_id", "").strip()

    if grant_type not in {OAUTH_GRANT_TYPE_AUTHORIZATION_CODE, OAUTH_GRANT_TYPE_REFRESH_TOKEN}:
        return _oauth_token_error_response(
            code="unsupported_grant_type",
            message=_oauth_error_message("oauth_grant_type_not_supported"),
        )

    if not client_id:
        return _oauth_token_error_response(
            code="invalid_request",
            message=_oauth_error_message("oauth_client_required"),
        )

    client = _get_oauth_client(client_id)

    if client is None:
        return _oauth_token_error_response(
            code="invalid_client",
            message=_oauth_error_message("oauth_client_not_found"),
            status=401,
        )

    if not client.is_active:
        return _oauth_token_error_response(
            code="invalid_client",
            message=_oauth_error_message("oauth_client_inactive"),
            status=401,
        )

    if grant_type == OAUTH_GRANT_TYPE_REFRESH_TOKEN:
        raw_refresh_token = request.POST.get("refresh_token", "").strip()
        if not raw_refresh_token:
            return _oauth_token_error_response(
                code="invalid_request",
                message="OAuth refresh token is required.",
            )
        result = rotate_mobile_refresh_token(
            raw_refresh_token=raw_refresh_token,
            client=client,
        )
        if not result.ok:
            return _oauth_token_error_response(
                code="invalid_grant",
                message=result.error.message,
                details={"code": result.error.code, **result.error.details},
            )
        return JsonResponse(result.as_token_response(), status=200)

    raw_code = request.POST.get("code", "").strip()
    redirect_uri = request.POST.get("redirect_uri", "").strip()
    code_verifier = request.POST.get("code_verifier", "").strip()

    if not raw_code:
        return _oauth_token_error_response(
            code="invalid_request",
            message=_oauth_error_message("oauth_code_required"),
        )

    if not redirect_uri:
        return _oauth_token_error_response(
            code="invalid_request",
            message=_oauth_error_message("oauth_redirect_uri_required"),
        )

    if not code_verifier:
        return _oauth_token_error_response(
            code="invalid_request",
            message=_oauth_error_message("oauth_code_verifier_required"),
        )

    is_mobile_client = any(scope in MOBILE_SCOPES for scope in client.allowed_scopes)
    if is_mobile_client:
        result = issue_mobile_tokens_from_authorization_code(
            raw_code=raw_code,
            client=client,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
            device_id=request.POST.get("device_id", "").strip(),
            device_name=request.POST.get("device_name", "").strip(),
            platform=request.POST.get("platform", "").strip(),
        )
    else:
        result = issue_oauth_access_token_from_authorization_code(
            raw_code=raw_code,
            client=client,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        )

    if not result.ok:
        return _oauth_token_error_response(
            code="invalid_grant",
            message=result.error.message,
            details={
                "code": result.error.code,
                **result.error.details,
            },
        )

    return JsonResponse(
        result.as_token_response(),
        status=200,
    )
