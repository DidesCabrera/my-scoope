"""Narrow token introspection boundary for the standalone MCP server."""

import logging
from hashlib import sha256
from time import time

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from notas.application.services.mcp_user_tokens import (
    MCP_USER_TOKEN_PREFIX,
    validate_mcp_user_token,
)
from notas.interface.api.auth import extract_bearer_token

logger = logging.getLogger("myscoope.mcp")


def _auth_rate_limited(request) -> bool:
    maximum = settings.MCP_AUTH_MAX_PER_IP_PER_MINUTE
    if maximum < 1:
        return True
    address = request.META.get("REMOTE_ADDR", "unknown")
    fingerprint = sha256(address.encode("utf-8")).hexdigest()
    key = f"mcp:auth:{fingerprint}:{int(time()) // 60}"
    if cache.add(key, 1, timeout=61):
        return False
    try:
        return cache.incr(key) > maximum
    except ValueError:
        return True


def _no_store_response(payload: dict, status: int) -> JsonResponse:
    response = JsonResponse(payload, status=status)
    response["Cache-Control"] = "no-store"
    return response


@csrf_exempt
@require_POST
def mcp_token_introspection(request):
    """Return only verified scopes/audience; never accept sessions or legacy keys."""
    if _auth_rate_limited(request):
        response = _no_store_response({"active": False}, 429)
        response["Retry-After"] = "60"
        return response

    resource = getattr(settings, "MCP_RESOURCE_URL", "")
    if not resource:
        return _no_store_response({"active": False}, 503)

    raw_token = extract_bearer_token(request)
    if not raw_token.startswith(MCP_USER_TOKEN_PREFIX):
        return _no_store_response({"active": False}, 401)

    result = validate_mcp_user_token(raw_token, required_resource=resource)
    if not result.ok:
        logger.warning("mcp_auth_rejected reason=%s", result.error.code)
        return _no_store_response({"active": False}, 401)

    token = result.token
    if token.expires_at is None:
        return _no_store_response({"active": False}, 401)

    logger.info("mcp_auth_verified user_id=%s", token.user_id)

    return _no_store_response(
        {
            "active": True,
            "scopes": token.scopes,
            "resource": token.resource,
            "expires_at": int(token.expires_at.timestamp()),
        },
        200,
    )
