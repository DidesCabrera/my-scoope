from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from billing.application.contracts import TaxDocumentGateway
from billing.models import TaxDocument


class TaxDocumentIssuanceError(RuntimeError):
    pass


def build_receipt_payload(document: TaxDocument, *, issuer: dict) -> dict:
    source = dict(document.request_payload or {})
    if source.get("currency") != "CLP" or not issuer:
        raise TaxDocumentIssuanceError("A CLP payment and approved OpenFactura issuer profile are required.")
    amount = int(source["amount_minor"])
    return {
        "response": ["FOLIO"],
        "dte": {
            "Encabezado": {
                "IdDoc": {"TipoDTE": 39, "Folio": 0, "FchEmis": timezone.localdate().isoformat(), "IndServicio": 3},
                "Emisor": dict(issuer),
                "Totales": {"MntTotal": amount},
            },
            "Detalle": [{
                "NroLinDet": 1,
                "NmbItem": f"Suscripción My Scoope · {source.get('plan_slug', 'plan')}",
                "QtyItem": 1,
                "PrcItem": amount,
                "MontoItem": amount,
            }],
        },
    }


@transaction.atomic
def issue_tax_document(*, document: TaxDocument, gateway: TaxDocumentGateway, issuer: dict) -> TaxDocument:
    document = TaxDocument.objects.select_for_update().get(pk=document.pk)
    if document.status in {TaxDocument.Status.ACCEPTED, TaxDocument.Status.ACCEPTED_WITH_OBJECTIONS}:
        return document
    now = timezone.now()
    if document.first_attempt_at and now - document.first_attempt_at > timedelta(hours=23):
        document.status = TaxDocument.Status.FAILED
        document.last_error = "Automatic retry window expired; reconcile manually before retrying."
        document.save(update_fields=["status", "last_error", "updated_at"])
        return document
    document.attempts += 1
    document.first_attempt_at = document.first_attempt_at or now
    document.last_attempt_at = now
    document.status = TaxDocument.Status.ISSUING
    document.save(update_fields=["attempts", "first_attempt_at", "last_attempt_at", "status", "updated_at"])
    try:
        result = gateway.issue_document(
            idempotency_key=str(document.idempotency_key),
            payload=build_receipt_payload(document, issuer=issuer),
        )
    except Exception as exc:
        document.status = TaxDocument.Status.FAILED
        document.last_error = str(exc)[:1000]
        document.save(update_fields=["status", "last_error", "updated_at"])
        return document
    document.status = TaxDocument.Status.ISSUED
    document.external_document_id = result.external_document_id
    document.folio = result.folio
    document.document_token = result.document_token
    document.response_metadata = dict(result.metadata or {})
    document.last_error = ""
    document.issued_at = now
    document.save()
    return document


@transaction.atomic
def reconcile_tax_document(*, document: TaxDocument, gateway: TaxDocumentGateway) -> TaxDocument:
    document = TaxDocument.objects.select_for_update().get(pk=document.pk)
    if not document.document_token:
        return document
    result = gateway.get_document_status(document.document_token)
    document.status = result.status
    metadata = dict(document.response_metadata or {})
    metadata["status_snapshot"] = dict(result.metadata or {})
    document.response_metadata = metadata
    document.save(update_fields=["status", "response_metadata", "updated_at"])
    return document
