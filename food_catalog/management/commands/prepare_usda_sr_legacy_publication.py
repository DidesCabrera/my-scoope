from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from food_catalog.infrastructure.usda_portion_publication import (
    prepare_usda_sr_legacy_publication,
)


class Command(BaseCommand):
    help = (
        "Add versioned USDA SR Legacy portions and move the complete valid pending "
        "wave to verified. Publishing remains a separate protected command."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--actor-email", default="")
        parser.add_argument("--reason", default="")

    def handle(self, *args, **options):
        actor = None
        if options["apply"]:
            email = str(options["actor_email"] or "").strip()
            if not email:
                raise CommandError("--actor-email is required with --apply.")
            actor = get_user_model().objects.filter(email__iexact=email).first()
            if actor is None:
                raise CommandError("Actor email does not match an authority user.")
        try:
            result = prepare_usda_sr_legacy_publication(
                apply=options["apply"],
                actor=actor,
                reason=options["reason"],
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        mode = "Applied" if options["apply"] else "Dry run valid"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode}: foods={result.foods} official={result.official_foods} "
                f"fallbacks={result.fallback_foods} portions={result.portion_rows} "
                f"changed={result.changed_foods}."
            )
        )
