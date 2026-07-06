from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import AccountSubscription
from accounts.services.subscriptions import ensure_account_subscription_for_user


class Command(BaseCommand):
    help = "Backfill AccountSubscription rows from current account/legacy plan resolution."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing rows.")
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Also realign existing subscriptions to the currently resolved account plan.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        update_existing = bool(options.get("update_existing"))
        summary = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}
        users = get_user_model().objects.all().order_by("id")

        for user in users:
            if dry_run:
                existing = AccountSubscription.objects.filter(user=user).first()
                if existing is None:
                    summary["created"] += 1
                elif update_existing:
                    summary["updated"] += 1
                else:
                    summary["unchanged"] += 1
                continue

            subscription, created, updated = ensure_account_subscription_for_user(
                user,
                source=AccountSubscription.Source.MIGRATION,
                update_existing=update_existing,
            )
            if subscription is None:
                summary["skipped"] += 1
            elif created:
                summary["created"] += 1
            elif updated:
                summary["updated"] += 1
            else:
                summary["unchanged"] += 1

        prefix = "Account subscriptions would sync" if dry_run else "Account subscriptions synced"
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}: created={summary['created']} updated={summary['updated']} "
                f"unchanged={summary['unchanged']} skipped={summary['skipped']}"
            )
        )
