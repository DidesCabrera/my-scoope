from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from billing.application.services.google_play import GooglePlayEvidenceError, sync_google_play_subscription
from billing.infrastructure.gateways import build_google_play_gateway
from billing.infrastructure.providers.google_play import GooglePlayConfigurationError, InvalidGooglePlayPurchase
from billing.models import PaymentProvider, ProviderSubscription


class Command(BaseCommand):
    help = "Recheck stored Google Play subscriptions; dry-run unless --apply is supplied."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--if-enabled", action="store_true")
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        if options["if_enabled"] and not settings.BILLING_GOOGLE_PLAY_SUBSCRIPTION_RECONCILIATION_ENABLED:
            self.stdout.write("Google Play subscription reconciliation is disabled; skipped.")
            return
        limit = options["limit"]
        if not 1 <= limit <= 1000:
            raise CommandError("--limit must be between 1 and 1000.")

        subscriptions = list(
            ProviderSubscription.objects.filter(provider=PaymentProvider.GOOGLE_PLAY)
            .exclude(status=ProviderSubscription.Status.EXPIRED)
            .select_related("user")
            .order_by("updated_at", "pk")[:limit]
        )
        if not subscriptions:
            self.stdout.write("Google Play subscriptions: checked=0 changed=0 errors=0.")
            return

        gateway = build_google_play_gateway()
        changed = 0
        errors = 0
        for subscription in subscriptions:
            try:
                evidence = gateway.verify_subscription(subscription.external_subscription_id)
                if evidence.purchase_token != subscription.external_subscription_id:
                    raise GooglePlayEvidenceError("Google Play returned a different purchase token.")
                if options["apply"]:
                    before = (subscription.status, subscription.current_period_end, subscription.cancel_at_period_end)
                    refreshed = sync_google_play_subscription(evidence, expected_user=subscription.user)
                    after = (refreshed.status, refreshed.current_period_end, refreshed.cancel_at_period_end)
                    changed += before != after
                else:
                    changed += 1
            except (GooglePlayConfigurationError, InvalidGooglePlayPurchase, GooglePlayEvidenceError) as exc:
                errors += 1
                self.stderr.write(f"Google Play subscription row {subscription.pk}: {exc}")

        mode = "applied" if options["apply"] else "dry-run; would recheck"
        self.stdout.write(
            f"Google Play subscriptions ({mode}): checked={len(subscriptions)} changed={changed} errors={errors}."
        )
        if errors:
            raise CommandError(f"Google Play subscription reconciliation had {errors} error(s).")
