import os
from dataclasses import dataclass

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/app"


@dataclass(frozen=True)
class MCPServerConfig:
    api_base_url: str
    auth_token: str | None = None
    request_timeout_seconds: float = 20.0

    @property
    def normalized_api_base_url(self) -> str:
        return self.api_base_url.rstrip("/")


def load_config_from_env() -> MCPServerConfig:
    return MCPServerConfig(
        api_base_url=os.getenv(
            "MYSCOOPE_API_BASE_URL",
            DEFAULT_API_BASE_URL,
        ),
        auth_token=os.getenv("MYSCOOPE_API_AUTH_TOKEN") or None,
        request_timeout_seconds=float(
            os.getenv(
                "MYSCOOPE_API_TIMEOUT_SECONDS",
                "20",
            )
        ),
    )