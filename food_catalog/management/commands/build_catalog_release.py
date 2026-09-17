from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from food_catalog.infrastructure.releases import (
    CatalogReleaseError,
    build_catalog_release,
)


class Command(BaseCommand):
    help = "Build an immutable candidate release from published CatalogFood rows."

    def add_arguments(self, parser):
        parser.add_argument("--release-version", required=True)
        parser.add_argument("--notes", default="")
        parser.add_argument("--actor-email", default="")
        parser.add_argument("--previous-version", default="")

    def handle(self, *args, **options):
        actor = _actor_by_email(options["actor_email"])
        try:
            release = build_catalog_release(
                version=options["release_version"],
                actor=actor,
                notes=options["notes"],
                previous_version=options["previous_version"],
            )
        except CatalogReleaseError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Candidate release {release.version}: foods={release.food_count} "
                f"sha256={release.payload_sha256}"
            )
        )


def _actor_by_email(email: str):
    normalized = str(email or "").strip()
    if not normalized:
        return None
    actor = get_user_model().objects.filter(email__iexact=normalized).first()
    if actor is None:
        raise CommandError("Actor email does not match an authority user.")
    return actor
