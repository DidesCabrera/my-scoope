"""Bootstrap and validation helpers for the canonical commercial catalog."""

from __future__ import annotations

from dataclasses import dataclass

from accounts.models import AccountPlan
from billing.models import BillingOffer, CreditPackOffer


@dataclass(frozen=True)
class DefaultOffer:
    code: str
    plan_slug: str
    amount_minor: int
    currency: str
    interval: str
    display_order: int


# Bootstrap values only. Once created, BillingOffer is the runtime price authority.
# Existing offers are deliberately never overwritten by the seed operation because
# price changes require a coordinated provider-catalog migration.
DEFAULT_BILLING_OFFERS: tuple[DefaultOffer, ...] = (
    DefaultOffer("basic-monthly", "basic", 3_990, "CLP", BillingOffer.Interval.MONTH, 10),
    DefaultOffer("basic-annual", "basic", 34_990, "CLP", BillingOffer.Interval.YEAR, 20),
    DefaultOffer("pro-monthly", "pro", 6_990, "CLP", BillingOffer.Interval.MONTH, 10),
    DefaultOffer("pro-annual", "pro", 59_990, "CLP", BillingOffer.Interval.YEAR, 20),
)


@dataclass(frozen=True)
class DefaultCreditPack:
    code: str
    credits: int
    amount_minor: int
    display_order: int


DEFAULT_CREDIT_PACKS: tuple[DefaultCreditPack, ...] = (
    DefaultCreditPack("credits-500", 500, 2_990, 10),
    DefaultCreditPack("credits-1000", 1000, 5_990, 20),
    DefaultCreditPack("credits-2000", 2000, 9_990, 30),
)


def seed_credit_pack_offers(*, dry_run: bool = False) -> dict[str, int]:
    """Create missing bags; report any price/credit drift without overwriting it."""

    summary = {"created": 0, "unchanged": 0, "drifted": 0}
    for spec in DEFAULT_CREDIT_PACKS:
        offer = CreditPackOffer.objects.filter(code=spec.code).first()
        if offer is None:
            summary["created"] += 1
            if not dry_run:
                CreditPackOffer.objects.create(
                    code=spec.code, credits=spec.credits, amount_minor=spec.amount_minor,
                    currency="CLP", display_order=spec.display_order,
                )
            continue
        current = (offer.credits, offer.amount_minor, offer.currency, offer.display_order)
        expected = (spec.credits, spec.amount_minor, "CLP", spec.display_order)
        summary["unchanged" if current == expected else "drifted"] += 1
    return summary


def seed_billing_offers(*, dry_run: bool = False) -> dict[str, int]:
    """Create missing canonical offers without silently changing live prices."""

    summary = {"created": 0, "unchanged": 0, "drifted": 0, "missing_plans": 0}
    for spec in DEFAULT_BILLING_OFFERS:
        plan = AccountPlan.objects.filter(slug=spec.plan_slug).first()
        if plan is None:
            summary["missing_plans"] += 1
            continue

        offer = BillingOffer.objects.filter(code=spec.code).first()
        if offer is None:
            summary["created"] += 1
            if not dry_run:
                BillingOffer.objects.create(
                    code=spec.code,
                    account_plan=plan,
                    amount_minor=spec.amount_minor,
                    currency=spec.currency,
                    interval=spec.interval,
                    interval_count=1,
                    display_order=spec.display_order,
                    metadata={"bootstrap_source": "billing.catalog"},
                )
            continue

        expected = (
            plan.pk,
            spec.amount_minor,
            spec.currency,
            spec.interval,
            1,
            spec.display_order,
        )
        actual = (
            offer.account_plan_id,
            offer.amount_minor,
            offer.currency,
            offer.interval,
            offer.interval_count,
            offer.display_order,
        )
        summary["unchanged" if actual == expected else "drifted"] += 1
    return summary
