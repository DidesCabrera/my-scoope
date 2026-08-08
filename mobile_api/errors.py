from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MobileAPIError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: dict = field(default_factory=dict)


def error_envelope(error: MobileAPIError) -> dict:
    return {
        "ok": False,
        "data": {},
        "error": {
            "code": error.code,
            "message": error.message,
            "details": error.details,
        },
    }
