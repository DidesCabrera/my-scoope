from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from billing.models import AppleSandboxAccess, BillingProduct, PaymentProvider, ProviderCreditPack

SUBSCRIPTION_PRODUCTS = {
    "basic-monthly": "com.myscoope.basic.monthly",
    "basic-annual": "com.myscoope.basic.annual",
    "pro-monthly": "com.myscoope.pro.monthly",
    "pro-annual": "com.myscoope.pro.annual",
}
PACK_PRODUCTS = {
    "credits-500": "com.myscoope.credits.500",
    "credits-1000": "com.myscoope.credits.1000",
    "credits-2000": "com.myscoope.credits.2000",
}


class Command(BaseCommand):
    help = "Check Apple production/TestFlight configuration without changing billing state."

    def add_arguments(self, parser):
        parser.add_argument(
            "--scenario",
            choices=("production", "testflight", "all"),
            default="all",
        )
        parser.add_argument("--require-enabled", action="store_true")
        parser.add_argument("--require-reconciliation", action="store_true")

    def handle(self, *args, **options):
        scenario = options["scenario"]
        issues = _configuration_issues()

        for environment in _scenario_environments(scenario):
            catalog_issues, summary = _catalog_readiness(environment)
            issues.extend(catalog_issues)
            self.stdout.write(summary)

        sandbox_access_count = AppleSandboxAccess.objects.filter(active=True).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        ).count()
        self.stdout.write(f"active_sandbox_accounts={sandbox_access_count}")
        if scenario in {"testflight", "all"} and sandbox_access_count == 0:
            issues.append("no active, unexpired AppleSandboxAccess account exists")

        if options["require_enabled"]:
            issues.extend(_enabled_issues(scenario))

        reconciliation_ready = all(
            (
                settings.BILLING_APPLE_IN_APP_PURCHASE_KEY,
                settings.BILLING_APPLE_KEY_ID,
                settings.BILLING_APPLE_ISSUER_ID,
            )
        )
        self.stdout.write(
            f"reconciliation_credentials={'ready' if reconciliation_ready else 'missing'}"
        )
        if options["require_reconciliation"] and not reconciliation_ready:
            issues.append("App Store Server API reconciliation credentials are incomplete")

        if issues:
            raise CommandError("Apple billing is not ready: " + "; ".join(issues))
        self.stdout.write(self.style.SUCCESS(f"Apple billing readiness passed for {scenario}."))


def _configuration_issues() -> list[str]:
    issues = []
    if settings.BILLING_APPLE_ENVIRONMENT != "production":
        issues.append("BILLING_APPLE_ENVIRONMENT must be production")
    if settings.BILLING_APPLE_BUNDLE_ID != "com.myscoope.app":
        issues.append("BILLING_APPLE_BUNDLE_ID must match com.myscoope.app")
    if not settings.BILLING_APPLE_APP_ID:
        issues.append("BILLING_APPLE_APP_ID is missing")
    return issues


def _scenario_environments(scenario: str) -> tuple[str, ...]:
    if scenario == "production":
        return (BillingProduct.Environment.LIVE,)
    if scenario == "testflight":
        return (BillingProduct.Environment.SANDBOX,)
    return (BillingProduct.Environment.LIVE, BillingProduct.Environment.SANDBOX)


def _catalog_readiness(environment: str) -> tuple[list[str], str]:
    actual_subscriptions = dict(
        BillingProduct.objects.filter(
            provider=PaymentProvider.APPLE_APP_STORE,
            environment=environment,
            active=True,
        ).values_list("offer__code", "external_product_id")
    )
    actual_packs = dict(
        ProviderCreditPack.objects.filter(
            provider=PaymentProvider.APPLE_APP_STORE,
            environment=environment,
            active=True,
        ).values_list("offer__code", "external_product_id")
    )
    issues = [
        *_catalog_issues(
            environment=environment,
            expected=SUBSCRIPTION_PRODUCTS,
            actual=actual_subscriptions,
            label="subscriptions",
        ),
        *_catalog_issues(
            environment=environment,
            expected=PACK_PRODUCTS,
            actual=actual_packs,
            label="credit packs",
        ),
    ]
    matched_subscriptions = sum(
        actual_subscriptions.get(code) == product_id
        for code, product_id in SUBSCRIPTION_PRODUCTS.items()
    )
    matched_packs = sum(actual_packs.get(code) == product_id for code, product_id in PACK_PRODUCTS.items())
    summary = (
        f"{environment}_catalog=subscriptions:{matched_subscriptions}/4 "
        f"credit_packs:{matched_packs}/3"
    )
    return issues, summary


def _enabled_issues(scenario: str) -> list[str]:
    issues = []
    if scenario in {"production", "all"}:
        if not settings.BILLING_APPLE_PURCHASES_ENABLED:
            issues.append("BILLING_APPLE_PURCHASES_ENABLED is false")
        if not settings.BILLING_APPLE_NOTIFICATIONS_ENABLED:
            issues.append("BILLING_APPLE_NOTIFICATIONS_ENABLED is false")
    if scenario in {"testflight", "all"}:
        if not settings.BILLING_APPLE_SANDBOX_PURCHASES_ENABLED:
            issues.append("BILLING_APPLE_SANDBOX_PURCHASES_ENABLED is false")
        if not settings.BILLING_APPLE_SANDBOX_NOTIFICATIONS_ENABLED:
            issues.append("BILLING_APPLE_SANDBOX_NOTIFICATIONS_ENABLED is false")
    return issues


def _catalog_issues(*, environment: str, expected: dict[str, str], actual: dict[str | None, str], label: str):
    issues = []
    for offer_code, product_id in expected.items():
        if actual.get(offer_code) != product_id:
            issues.append(f"{environment} {label} mapping is missing or invalid for {offer_code}")
    unexpected = sorted(str(code) for code in actual if code not in expected)
    if unexpected:
        issues.append(f"{environment} {label} has unexpected active offers: {', '.join(unexpected)}")
    return issues
