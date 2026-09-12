from django.core.management.base import BaseCommand, CommandError

from accounts.seed_plans import seed_account_plans
from billing.catalog import seed_billing_offers


class Command(BaseCommand):
    help = "Create missing account plans and canonical billing offers without overwriting prices."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        plan_summary = seed_account_plans(dry_run=dry_run)
        offer_summary = seed_billing_offers(dry_run=dry_run)

        if offer_summary["missing_plans"] and not dry_run:
            raise CommandError("Billing offers could not be seeded because required account plans are missing.")

        verb = "would seed" if dry_run else "seeded"
        self.stdout.write(
            self.style.SUCCESS(
                f"Billing catalog {verb}: plans={plan_summary}; offers={offer_summary}"
            )
        )
