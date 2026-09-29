"""Explicit, audited launch entitlement alignment; never a billing cancellation."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import AccountPlan, AccountSubscription
from billing.models import ProviderSubscription


class Command(BaseCommand):
    help = "Preview/apply environment-specific launch entitlements."

    def add_arguments(self, parser):
        parser.add_argument("--scope", choices=("local", "staging", "production"), required=True)
        parser.add_argument("--apply", action="store_true", help="Apply only after reviewing dry-run and provider billing.")

    def handle(self, *args, **options):
        scope = options["scope"]
        service_name = str(getattr(settings, "SENTRY_ENVIRONMENT", "") or "").lower()
        if scope == "local" and not settings.DEBUG:
            raise CommandError("Local scope requires DEBUG settings.")
        if scope == "staging" and (settings.DEBUG or "staging" not in service_name):
            raise CommandError("Staging scope requires a staging Render environment.")
        if scope == "production" and (settings.DEBUG or service_name != "my-scoope"):
            raise CommandError("Production scope requires the my-scoope Render service.")
        user_model = get_user_model()
        owner = None
        if scope == "production":
            owners = user_model.objects.filter(username__iexact="bacardides")
            if owners.count() != 1:
                raise CommandError("Expected exactly one bacardides account; no changes made.")
            owner = owners.get()
        plans = {plan.slug: plan for plan in AccountPlan.objects.filter(slug__in=("free", "pro"))}
        if set(plans) != {"free", "pro"}:
            raise CommandError("Active Free and Pro account plans must be seeded first.")
        if any(plan.status != AccountPlan.Status.ACTIVE for plan in plans.values()):
            raise CommandError("Free and Pro plans must be active; no changes made.")
        active_billing = ProviderSubscription.objects.filter(
            status__in=(ProviderSubscription.Status.AUTHORIZED, ProviderSubscription.Status.PAST_DUE, ProviderSubscription.Status.PAUSED)
        )
        if scope == "production" and active_billing.exclude(user=owner).exists():
            raise CommandError(
                "Provider subscriptions still have authorized/past-due billing. "
                "Reconcile or cancel those agreements before changing entitlements."
            )
        changes = []
        for user in user_model.objects.all().order_by("pk"):
            target = plans["pro" if scope != "production" or user.pk == owner.pk else "free"]
            current = AccountSubscription.objects.select_related("plan").filter(user=user).first()
            if current is None or current.plan_id != target.pk or current.status != AccountSubscription.Status.ACTIVE:
                changes.append((user, current, target))
        self.stdout.write(
            f"Launch plan reconciliation: scope={scope} users={user_model.objects.count()} "
            f"changes={len(changes)} mode={'apply' if options['apply'] else 'dry-run'}"
        )
        if not options["apply"]:
            return
        with transaction.atomic():
            for user, current, target in changes:
                metadata = dict(current.metadata or {}) if current else {}
                history = list(metadata.get("launch_plan_transitions") or [])
                history.append({
                    "at": timezone.now().isoformat(),
                    "from": current.plan.slug if current else None,
                    "to": target.slug,
                    "reason": f"2026_launch_account_rule_{scope}",
                })
                metadata["launch_plan_transitions"] = history
                if scope == "production" and user.pk == owner.pk:
                    metadata["commercial_cadence"] = "annual"
                if current is None:
                    AccountSubscription.objects.create(
                        user=user, plan=target, status=AccountSubscription.Status.ACTIVE,
                        source=AccountSubscription.Source.MIGRATION, metadata=metadata,
                    )
                else:
                    current.plan = target
                    current.status = AccountSubscription.Status.ACTIVE
                    current.source = AccountSubscription.Source.MIGRATION
                    current.metadata = metadata
                    current.save(update_fields=["plan", "status", "source", "metadata", "updated_at"])
