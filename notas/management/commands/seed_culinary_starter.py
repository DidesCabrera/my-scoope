import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from notas.application.culinary_starter import seed_starter_library


class Command(BaseCommand):
    help = "Create a private rule-validated culinary starter library, without claiming human review."

    def add_arguments(self, parser):
        parser.add_argument("--user-id", type=int, required=True)

    def handle(self, *args, **options):
        user = get_user_model().objects.get(pk=options["user_id"])
        self.stdout.write(json.dumps(seed_starter_library(user=user), ensure_ascii=False))
