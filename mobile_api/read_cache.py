from __future__ import annotations

import json
from hashlib import sha256

from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder

HOME_CACHE_SECONDS = 30


def home_cache_key(user_id: int) -> str:
    return f"mobile-api:home:v1:user:{user_id}"


def read_generation_key(user_id: int) -> str:
    return f"mobile-api:read-generation:v1:user:{user_id}"


def mobile_read_generation(user_id: int) -> int:
    return int(cache.get(read_generation_key(user_id), 0))


def get_cached_home(user_id: int):
    return cache.get(home_cache_key(user_id))


def cache_home(user_id: int, payload: dict, *, generation: int) -> None:
    if mobile_read_generation(user_id) == generation:
        cache.set(home_cache_key(user_id), payload, timeout=HOME_CACHE_SECONDS)


def invalidate_mobile_read_cache(user_id: int) -> None:
    cache.delete(home_cache_key(user_id))
    generation_key = read_generation_key(user_id)
    if not cache.add(generation_key, 1, timeout=None):
        try:
            cache.incr(generation_key)
        except ValueError:
            cache.set(generation_key, 1, timeout=None)


def payload_etag(content: bytes) -> str:
    return f'W/"{sha256(content).hexdigest()}"'


def payload_version(payload: dict) -> str:
    serialized = json.dumps(payload, cls=DjangoJSONEncoder, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode("utf-8")).hexdigest()[:16]
