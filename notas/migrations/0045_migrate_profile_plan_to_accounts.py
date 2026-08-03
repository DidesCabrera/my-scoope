from __future__ import annotations

import re

from django.db import migrations


def _legacy_slug(legacy_plan) -> str:
    normalized = re.sub(
        r"[^a-z0-9]+",
        "-",
        str(legacy_plan.name or "plan").strip().lower(),
    ).strip("-")
    return f"legacy-{legacy_plan.pk}-{normalized}"[:60].rstrip("-")


def _legacy_entitlements(legacy_plan) -> dict:
    return {
        "nutrition_workspace": {
            "can_create_food": True,
            "can_create_meal": bool(legacy_plan.can_create_meal),
            "can_create_dailyplan": bool(legacy_plan.can_create_dailyplan),
            "can_create_program": bool(legacy_plan.can_create_program),
            "can_publish": bool(legacy_plan.can_publish),
            "can_fork": bool(legacy_plan.can_fork),
            "can_copy": bool(legacy_plan.can_copy),
            "max_program_duration_days": legacy_plan.max_program_duration_days,
            "max_active_subscriptions": legacy_plan.max_active_subscriptions,
        }
    }


def _ensure_role_plan(AccountPlan, *, role: str):
    slug = "pro" if role == "nutritionist" else "basic"
    name = "Pro" if role == "nutritionist" else "Basic"
    plan = AccountPlan.objects.filter(slug=slug).first()
    if plan is not None:
        return plan
    return AccountPlan.objects.create(
        slug=slug,
        name=name,
        status="active",
        entitlements={
            "nutrition_workspace": {
                "can_create_food": True,
                "can_create_meal": True,
                "can_create_dailyplan": True,
                "can_create_program": True,
                "can_publish": role == "nutritionist",
                "can_fork": True,
                "can_copy": role == "nutritionist",
            }
        },
        metadata={"created_by": "notas.0045_profile_plan_migration"},
    )


def migrate_profile_plans_forward(apps, schema_editor):
    Profile = apps.get_model("notas", "Profile")
    AccountPlan = apps.get_model("accounts", "AccountPlan")
    AccountSubscription = apps.get_model("accounts", "AccountSubscription")

    for profile in Profile.objects.select_related("plan").order_by("pk").iterator():
        legacy_plan = profile.plan
        if legacy_plan is not None:
            account_plan, _ = AccountPlan.objects.update_or_create(
                slug=_legacy_slug(legacy_plan),
                defaults={
                    "name": legacy_plan.name,
                    "description": "Migrated from notas.Plan before Profile.plan retirement.",
                    "status": "active",
                    "entitlements": _legacy_entitlements(legacy_plan),
                    "metadata": {
                        "migrated_from_legacy_profile_plan_id": legacy_plan.pk,
                        "legacy_role": legacy_plan.role,
                    },
                },
            )
        else:
            existing = AccountSubscription.objects.filter(user_id=profile.user_id).first()
            account_plan = existing.plan if existing is not None else _ensure_role_plan(
                AccountPlan,
                role=str(profile.role or "member"),
            )

        subscription, _ = AccountSubscription.objects.get_or_create(
            user_id=profile.user_id,
            defaults={
                "plan": account_plan,
                "status": "active",
                "source": "migration",
            },
        )
        subscription.plan = account_plan
        subscription.status = "active"
        subscription.source = "migration"
        metadata = dict(subscription.metadata or {})
        metadata.update(
            {
                "profile_plan_migration": "notas.0045",
                "legacy_profile_plan_id": legacy_plan.pk if legacy_plan is not None else None,
            }
        )
        subscription.metadata = metadata
        subscription.save(update_fields=["plan", "status", "source", "metadata", "updated_at"])


def migrate_profile_plans_reverse(apps, schema_editor):
    Profile = apps.get_model("notas", "Profile")
    AccountSubscription = apps.get_model("accounts", "AccountSubscription")
    for subscription in AccountSubscription.objects.order_by("pk").iterator():
        metadata = dict(subscription.metadata or {})
        if metadata.get("profile_plan_migration") != "notas.0045":
            continue
        legacy_plan_id = metadata.get("legacy_profile_plan_id")
        if legacy_plan_id:
            Profile.objects.filter(user_id=subscription.user_id).update(
                plan_id=legacy_plan_id
            )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_creditwallet_creditledger"),
        ("notas", "0044_profile_timezone_name_programcalendarization_and_more"),
    ]

    operations = [
        migrations.RunPython(
            migrate_profile_plans_forward,
            migrate_profile_plans_reverse,
        ),
        migrations.RemoveField(
            model_name="profile",
            name="plan",
        ),
    ]
