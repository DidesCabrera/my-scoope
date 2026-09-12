from __future__ import annotations

from dataclasses import dataclass

from billing.models import BillingOffer


@dataclass(frozen=True)
class PublicPlanPriceVM:
    monthly: str
    annual: str
    annual_monthly_equivalent: str
    currency: str
    available: bool


def build_public_plan_prices() -> dict[str, PublicPlanPriceVM]:
    """Return public prices from BillingOffer, the sole runtime price authority."""

    offers = (
        BillingOffer.objects.select_related("account_plan")
        .filter(active=True, public=True, account_plan__status="active")
        .order_by("account_plan__display_order", "display_order")
    )
    grouped: dict[str, dict[str, BillingOffer]] = {}
    for offer in offers:
        grouped.setdefault(offer.account_plan.slug, {})[offer.interval] = offer

    result: dict[str, PublicPlanPriceVM] = {}
    for plan_slug in ("basic", "pro"):
        plan_offers = grouped.get(plan_slug, {})
        monthly = plan_offers.get(BillingOffer.Interval.MONTH)
        annual = plan_offers.get(BillingOffer.Interval.YEAR)
        available = monthly is not None and annual is not None and monthly.currency == annual.currency
        result[plan_slug] = PublicPlanPriceVM(
            monthly=_money(monthly) if monthly else "No disponible",
            annual=_money(annual) if annual else "No disponible",
            annual_monthly_equivalent=_monthly_equivalent(annual) if annual else "No disponible",
            currency=monthly.currency if monthly else (annual.currency if annual else ""),
            available=available,
        )
    return result


def _money(offer: BillingOffer) -> str:
    amount = int(offer.amount_minor)
    if offer.currency == "CLP":
        return f"CLP {amount:,}".replace(",", ".")
    return f"{offer.currency} {amount / 100:.2f}"


def _monthly_equivalent(offer: BillingOffer) -> str:
    if offer.interval != BillingOffer.Interval.YEAR or offer.interval_count != 1:
        return _money(offer)
    monthly_amount = round(int(offer.amount_minor) / 12)
    if offer.currency == "CLP":
        return f"CLP {monthly_amount:,}".replace(",", ".")
    return f"{offer.currency} {monthly_amount / 100:.2f}"
