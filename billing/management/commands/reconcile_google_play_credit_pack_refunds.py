from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from billing.application.services.credit_packs import (
    CreditPackUnavailable,
    reconcile_google_play_voided_products,
)
from billing.infrastructure.gateways import build_google_play_gateway
from billing.infrastructure.providers.google_play import GooglePlayConfigurationError


class Command(BaseCommand):
    help = "Reconcile Google Play voided consumables; dry-run unless --apply is supplied."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--if-enabled", action="store_true")
        parser.add_argument("--days", type=int, default=29)

    def handle(self, *args, **options):
        if options["if_enabled"] and not settings.BILLING_GOOGLE_PLAY_REFUND_RECONCILIATION_ENABLED:
            self.stdout.write("Google Play refund reconciliation is disabled; skipped.")
            return
        days = options["days"]
        if not 1 <= days <= 29:
            raise CommandError("--days must be between 1 and 29 (Google retains only 30 days).")
        start = timezone.now() - timedelta(days=days)
        try:
            summary = reconcile_google_play_voided_products(
                gateway=build_google_play_gateway(),
                start_time_ms=int(start.timestamp() * 1000),
                apply=options["apply"],
            )
        except (CreditPackUnavailable, GooglePlayConfigurationError) as exc:
            raise CommandError(str(exc)) from exc
        mode = "applied" if options["apply"] else "dry-run"
        self.stdout.write(f"Google Play voided consumables ({mode}): {summary}")
