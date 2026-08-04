from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

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

            parsed_body, error_response = _parse_json_payload(request)

            if error_response is not None:
                return error_response

            request.ai_tool_payload = parsed_body

            return func(request, *args, **kwargs)

        return csrf_exempt(wrapper)

    if view_func is None:
        return decorator

    return decorator(view_func)