from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

import jwt
import requests

from billing.application.contracts import GooglePlayProductEvidence, GooglePlaySubscriptionEvidence


class GooglePlayConfigurationError(RuntimeError):
    pass


class InvalidGooglePlayPurchase(ValueError):
    pass


class GooglePlayClient:
    def __init__(self, *, package_name: str, service_account: dict[str, Any], timeout_seconds: int = 10):
        self.package_name = package_name
        self.service_account = service_account
        self.timeout_seconds = timeout_seconds

    def verify_subscription(self, purchase_token: str) -> GooglePlaySubscriptionEvidence:
        if not self.package_name or not self.service_account:
            raise GooglePlayConfigurationError("Google Play verification is not configured.")
        token = purchase_token.strip()
        if not token:
            raise InvalidGooglePlayPurchase("A Google Play purchase token is required.")
        url = (
            "https://androidpublisher.googleapis.com/androidpublisher/v3/applications/"
            f"{quote(self.package_name, safe='')}/purchases/subscriptionsv2/tokens/{quote(token, safe='')}"
        )
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {self._access_token()}"},
            timeout=self.timeout_seconds,
        )
        if response.status_code in {400, 404}:
            raise InvalidGooglePlayPurchase("Google Play did not recognize the subscription purchase.")
        if response.status_code >= 400:
            raise GooglePlayConfigurationError(f"Google Play verification failed with HTTP {response.status_code}.")
        data = response.json()
        line_items = data.get("lineItems") or []
        if not line_items:
            raise InvalidGooglePlayPurchase("Google Play returned no subscription line item.")
        current = max(line_items, key=lambda item: str(item.get("expiryTime") or ""))
        offer = current.get("offerDetails") or {}
        identifiers = data.get("externalAccountIdentifiers") or {}
        state = str(data.get("subscriptionState") or "")
        return GooglePlaySubscriptionEvidence(
            purchase_token=token,
            product_id=str(current.get("productId") or ""),
            base_plan_id=str(offer.get("basePlanId") or ""),
            status=state,
            environment="sandbox" if data.get("testPurchase") is not None else "live",
            start_time=data.get("startTime"),
            expiry_time=current.get("expiryTime"),
            obfuscated_account_id=str(identifiers.get("obfuscatedAccountId") or ""),
            acknowledged=str(data.get("acknowledgementState") or "").endswith("ACKNOWLEDGED"),
            auto_renewing=bool((current.get("autoRenewingPlan") or {}).get("autoRenewEnabled")),
            metadata=data,
        )

    def verify_product(self, purchase_token: str) -> GooglePlayProductEvidence:
        if not self.package_name or not self.service_account:
            raise GooglePlayConfigurationError("Google Play verification is not configured.")
        token = purchase_token.strip()
        if not token:
            raise InvalidGooglePlayPurchase("A Google Play purchase token is required.")
        url = (
            "https://androidpublisher.googleapis.com/androidpublisher/v3/applications/"
            f"{quote(self.package_name, safe='')}/purchases/productsv2/tokens/{quote(token, safe='')}"
        )
        response = requests.get(
            url, headers={"Authorization": f"Bearer {self._access_token()}"}, timeout=self.timeout_seconds
        )
        if response.status_code in {400, 404}:
            raise InvalidGooglePlayPurchase("Google Play did not recognize the product purchase.")
        if response.status_code >= 400:
            raise GooglePlayConfigurationError(f"Google Play verification failed with HTTP {response.status_code}.")
        data = response.json()
        items = data.get("productLineItem") or []
        if len(items) != 1 or not isinstance(items[0], dict):
            raise InvalidGooglePlayPurchase("A credit purchase must contain one product line item.")
        state = str((data.get("purchaseStateContext") or {}).get("purchaseState") or "")
        return GooglePlayProductEvidence(
            purchase_token=token,
            product_id=str(items[0].get("productId") or ""),
            status="PURCHASED" if state == "PURCHASED" else state,
            obfuscated_account_id=str(data.get("obfuscatedExternalAccountId") or ""),
            order_id=str(data.get("orderId") or ""),
            environment="sandbox" if data.get("testPurchaseContext") is not None else "live",
            metadata=data,
        )

    def list_voided_products(self, *, start_time_ms: int) -> list[dict[str, Any]]:
        """Read every page of revoked one-time purchases from Google's server API.

        Google exposes at most 30 days here. Callers must poll more often than
        that and treat a failed/incomplete scan as a reconciliation failure.
        """
        if not self.package_name or not self.service_account:
            raise GooglePlayConfigurationError("Google Play verification is not configured.")
        url = (
            "https://androidpublisher.googleapis.com/androidpublisher/v3/applications/"
            f"{quote(self.package_name, safe='')}/purchases/voidedpurchases"
        )
        params: dict[str, Any] = {
            "startTime": str(start_time_ms),
            "type": 0,  # In-app products only; subscription tokens are not unique per renewal.
            "includeQuantityBasedPartialRefund": "false",
            "pageSelection.maxResults": 1000,
        }
        headers = {"Authorization": f"Bearer {self._access_token()}"}
        purchases: list[dict[str, Any]] = []
        seen_pages: set[str] = set()
        while True:
            response = requests.get(url, headers=headers, params=params, timeout=self.timeout_seconds)
            if response.status_code >= 400:
                raise GooglePlayConfigurationError(
                    f"Google Play voided purchases query failed with HTTP {response.status_code}."
                )
            data = response.json()
            page = data.get("voidedPurchases") or []
            if not isinstance(page, list):
                raise GooglePlayConfigurationError("Google Play returned an invalid voided purchases page.")
            purchases.extend(item for item in page if isinstance(item, dict))
            next_page = str((data.get("tokenPagination") or {}).get("nextPageToken") or "")
            if not next_page:
                return purchases
            if next_page in seen_pages:
                raise GooglePlayConfigurationError("Google Play repeated a voided purchases page token.")
            seen_pages.add(next_page)
            params = {"pageSelection.token": next_page}

    def _access_token(self) -> str:
        client_email = str(self.service_account.get("client_email") or "")
        private_key = str(self.service_account.get("private_key") or "")
        token_uri = str(self.service_account.get("token_uri") or "https://oauth2.googleapis.com/token")
        if not client_email or not private_key:
            raise GooglePlayConfigurationError("Google Play service account credentials are incomplete.")
        now = int(time.time())
        assertion = jwt.encode(
            {
                "iss": client_email,
                "scope": "https://www.googleapis.com/auth/androidpublisher",
                "aud": token_uri,
                "iat": now,
                "exp": now + 3600,
            },
            private_key,
            algorithm="RS256",
        )
        response = requests.post(
            token_uri,
            data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion},
            timeout=self.timeout_seconds,
        )
        if response.status_code >= 400:
            raise GooglePlayConfigurationError("Google Play service account authorization failed.")
        access_token = str(response.json().get("access_token") or "")
        if not access_token:
            raise GooglePlayConfigurationError("Google Play returned no access token.")
        return access_token
