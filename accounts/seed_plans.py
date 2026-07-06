from __future__ import annotations

from copy import deepcopy
from typing import Any

from .models import AccountPlan

ACCOUNT_PLAN_SEED_VERSION = "ACC04.2026-07-04"

ACCOUNT_PLAN_SEEDS: tuple[dict[str, Any], ...] = (
    {
        "slug": "free",
        "name": "Free",
        "description": "Plan de entrada para probar My Scoope con créditos y límites comerciales básicos.",
        "status": AccountPlan.Status.ACTIVE,
        "display_order": 10,
        "included_monthly_credits": 25,
        "daily_credit_limit": 5,
        "monthly_credit_limit": 25,
        "entitlements": {
            "ai_assistant": {
                "enabled": True,
                "monthly_credit_limit": 25,
                "daily_credit_limit": 5,
                "block_on_exhaustion": True,
            },
            "nutrition_workspace": {
                "can_create_meal": True,
                "can_create_dailyplan": True,
                "can_create_program": False,
                "can_publish": False,
                "can_copy": False,
                "can_fork": True,
            },
        },
    },
    {
        "slug": "basic",
        "name": "Basic",
        "description": "Plan base para usuarios que gestionan su propia planificación nutricional con mayor capacidad de IA.",
        "status": AccountPlan.Status.ACTIVE,
        "display_order": 20,
        "included_monthly_credits": 150,
        "daily_credit_limit": 30,
        "monthly_credit_limit": 150,
        "entitlements": {
            "ai_assistant": {
                "enabled": True,
                "monthly_credit_limit": 150,
                "daily_credit_limit": 30,
                "block_on_exhaustion": True,
            },
            "nutrition_workspace": {
                "can_create_meal": True,
                "can_create_dailyplan": True,
                "can_create_program": True,
                "can_publish": False,
                "can_copy": True,
                "can_fork": True,
            },
        },
    },
    {
        "slug": "pro",
        "name": "Pro",
        "description": "Plan avanzado para usuarios intensivos y profesionales que necesitan más créditos y capacidades comerciales.",
        "status": AccountPlan.Status.ACTIVE,
        "display_order": 30,
        "included_monthly_credits": 1000,
        "daily_credit_limit": 150,
        "monthly_credit_limit": 1000,
        "entitlements": {
            "ai_assistant": {
                "enabled": True,
                "monthly_credit_limit": 1000,
                "daily_credit_limit": 150,
                "block_on_exhaustion": True,
            },
            "nutrition_workspace": {
                "can_create_meal": True,
                "can_create_dailyplan": True,
                "can_create_program": True,
                "can_publish": True,
                "can_copy": True,
                "can_fork": True,
                "max_active_subscriptions": None,
            },
        },
    },
)


def iter_account_plan_seed_payloads() -> tuple[dict[str, Any], ...]:
    """Return a defensive copy of seed payloads for commands/tests."""

    return tuple(deepcopy(seed) for seed in ACCOUNT_PLAN_SEEDS)


def seed_account_plans(*, dry_run: bool = False) -> dict[str, int]:
    """Create or update the initial commercial account plans.

    The operation is idempotent: slugs are stable and can be re-seeded without
    duplicating rows. Existing rows are updated to the canonical seed payload so
    commercial defaults remain easy to correct while the ACC cycle evolves.
    """

    summary = {"created": 0, "updated": 0, "unchanged": 0}
    for payload in iter_account_plan_seed_payloads():
        slug = payload.pop("slug")
        metadata = dict(payload.get("metadata") or {})
        metadata.setdefault("seed_version", ACCOUNT_PLAN_SEED_VERSION)
        metadata.setdefault("seed_source", "accounts.seed_plans")
        payload["metadata"] = metadata

        plan = AccountPlan.objects.filter(slug=slug).first()
        if plan is None:
            summary["created"] += 1
            if not dry_run:
                AccountPlan.objects.create(slug=slug, **payload)
            continue

        changed = False
        for field, value in payload.items():
            if getattr(plan, field) != value:
                changed = True
                if not dry_run:
                    setattr(plan, field, value)
        if changed:
            summary["updated"] += 1
            if not dry_run:
                plan.save(update_fields=[*payload.keys(), "updated_at"])
        else:
            summary["unchanged"] += 1
    return summary
