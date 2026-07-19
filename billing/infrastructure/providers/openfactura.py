from __future__ import annotations

from typing import Any, Mapping

import requests

from billing.application.contracts import TaxDocumentIssueResult, TaxDocumentStatusResult


class OpenFacturaProviderError(RuntimeError):
    pass


class OpenFacturaClient:
    def __init__(self, *, api_key: str, base_url: str, timeout_seconds: int = 10, session=None):
        if not api_key:
            raise ValueError("OpenFactura API key is required.")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def issue_document(self, *, idempotency_key: str, payload: Mapping[str, Any]) -> TaxDocumentIssueResult:
        data = self._request(
            "POST",
            "/v2/dte/document",
            json=dict(payload),
            headers={"Idempotency-Key": idempotency_key},
        )
        token = str(data.get("token") or data.get("TOKEN") or "")
        external_id = str(data.get("id") or data.get("documentId") or token)
        if not token and not external_id:
            raise OpenFacturaProviderError("OpenFactura returned no document identity.")
        return TaxDocumentIssueResult(
            external_document_id=external_id,
            folio=str(data.get("folio") or data.get("FOLIO") or ""),
            document_token=token,
            status="issued",
            metadata=data,
        )

    def get_document_status(self, document_token: str) -> TaxDocumentStatusResult:
        data = self._request("GET", f"/v2/dte/document/{document_token}/status")
        raw_status = str(data.get("status") or data.get("estado") or "").strip().lower()
        normalized = {
            "aceptado": "accepted",
            "pendiente": "issued",
            "rechazado": "rejected",
            "aceptado con reparo": "accepted_with_objections",
        }.get(raw_status, "issued")
        return TaxDocumentStatusResult(status=normalized, metadata=data)

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        headers = {"apikey": self.api_key, "Accept": "application/json"}
        headers.update(kwargs.pop("headers", {}))
        try:
            response = self.session.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                timeout=self.timeout_seconds,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise OpenFacturaProviderError("OpenFactura request failed.") from exc
        if response.status_code < 200 or response.status_code >= 300:
            raise OpenFacturaProviderError(f"OpenFactura returned HTTP {response.status_code}.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise OpenFacturaProviderError("OpenFactura returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise OpenFacturaProviderError("OpenFactura returned an invalid payload.")
        return payload
