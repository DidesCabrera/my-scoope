from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests


class PaddleProviderError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class PaddlePortalLinks:
    overview: str
    cancel_subscription: str
    update_payment_method: str


class PaddleClient:
    def __init__(self, *, api_key: str, base_url: str, timeout_seconds: int = 10, session=None):
        if not api_key.strip():
            raise ValueError("Paddle API key is required.")
        if base_url.rstrip("/") not in {"https://sandbox-api.paddle.com", "https://api.paddle.com"}:
            raise ValueError("Paddle API URL must be an official sandbox or live endpoint.")
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def create_customer_portal_session(
        self,
        *,
        customer_id: str,
        subscription_id: str,
    ) -> PaddlePortalLinks:
        if not re.fullmatch(r"ctm_[A-Za-z0-9_]+", customer_id) or not re.fullmatch(
            r"sub_[A-Za-z0-9_]+", subscription_id
        ):
            raise PaddleProviderError("Paddle customer or subscription identity is invalid.")
        payload = self._request(
            "POST",
            f"/customers/{customer_id}/portal-sessions",
            json={"subscription_ids": [subscription_id]},
        )
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        urls = data.get("urls") if isinstance(data.get("urls"), dict) else {}
        general = urls.get("general") if isinstance(urls.get("general"), dict) else {}
        subscriptions = urls.get("subscriptions") if isinstance(urls.get("subscriptions"), list) else []
        subscription_urls = next(
            (
                item
                for item in subscriptions
                if isinstance(item, dict) and str(item.get("id") or "") == subscription_id
            ),
            {},
        )
        links = PaddlePortalLinks(
            overview=str(general.get("overview") or ""),
            cancel_subscription=str(subscription_urls.get("cancel_subscription") or ""),
            update_payment_method=str(subscription_urls.get("update_subscription_payment_method") or ""),
        )
        if not _is_paddle_portal_url(links.overview) or not _is_paddle_portal_url(links.cancel_subscription):
            raise PaddleProviderError("Paddle returned incomplete customer portal links.")
        return links

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        try:
            response = self.session.request(
                method,
                f"{self.base_url}{path}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout_seconds,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise PaddleProviderError("Paddle request failed.") from exc
        if response.status_code < 200 or response.status_code >= 300:
            raise PaddleProviderError("Paddle returned a non-success response.", status_code=response.status_code)
        try:
            payload = response.json()
        except ValueError as exc:
            raise PaddleProviderError("Paddle returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise PaddleProviderError("Paddle returned an invalid object.")
        return payload


def _is_paddle_portal_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and parsed.hostname in {
        "customer-portal.paddle.com",
        "buyer-portal.paddle.com",
    }
