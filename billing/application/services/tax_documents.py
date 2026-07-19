"""Tax-document outbox use cases without provider I/O."""

from __future__ import annotations

from django.db import transaction

from billing.models import BillingPayment, TaxDocument


class PaymentNotApproved(ValueError):
    pass


@transaction.atomic
def schedule_tax_document(
    *,
    payment: BillingPayment,
    kind: str = TaxDocument.Kind.ELECTRONIC_RECEIPT,
    request_payload: dict | None = None,
) -> tuple[TaxDocument, bool]:
    """Create the OpenFactura outbox row once; this function performs no network I/O."""

    if payment.status != BillingPayment.Status.APPROVED:
        raise PaymentNotApproved("A tax document requires an approved payment.")

    return TaxDocument.objects.get_or_create(
        payment=payment,
        defaults={
            "provider": TaxDocument.Provider.OPENFACTURA,
            "kind": kind,
            "request_payload": dict(request_payload or {}),
        },
    )
