import logging
from functools import wraps
from hashlib import sha256
from time import time

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from notas.application.services.mcp_user_tokens import MCP_SCOPE_PROPOSALS_CREATE
from notas.interface.api.auth import (
    get_authorization_header,
    resolve_internal_api_user,
)
from notas.interface.api.responses import (
    internal_api_auth_error_response,
    invalid_json_response,
    method_not_allowed_response,
    parse_json_body,
)

logger = logging.getLogger("myscoope.mcp")


def _mcp_limit_response(code: str, message: str, status: int, retry_after: int | None = None):
    response = JsonResponse(
        {"ok": False, "data": {}, "error": {"code": code, "message": message, "details": {}}},
        status=status,
    )
    if retry_after is not None:
        response["Retry-After"] = str(retry_after)
    return response


def _mcp_token_rate_limited(request) -> bool:
    token_fingerprint = sha256(get_authorization_header(request).encode("utf-8")).hexdigest()
    now = int(time())
    for period, maximum in (
        (60, settings.MCP_CREATE_MAX_PER_MINUTE),
        (86_400, settings.MCP_CREATE_MAX_PER_DAY),
    ):
        if maximum < 1:
            return True
        key = f"mcp:create:{token_fingerprint}:{period}:{now // period}"
        if cache.add(key, 1, timeout=period + 1):
            count = 1
        else:
            try:
                count = cache.incr(key)
            except ValueError:
                return True
        if count > maximum:
            return True
    return False


def _has_internal_api_auth_header(request) -> bool:
    authorization = get_authorization_header(request)

    return bool(authorization)


def _authenticate_internal_api_request(
    request,
    *,
    required_scopes=None,
) -> bool:
    result = resolve_internal_api_user(
        request,
        required_scopes=required_scopes,
    )

    if not result.ok:
        request.ai_tool_internal_auth_error = result.error
        return False

    request.user = result.user
    request.ai_tool_internal_auth_error = None
    request.ai_tool_auth_source = result.auth_source or "internal_api"

    return True


def _parse_json_payload(request):
    try:
        parsed_body = parse_json_body(request)
    except ValueError as exc:
        error_code = str(exc)

        if error_code == "invalid_json":
            return None, invalid_json_response()

        if error_code == "json_body_must_be_object":
            return None, JsonResponse(
                {
                    "ok": False,
                    "data": {},
                    "error": {
                        "code": "json_body_must_be_object",
                        "message": "Request body must be a JSON object.",
                        "details": {},
                    },
                },
                status=400,
            )

        raise

    if isinstance(parsed_body, JsonResponse):
        return None, parsed_body

    return parsed_body, None


def ai_tool_api_view(
    view_func=None,
    *,
    required_scopes=None,
):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if request.method != "POST":
                return method_not_allowed_response()

            if request.user.is_authenticated:
                request.ai_tool_auth_source = "session"
            elif _has_internal_api_auth_header(request):
                if not _authenticate_internal_api_request(
                    request,
                    required_scopes=required_scopes,
                ):
                    return internal_api_auth_error_response(
                        request.ai_tool_internal_auth_error,
                    )
            else:
                return login_required(func)(request, *args, **kwargs)

            if request.ai_tool_auth_source == "mcp_user_token":
                max_bytes = settings.MCP_MAX_REQUEST_BYTES
                if max_bytes < 1 or len(request.body) > max_bytes:
                    return _mcp_limit_response(
                        "mcp_request_too_large", "MCP request is too large.", 413,
                    )
                if MCP_SCOPE_PROPOSALS_CREATE in (required_scopes or ()) and _mcp_token_rate_limited(request):
                    logger.warning("mcp_tool_rate_limited user_id=%s path=%s", request.user.pk, request.path)
                    return _mcp_limit_response(
                        "mcp_create_rate_limited", "MCP creation limit exceeded.", 429, 60,
                    )

            parsed_body, error_response = _parse_json_payload(request)

            if error_response is not None:
                return error_response

            request.ai_tool_payload = parsed_body

            response = func(request, *args, **kwargs)
            if request.ai_tool_auth_source == "mcp_user_token":
                logger.info(
                    "mcp_tool_call user_id=%s path=%s status=%s",
                    request.user.pk, request.path, response.status_code,
                )
            return response

        return csrf_exempt(wrapper)

    if view_func is None:
        return decorator

    return decorator(view_func)
