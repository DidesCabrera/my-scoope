from django.core.management.base import BaseCommand, CommandError

from billing.application.services.apple_app_store import sync_apple_transaction
from billing.infrastructure.gateways import build_apple_app_store_gateway
from billing.infrastructure.providers.apple_app_store import AppleAppStoreConfigurationError
from billing.models import PaymentProvider, ProviderSubscription


class Command(BaseCommand):
    help = "Reconcile stored Apple subscriptions with App Store Server API evidence."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        subscriptions = list(
            ProviderSubscription.objects.filter(provider=PaymentProvider.APPLE_APP_STORE)
            .order_by("updated_at")[: options["limit"]]
        )
        active_rows = ProviderSubscription.objects.filter(status=ProviderSubscription.Status.AUTHORIZED).values(
            "user_id", "provider"
        )
        provider_sets: dict[int, set[str]] = {}
        for item in active_rows:
            provider_sets.setdefault(item["user_id"], set()).add(item["provider"])
        duplicates = sum(1 for providers in provider_sets.values() if len(providers) > 1)
        if options["dry_run"]:
            self.stdout.write(f"apple_subscriptions={len(subscriptions)} duplicate_active_accounts={duplicates}")
            return
        try:
            gateway = build_apple_app_store_gateway()
            reconciled = 0
            for subscription in subscriptions:
                for item in gateway.get_subscription_statuses(subscription.external_subscription_id):
                    if item.transaction.original_transaction_id != subscription.external_subscription_id:
                        continue
                    sync_apple_transaction(item.transaction, source="app_store_server_api")
                    reconciled += 1
        except AppleAppStoreConfigurationError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"apple_subscriptions={len(subscriptions)} reconciled={reconciled} "
                f"duplicate_active_accounts={duplicates}"
            )
        )
