from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.seed_plans import seed_account_plans


class Command(BaseCommand):
    help = "Seed initial commercial account plans for the ACC plans/credits cycle."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be created/updated without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        if dry_run:
            summary = seed_account_plans(dry_run=True)
        else:
            with transaction.atomic():
                summary = seed_account_plans(dry_run=False)

        action = "would seed" if dry_run else "seeded"
        self.stdout.write(
            self.style.SUCCESS(
                "Account plans {action}: {created} created, {updated} updated, {unchanged} unchanged.".format(
                    action=action,
                    **summary,
                )
            )
        )
