from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from billing.models import BillingOffer, BillingProduct, PaymentProvider


class CatalogMappingError(ValueError):
    pass


@dataclass(frozen=True)
class PaddleCatalogReference:
    offer_code: str
    product_id: str
    price_id: str


@dataclass(frozen=True)
class AppleCatalogReference:
    offer_code: str
    product_id: str


@dataclass(frozen=True)
class GooglePlayCatalogReference:
    offer_code: str
    product_id: str
    base_plan_id: str


@transaction.atomic
def configure_paddle_catalog(
    *,
    environment: str,
    references: tuple[PaddleCatalogReference, ...],
) -> dict[str, int]:
    """Map canonical offers to one Paddle environment without rewriting history."""

    if environment not in BillingProduct.Environment.values:
        raise CatalogMappingError("Paddle environment must be sandbox or live.")
    if len({reference.offer_code for reference in references}) != len(references):
        raise CatalogMappingError("Each canonical offer must appear once in a Paddle mapping operation.")

    summary = {"created": 0, "reused": 0, "replaced": 0}
    for reference in references:
        if not reference.product_id.startswith("pro_") or not reference.price_id.startswith("pri_"):
            raise CatalogMappingError("Paddle catalog IDs must use pro_ and pri_ prefixes.")
        offer = BillingOffer.objects.select_related("account_plan").filter(code=reference.offer_code).first()
        if offer is None or not offer.active:
            raise CatalogMappingError(f"Canonical offer {reference.offer_code} is missing or inactive.")

        active = (
            BillingProduct.objects.select_for_update()
            .filter(
                provider=PaymentProvider.PADDLE,
                environment=environment,
                offer=offer,
                active=True,
            )
            .first()
        )
        snapshot = _offer_snapshot(offer)
        if active is not None and active.external_price_id == reference.price_id:
            if active.external_product_id != reference.product_id or not _snapshot_matches(active, snapshot):
                raise CatalogMappingError(
                    f"Paddle mapping {reference.price_id} conflicts with the current canonical offer; "
                    "create a new Paddle price instead of rewriting it."
                )
            summary["reused"] += 1
            continue

        historical = (
            BillingProduct.objects.select_for_update()
            .filter(
                provider=PaymentProvider.PADDLE,
                environment=environment,
                external_price_id=reference.price_id,
            )
            .first()
        )
        if historical is not None:
            if (
                historical.offer_id != offer.pk
                or historical.external_product_id != reference.product_id
                or not _snapshot_matches(historical, snapshot)
            ):
                raise CatalogMappingError(
                    f"Paddle price {reference.price_id} is already mapped to different commercial terms."
                )

        if active is not None:
            active.active = False
            active.save(update_fields=["active", "updated_at"])
            summary["replaced"] += 1

        if historical is not None:
            historical.active = True
            historical.save(update_fields=["active", "updated_at"])
            summary["reused"] += 1
        else:
            BillingProduct.objects.create(
                provider=PaymentProvider.PADDLE,
                environment=environment,
                external_product_id=reference.product_id,
                external_price_id=reference.price_id,
                offer=offer,
                account_plan=offer.account_plan,
                amount_minor=offer.amount_minor,
                currency=offer.currency,
                interval=offer.interval,
                interval_count=offer.interval_count,
                active=True,
                metadata={
                    "catalog_source": "configure_paddle_catalog",
                    "paddle_environment": environment,
                },
            )
            summary["created"] += 1
    return summary


@transaction.atomic
def configure_apple_catalog(
    *,
    environment: str,
    references: tuple[AppleCatalogReference, ...],
) -> dict[str, int]:
    """Map canonical offers to App Store Connect product identifiers."""

    if environment not in BillingProduct.Environment.values:
        raise CatalogMappingError("Apple catalog environment must be sandbox or live.")
    if len({reference.offer_code for reference in references}) != len(references):
        raise CatalogMappingError("Each canonical offer must appear once in an Apple mapping operation.")

    summary = {"created": 0, "reused": 0, "replaced": 0}
    for reference in references:
        product_id = reference.product_id.strip()
        if not product_id or len(product_id) > 160:
            raise CatalogMappingError("Apple product identifiers must contain between 1 and 160 characters.")
        offer = BillingOffer.objects.select_related("account_plan").filter(code=reference.offer_code).first()
        if offer is None or not offer.active:
            raise CatalogMappingError(f"Canonical offer {reference.offer_code} is missing or inactive.")

        active = (
            BillingProduct.objects.select_for_update()
            .filter(
                provider=PaymentProvider.APPLE_APP_STORE,
                environment=environment,
                offer=offer,
                active=True,
            )
            .first()
        )
        snapshot = _offer_snapshot(offer)
        if active is not None and active.external_product_id == product_id:
            if not _snapshot_matches(active, snapshot):
                raise CatalogMappingError(
                    f"Apple mapping {product_id} conflicts with the current canonical offer; "
                    "create a new App Store product instead of rewriting it."
                )
            summary["reused"] += 1
            continue

        historical = (
            BillingProduct.objects.select_for_update()
            .filter(
                provider=PaymentProvider.APPLE_APP_STORE,
                environment=environment,
                external_product_id=product_id,
                external_price_id="",
            )
            .first()
        )
        if historical is not None and (historical.offer_id != offer.pk or not _snapshot_matches(historical, snapshot)):
            raise CatalogMappingError(f"Apple product {product_id} is already mapped to different commercial terms.")

        if active is not None:
            active.active = False
            active.save(update_fields=["active", "updated_at"])
            summary["replaced"] += 1

        if historical is not None:
            historical.active = True
            historical.save(update_fields=["active", "updated_at"])
            summary["reused"] += 1
        else:
            BillingProduct.objects.create(
                provider=PaymentProvider.APPLE_APP_STORE,
                environment=environment,
                external_product_id=product_id,
                external_price_id="",
                offer=offer,
                account_plan=offer.account_plan,
                amount_minor=offer.amount_minor,
                currency=offer.currency,
                interval=offer.interval,
                interval_count=offer.interval_count,
                active=True,
                metadata={
                    "catalog_source": "configure_apple_catalog",
                    "apple_environment": environment,
                },
            )
            summary["created"] += 1
    return summary


@transaction.atomic
def configure_google_play_catalog(
    *, environment: str, references: tuple[GooglePlayCatalogReference, ...]
) -> dict[str, int]:
    """Map canonical offers to Google Play subscription base plans."""
    if environment not in BillingProduct.Environment.values:
        raise CatalogMappingError("Google Play catalog environment must be sandbox or live.")
    if len({reference.offer_code for reference in references}) != len(references):
        raise CatalogMappingError("Each canonical offer must appear once in a Google Play mapping operation.")
    summary = {"created": 0, "reused": 0, "replaced": 0}
    for reference in references:
        product_id = reference.product_id.strip()
        base_plan_id = reference.base_plan_id.strip()
        if not product_id or not base_plan_id:
            raise CatalogMappingError("Google Play product and base plan identifiers are required.")
        offer = (
            BillingOffer.objects.select_related("account_plan").filter(code=reference.offer_code, active=True).first()
        )
        if offer is None:
            raise CatalogMappingError(f"Canonical offer {reference.offer_code} is missing or inactive.")
        active = (
            BillingProduct.objects.select_for_update()
            .filter(provider=PaymentProvider.GOOGLE_PLAY, environment=environment, offer=offer, active=True)
            .first()
        )
        snapshot = _offer_snapshot(offer)
        if active is not None and (active.external_product_id, active.external_price_id) == (product_id, base_plan_id):
            if not _snapshot_matches(active, snapshot):
                raise CatalogMappingError("Google Play mapping conflicts with the current canonical offer.")
            summary["reused"] += 1
            continue
        historical = (
            BillingProduct.objects.select_for_update()
            .filter(
                provider=PaymentProvider.GOOGLE_PLAY,
                environment=environment,
                external_price_id=base_plan_id,
            )
            .first()
        )
        if historical is not None and (
            historical.offer_id != offer.pk
            or historical.external_product_id != product_id
            or not _snapshot_matches(historical, snapshot)
        ):
            raise CatalogMappingError("Google Play base plan is already mapped to different commercial terms.")
        if active is not None:
            active.active = False
            active.save(update_fields=["active", "updated_at"])
            summary["replaced"] += 1
        if historical is not None:
            historical.active = True
            historical.save(update_fields=["active", "updated_at"])
            summary["reused"] += 1
        else:
            BillingProduct.objects.create(
                provider=PaymentProvider.GOOGLE_PLAY,
                environment=environment,
                external_product_id=product_id,
                external_price_id=base_plan_id,
                offer=offer,
                account_plan=offer.account_plan,
                amount_minor=offer.amount_minor,
                currency=offer.currency,
                interval=offer.interval,
                interval_count=offer.interval_count,
                metadata={"catalog_source": "configure_google_play_catalog"},
            )
            summary["created"] += 1
    return summary


def _offer_snapshot(offer: BillingOffer) -> tuple[int, int, str, str, int]:
    return (
        offer.account_plan_id,
        offer.amount_minor,
        offer.currency,
        offer.interval,
        offer.interval_count,
    )


def _snapshot_matches(product: BillingProduct, snapshot: tuple[int, int, str, str, int]) -> bool:
    return (
        product.account_plan_id,
        product.amount_minor,
        product.currency,
        product.interval,
        product.interval_count,
    ) == snapshot
