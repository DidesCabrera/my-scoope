import json

from django.core.management.base import BaseCommand

from notas.application.services.commands.calendarization_commands import prune_calendarization_operational_data


class Command(BaseCommand):
    help = "Delete expired calendarization delivery logs and inactive push subscriptions."

    def add_arguments(self, parser):
        parser.add_argument("--event-days", type=int, default=90)
        parser.add_argument("--subscription-days", type=int, default=30)

    def handle(self, *args, **options):
        result = prune_calendarization_operational_data(
            event_retention_days=options["event_days"],
            inactive_subscription_days=options["subscription_days"],
        )
        self.stdout.write(json.dumps(result, sort_keys=True))
