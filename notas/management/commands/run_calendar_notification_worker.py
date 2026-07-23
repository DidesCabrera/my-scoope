import json
import time

from django.core.management.base import BaseCommand

from notas.application.services.commands.calendarization_commands import dispatch_due_notifications


class Command(BaseCommand):
    help = "Run the calendar notification dispatcher continuously for a background worker service."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=int, default=300)
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        interval = max(30, options["interval"])
        while True:
            result = dispatch_due_notifications(limit=options["limit"])
            self.stdout.write(json.dumps(result.__dict__, sort_keys=True))
            if options["once"]:
                return
            time.sleep(interval)
