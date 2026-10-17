"""Low-overhead worker memory high-water logging for production requests."""

import logging
import os
import resource
import sys

logger = logging.getLogger(__name__)
MIB = 1024 * 1024
LOG_STEP_MIB = 32


def peak_rss_mib():
    """Return this process's peak resident memory in MiB."""
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux reports KiB; macOS reports bytes.
    return peak / (MIB if sys.platform == "darwin" else 1024)


class WorkerMemoryHighWaterMiddleware:
    """Log the first request and each material increase in worker peak RSS.

    Route names are static Django metadata. Never log request paths, query
    strings, bodies, or user identifiers here.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.last_logged_mib = None

    def __call__(self, request):
        try:
            return self.get_response(request)
        finally:
            peak_mib = peak_rss_mib()
            if self.last_logged_mib is None or peak_mib - self.last_logged_mib >= LOG_STEP_MIB:
                route = getattr(getattr(request, "resolver_match", None), "view_name", None)
                logger.warning(
                    "web_worker_peak_rss pid=%s peak_mib=%.1f route=%s",
                    os.getpid(),
                    peak_mib,
                    route or "unresolved",
                )
                self.last_logged_mib = peak_mib
