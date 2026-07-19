import json

from django.core.management.base import BaseCommand

from notas.application.services.commands.calendarization_commands import dispatch_due_notifications


class Command(BaseCommand):
    help = "Dispatch due calendarization notifications using the configured Web Push provider."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        result = dispatch_due_notifications(limit=options["limit"])
        self.stdout.write(json.dumps(result.__dict__, sort_keys=True))
