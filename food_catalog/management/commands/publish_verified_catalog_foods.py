from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from food_catalog.application.curation import transition_catalog_foods_status
from food_catalog.application.publication import check_catalog_food_publishable
from food_catalog.models import CatalogFood


class Command(BaseCommand):
    help = (
        "Validate every verified CatalogFood and, only with --apply, publish the "
        "complete valid batch using the protected curation workflow."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--actor-email", default="")

    def handle(self, *args, **options):
        foods = tuple(
            CatalogFood.objects.filter(status=CatalogFood.STATUS_VERIFIED).order_by(
                "catalog_ref",
                "id",
            )
        )
        if not foods:
            self.stdout.write(self.style.WARNING("No verified foods are pending publication."))
            return

        blocked = []
        for food in foods:
            result = check_catalog_food_publishable(food)
            if not result.can_publish:
                blocked.append(f"{food.display_name}: {', '.join(result.errors)}")
        if blocked:
            raise CommandError(
                "Publication batch blocked; no foods changed:\n- " + "\n- ".join(blocked)
            )

        if not options["apply"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry run valid: {len(foods)} verified foods can be published. "
                    "Run again with --apply --actor-email <email>."
                )
            )
            return

        actor_email = str(options["actor_email"] or "").strip()
        if not actor_email:
            raise CommandError("--actor-email is required with --apply.")
        actor = get_user_model().objects.filter(email__iexact=actor_email).first()
        if actor is None:
            raise CommandError("Actor email does not match an authority user.")

        with transaction.atomic():
            result = transition_catalog_foods_status(
                foods,
                CatalogFood.STATUS_PUBLISHED,
                user=actor,
            )
            if result.blocked:
                raise CommandError(
                    "Publication batch blocked; transaction rolled back:\n- "
                    + "\n- ".join(result.blocked)
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Published {result.changed_count} foods; actor={actor_email}."
            )
        )
