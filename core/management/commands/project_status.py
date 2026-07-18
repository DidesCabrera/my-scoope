import json

from django.core.management.base import BaseCommand

from core.project_status import build_project_status


class Command(BaseCommand):
    help = "Report sanitized executable project status for humans and AI clients."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument("--skip-database", action="store_true")

    def handle(self, *args, **options):
        report = build_project_status(include_database=not options["skip_database"])
        if options["as_json"]:
            self.stdout.write(json.dumps(report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
            return

        self.stdout.write(f"My Scoope project status: {report.status}")
        self.stdout.write(
            f"Environment: {report.environment['name']} · release: {report.release['commit']}"
        )
        self.stdout.write(
            f"Runtime: Python {report.runtime['python']} · Django {report.runtime['django']}"
        )
        for probe in report.probes:
            self.stdout.write(f"[{probe.status.upper()}] {probe.code}")
            for key, value in probe.data.items():
                self.stdout.write(f"  {key}: {value}")
            if probe.message:
                self.stdout.write(f"  {probe.message}")
        attention = report.environment.get("attention", [])
        self.stdout.write(f"Environment attention items: {len(attention)}")

