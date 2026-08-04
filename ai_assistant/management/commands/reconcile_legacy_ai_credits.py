from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from accounts.services.credits import current_account_credit_period
from ai_assistant.application.credit_reconciliation import ai_credit_reconciliation_summary


class Command(BaseCommand):
    help = (
        "Compare account-owned AI credit movements with usage events. Legacy parity is "
        "reported for pre-cutover audits but is informational by default."
    )

    def add_arguments(self, parser):
        parser.add_argument("--period", default=current_account_credit_period())
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument("--fail-on-difference", action="store_true")
        parser.add_argument(
            "--require-legacy-parity",
            action="store_true",
            help="Also fail when frozen legacy rows differ; use only for a pre-cutover audit.",
        )

    def handle(self, *args, **options):
        period = str(options["period"] or "").strip()
        if len(period) != 7 or period[4:5] != "-":
            raise CommandError("--period must use YYYY-MM format.")
        summary = ai_credit_reconciliation_summary(period=period)
        if options["as_json"]:
            self.stdout.write(json.dumps(summary, sort_keys=True))
        else:
            self.stdout.write(
                f"AI credit reconciliation {period}: users={summary['users']} "
                f"account_event_mismatches={summary['account_event_mismatches']} "
                f"legacy_account_mismatches={summary['legacy_account_mismatches']}"
            )
            for row in summary["rows"]:
                if not row["reconciled"] or not row["legacy_matches_account"]:
                    self.stdout.write(
                        "user={user_id} legacy_quota={legacy_quota_used} "
                        "legacy_ledger={legacy_ledger_used} account={account_ledger_used} "
                        "events={usage_event_charged}".format(**row)
                    )
        account_mismatch = bool(summary["account_event_mismatches"])
        legacy_mismatch = bool(summary["legacy_account_mismatches"])
        should_fail = options["fail_on_difference"] and account_mismatch
        should_fail = should_fail or (options["require_legacy_parity"] and legacy_mismatch)
        if should_fail:
            raise CommandError("AI credit reconciliation found required differences.")
