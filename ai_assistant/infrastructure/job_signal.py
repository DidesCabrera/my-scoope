from __future__ import annotations

from django.conf import settings

QUEUE_SIGNAL_KEY = "myscoope:ai_async_jobs:available"


def notify_job_available(job_public_id: str) -> bool:
    client = _redis_client()
    if client is None:
        return False
    try:
        client.lpush(QUEUE_SIGNAL_KEY, str(job_public_id))
        client.ltrim(QUEUE_SIGNAL_KEY, 0, 999)
        return True
    except Exception:
        return False


def wait_for_job_signal(*, timeout_seconds: int) -> bool | None:
    client = _redis_client()
    if client is None:
        return None
    try:
        return bool(client.brpop(QUEUE_SIGNAL_KEY, timeout=max(1, min(timeout_seconds, 30))))
    except Exception:
        return None


def _redis_client():
    cache_url = str(getattr(settings, "CACHE_URL", "") or "").strip()
    if not cache_url:
        return None
    try:
        import redis

        return redis.Redis.from_url(cache_url, socket_connect_timeout=1, socket_timeout=35)
    except Exception:
        return None
