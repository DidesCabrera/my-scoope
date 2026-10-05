from __future__ import annotations

import logging
import re
from time import perf_counter

from django.http import HttpResponseNotModified

from mobile_api.read_cache import invalidate_mobile_read_cache, payload_etag

logger = logging.getLogger(__name__)


def _route_label(path: str) -> str:
    return re.sub(
        r"/(?:\d+|[0-9a-f]{8}-[0-9a-f-]{27,}|[A-Za-z0-9_-]{20,})(?=/|$)",
        "/:id",
        path,
        flags=re.IGNORECASE,
    )


class MobileAPIResponseMiddleware:
    """Attach private validation metadata and invalidate user projections after writes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started_at = perf_counter()
        response = self.get_response(request)
        if not request.path.startswith("/api/v1/"):
            return response

        duration_ms = (perf_counter() - started_at) * 1000
        response["Server-Timing"] = f"app;dur={duration_ms:.1f}"

        user = getattr(request, "user", None)
        if request.method not in {"GET", "HEAD", "OPTIONS"} and response.status_code < 400:
            if getattr(user, "is_authenticated", False):
                invalidate_mobile_read_cache(user.id)

        content_type = response.get("Content-Type", "").lower()
        if request.method == "GET" and response.status_code == 200 and "application/json" in content_type:
            etag = payload_etag(response.content)
            if request.headers.get("If-None-Match") == etag:
                not_modified = HttpResponseNotModified()
                not_modified["ETag"] = etag
                not_modified["Cache-Control"] = "private, no-cache"
                not_modified["Server-Timing"] = response["Server-Timing"]
                return not_modified
            response["ETag"] = etag
            response["Cache-Control"] = "private, no-cache"

        if duration_ms >= 500:
            logger.warning(
                "Slow mobile API response",
                extra={
                    "duration_ms": round(duration_ms, 1),
                    "method": request.method,
                    "path": _route_label(request.path),
                    "status_code": response.status_code,
                },
            )
        return response
