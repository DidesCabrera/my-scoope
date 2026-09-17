from __future__ import annotations

import json
import os
from pathlib import Path

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from food_catalog.infrastructure.releases import (
    CatalogReleaseError,
    import_catalog_release,
    validate_release_envelope,
)
from food_catalog.models import CatalogFood
from notas.application.services.food_catalog_snapshots import (
    create_operational_food_snapshot_from_catalog,
    mark_operational_food_catalog_snapshot_stale,
    refresh_operational_food_snapshot_from_catalog,
)
from notas.domain.models import Food


class Command(BaseCommand):
    help = (
        "Import one approved Food Catalog authority release and optionally materialize "
        "its published foods as global notas.Food snapshots."
    )

    def add_arguments(self, parser):
        source = parser.add_mutually_exclusive_group(required=False)
        source.add_argument("--url", default="")
        source.add_argument("--file", default="")
        parser.add_argument("--release-version", default="latest")
        parser.add_argument("--token", default="")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--materialize", action="store_true")

    def handle(self, *args, **options):
        try:
            envelope = _load_envelope(options)
            metadata, payload = validate_release_envelope(envelope)
        except (CatalogReleaseError, OSError, ValueError, requests.RequestException) as exc:
            raise CommandError(str(exc)) from exc

        if options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Release valid: version={metadata['version']} "
                    f"foods={len(payload['foods'])} sha256={metadata['payload_sha256']}"
                )
            )
            return

        try:
            with transaction.atomic():
                result = import_catalog_release(envelope)
                materialization = (
                    _materialize_release(version=result.release.version)
                    if options["materialize"]
                    else {"created": 0, "refreshed": 0, "stale": 0}
                )
        except CatalogReleaseError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Imported release "
                f"{result.release.version}: created={result.created_foods} "
                f"updated={result.updated_foods} deprecated={result.deprecated_foods} "
                f"idempotent={result.idempotent}; operational_created="
                f"{materialization['created']} operational_refreshed="
                f"{materialization['refreshed']} operational_stale="
                f"{materialization['stale']}"
            )
        )


def _load_envelope(options: dict) -> dict:
    file_path = str(options.get("file") or "").strip()
    if file_path:
        return json.loads(Path(file_path).read_text(encoding="utf-8"))

    version = str(options.get("release_version") or "latest").strip()
    url = str(options.get("url") or "").strip()
    if not url:
        base_url = os.environ.get("FOOD_CATALOG_RELEASE_URL", "").strip().rstrip("/")
        if not base_url:
            raise ValueError("Provide --url/--file or configure FOOD_CATALOG_RELEASE_URL.")
        url = f"{base_url}/internal/releases/{version}/export/"

    token = str(options.get("token") or "").strip() or os.environ.get(
        "FOOD_CATALOG_RELEASE_TOKEN",
        "",
    ).strip()
    if not token:
        raise ValueError("FOOD_CATALOG_RELEASE_TOKEN is required for remote delivery.")
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
    value = response.json()
    if not isinstance(value, dict):
        raise ValueError("Food Catalog release response must be a JSON object.")
    return value


def _materialize_release(*, version: str) -> dict[str, int]:
    created = 0
    refreshed = 0
    stale = 0
    published_foods = CatalogFood.objects.filter(
        is_release_managed=True,
        imported_release_version=version,
        status=CatalogFood.STATUS_PUBLISHED,
    ).order_by("id")
    for catalog_food in published_foods:
        operational = Food.objects.filter(catalog_food_id=catalog_food.pk).order_by("id").first()
        if operational is None:
            create_operational_food_snapshot_from_catalog(
                catalog_food,
                created_by=None,
                is_global=True,
            )
            created += 1
            continue
        if (
            operational.catalog_snapshot_version != catalog_food.catalog_version
            or operational.catalog_sync_status != Food.CATALOG_SYNC_SNAPSHOT
        ):
            refresh_operational_food_snapshot_from_catalog(
                operational,
                catalog_food=catalog_food,
            )
            refreshed += 1

    deprecated_ids = CatalogFood.objects.filter(
        is_release_managed=True,
        imported_release_version=version,
        status=CatalogFood.STATUS_DEPRECATED,
    ).values_list("id", flat=True)
    for operational in Food.objects.filter(catalog_food_id__in=deprecated_ids, is_active=True):
        mark_operational_food_catalog_snapshot_stale(operational)
        stale += 1
    return {"created": created, "refreshed": refreshed, "stale": stale}
