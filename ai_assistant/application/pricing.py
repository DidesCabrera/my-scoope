from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Mapping

from django.conf import settings


def estimate_cost_usd(
    *,
    provider: str,
    model: str,
    input_tokens: int | None,
    cached_input_tokens: int | None,
    output_tokens: int | None,
) -> Decimal | None:
    """Estimate provider cost from the settings-owned pricing table."""

    pricing = getattr(settings, "AI_ASSISTANT_LLM_PRICING_USD_PER_1M_TOKENS", {}) or {}
    model_pricing = _pricing_for_model(pricing, provider=provider, model=model)
    if not model_pricing:
        return None

    try:
        input_rate = Decimal(str(model_pricing.get("input", "0") or "0"))
        cached_rate = Decimal(str(model_pricing.get("cached_input", model_pricing.get("input", "0")) or "0"))
        output_rate = Decimal(str(model_pricing.get("output", "0") or "0"))
    except (InvalidOperation, ValueError):
        return None

    billable_input_tokens = max(0, int(input_tokens or 0) - int(cached_input_tokens or 0))
    cached_tokens = int(cached_input_tokens or 0)
    generated_tokens = int(output_tokens or 0)
    cost = (
        Decimal(billable_input_tokens) * input_rate
        + Decimal(cached_tokens) * cached_rate
        + Decimal(generated_tokens) * output_rate
    ) / Decimal(1_000_000)
    return cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def _pricing_for_model(
    pricing: Mapping[str, Any],
    *,
    provider: str,
    model: str,
) -> Mapping[str, Any]:
    provider_pricing = pricing.get(provider) if isinstance(pricing, Mapping) else None
    if not isinstance(provider_pricing, Mapping):
        return {}
    exact = provider_pricing.get(model)
    if isinstance(exact, Mapping):
        return exact
    default = provider_pricing.get("default")
    return default if isinstance(default, Mapping) else {}
