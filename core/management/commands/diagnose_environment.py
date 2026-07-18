import json

from django.core.management.base import BaseCommand

from core.environment_diagnostics import build_environment_diagnostic


class Command(BaseCommand):
    help = "Report sanitized My Scoope environment readiness without network calls."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument("--skip-database", action="store_true")

    def handle(self, *args, **options):
        report = build_environment_diagnostic(include_database=not options["skip_database"])
        if options["as_json"]:
            self.stdout.write(json.dumps(report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
            return

        self.stdout.write(f"My Scoope environment: {report.environment} ({report.status})")
        self.stdout.write(f"Settings: {report.settings_module}")
        for finding in report.findings:
            self.stdout.write(f"[{finding.status.upper()}] {finding.code}: {finding.summary}")
            if finding.action:
                self.stdout.write(f"  Action: {finding.action}")
        self.stdout.write(
            f"Configuration contract: {len(report.configuration_summary)} classified variables; values are not displayed."
        )

