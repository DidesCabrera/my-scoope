from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from food_catalog.infrastructure.releases import (
    CatalogReleaseError,
    approve_catalog_release,
)
from food_catalog.models import CatalogRelease


class Command(BaseCommand):
    help = "Approve one checksummed candidate Food Catalog release."

    def add_arguments(self, parser):
        parser.add_argument("--release-version", required=True)
        parser.add_argument("--actor-email", default="")

    def handle(self, *args, **options):
        release = CatalogRelease.objects.filter(
            version=options["release_version"]
        ).first()
        if release is None:
            raise CommandError("Catalog release does not exist.")
        actor = _actor_by_email(options["actor_email"])
        try:
            release = approve_catalog_release(release, actor=actor)
        except CatalogReleaseError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Approved release {release.version}: sha256={release.payload_sha256}"
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
