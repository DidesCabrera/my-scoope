import json
import tempfile
from decimal import Decimal
from pathlib import Path

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase, override_settings

from food_catalog.infrastructure.releases import (
    CatalogReleaseError,
    approve_catalog_release,
    build_authority_snapshot_envelope,
    build_catalog_release,
    import_authority_snapshot,
    import_catalog_release,
    release_envelope,
)
from food_catalog.models import (
    CatalogFood,
    CatalogFoodAlias,
    CatalogFoodPortion,
    CatalogFoodSource,
    CatalogImportBatch,
    CatalogRelease,
)

Food = apps.get_model("notas", "Food")


class CatalogReleaseTests(TestCase):
    def test_build_approve_and_export_checksummed_release(self):
        food = _published_food()
        candidate = build_catalog_release(version="2026.09.1", notes="Initial release")

        self.assertEqual(candidate.status, CatalogRelease.STATUS_CANDIDATE)
        self.assertEqual(candidate.food_count, 1)
        self.assertEqual(candidate.payload["foods"][0]["food"]["catalog_ref"], str(food.catalog_ref))

        approved = approve_catalog_release(candidate)
        envelope = release_envelope(approved)

        self.assertEqual(envelope["release"]["status"], "approved")
        self.assertEqual(envelope["release"]["payload_sha256"], approved.payload_sha256)

    @override_settings(
        ROOT_URLCONF="miapp.catalog_urls",
        FOOD_CATALOG_RELEASE_TOKEN="release-secret",
    )
    def test_release_endpoint_requires_token_and_never_exports_candidate(self):
        _published_food()
        build_catalog_release(version="candidate-only")
        client = Client()

        self.assertEqual(
            client.get("/internal/releases/candidate-only/export/").status_code,
            401,
        )
        self.assertEqual(
            client.get(
                "/internal/releases/candidate-only/export/",
                HTTP_AUTHORIZATION="Bearer release-secret",
            ).status_code,
            404,
        )

    def test_release_round_trip_and_materialization_are_idempotent(self):
        _published_food()
        authority_release = approve_catalog_release(
            build_catalog_release(version="2026.09.2")
        )
        envelope = release_envelope(authority_release)
        CatalogRelease.objects.all().delete()
        CatalogFood.objects.all().delete()

        imported = import_catalog_release(envelope)
        repeated = import_catalog_release(envelope)

        self.assertEqual(imported.created_foods, 1)
        self.assertTrue(repeated.idempotent)
        mirrored = CatalogFood.objects.get()
        self.assertTrue(mirrored.is_release_managed)
        self.assertEqual(mirrored.imported_release_version, "2026.09.2")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "release.json"
            path.write_text(json.dumps(envelope), encoding="utf-8")
            call_command(
                "import_food_catalog_release",
                file=str(path),
                materialize=True,
            )
            call_command(
                "import_food_catalog_release",
                file=str(path),
                materialize=True,
            )

        self.assertEqual(Food.objects.count(), 1)
        operational = Food.objects.get()
        self.assertTrue(operational.is_global)
        self.assertTrue(operational.solver_enabled)
        self.assertEqual(operational.catalog_snapshot_version, "v1")

    def test_authority_snapshot_preserves_unpublished_curation_state(self):
        food = _published_food()
        batch = CatalogImportBatch.objects.create(
            source_type=CatalogFood.SOURCE_NATURAL_VERIFIED,
            source_name="Initial curated seed",
            source_version="2026.09",
            status=CatalogImportBatch.STATUS_COMPLETED,
            reason="Preserve existing curation evidence",
            input_sha256="a" * 64,
            total_rows=1,
            imported_rows=1,
        )
        source = food.sources.get()
        source.import_batch = batch
        source.save(update_fields=["import_batch"])
        food.status = CatalogFood.STATUS_PENDING_REVIEW
        food.save(update_fields=["status"])
        envelope = build_authority_snapshot_envelope()
        CatalogFood.objects.all().delete()
        CatalogImportBatch.objects.all().delete()

        imported_count = import_authority_snapshot(envelope)

        self.assertEqual(imported_count, 1)
        restored = CatalogFood.objects.get()
        self.assertEqual(restored.status, CatalogFood.STATUS_PENDING_REVIEW)
        self.assertFalse(restored.is_release_managed)
        self.assertEqual(restored.sources.count(), 1)
        self.assertEqual(restored.portions.count(), 1)
        self.assertEqual(restored.aliases.count(), 1)
        restored_source = restored.sources.get()
        self.assertIsNotNone(restored_source.import_batch)
        self.assertEqual(restored_source.import_batch.source_name, "Initial curated seed")
        self.assertEqual(restored_source.import_batch.reason, batch.reason)

        with self.assertRaisesMessage(
            CatalogReleaseError,
            "catalog_authority_snapshot_requires_empty_catalog",
        ):
            import_authority_snapshot(envelope)

    def test_verified_publication_is_dry_run_by_default_and_requires_actor(self):
        food = _published_food()
        food.status = CatalogFood.STATUS_VERIFIED
        food.save(update_fields=["status"])

        call_command("publish_verified_catalog_foods")
        food.refresh_from_db()
        self.assertEqual(food.status, CatalogFood.STATUS_VERIFIED)

        with self.assertRaisesMessage(CommandError, "--actor-email is required"):
            call_command("publish_verified_catalog_foods", apply=True)

        actor = get_user_model().objects.create_user(
            username="catalog-operator",
            email="catalog-operator@myscoope.internal",
        )
        call_command(
            "publish_verified_catalog_foods",
            apply=True,
            actor_email=actor.email,
        )
        food.refresh_from_db()
        self.assertEqual(food.status, CatalogFood.STATUS_PUBLISHED)
        self.assertEqual(food.reviewed_by, actor)

    def test_new_release_refreshes_existing_operational_food_snapshot(self):
        authority_food = _published_food()
        first_release = approve_catalog_release(
            build_catalog_release(version="2026.09.3")
        )
        first_envelope = release_envelope(first_release)
        CatalogRelease.objects.all().delete()
        CatalogFood.objects.all().delete()

        import_catalog_release(first_envelope)
        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "release-v1.json"
            first_path.write_text(json.dumps(first_envelope), encoding="utf-8")
            call_command(
                "import_food_catalog_release",
                file=str(first_path),
                materialize=True,
            )

            mirrored = CatalogFood.objects.get(catalog_ref=authority_food.catalog_ref)
            operational = Food.objects.get(catalog_food_id=mirrored.pk)
            operational_id = operational.pk
            self.assertEqual(operational.protein, Decimal("31.000"))

            mirrored.catalog_version = "v2"
            mirrored.protein_g_per_100g = Decimal("32.500")
            mirrored.is_release_managed = False
            mirrored.save(
                update_fields=[
                    "catalog_version",
                    "protein_g_per_100g",
                    "is_release_managed",
                ]
            )
            CatalogRelease.objects.all().delete()
            second_release = approve_catalog_release(
                build_catalog_release(version="2026.09.4")
            )
            second_envelope = release_envelope(second_release)
            CatalogRelease.objects.all().delete()
            second_path = Path(directory) / "release-v2.json"
            second_path.write_text(json.dumps(second_envelope), encoding="utf-8")

            call_command(
                "import_food_catalog_release",
                file=str(second_path),
                materialize=True,
            )

        operational.refresh_from_db()
        self.assertEqual(operational.pk, operational_id)
        self.assertEqual(operational.protein, Decimal("32.500"))
        self.assertEqual(operational.catalog_snapshot_version, "v2")


def _published_food() -> CatalogFood:
    food = CatalogFood.objects.create(
        display_name="Pechuga de pollo cocida",
        canonical_name="pechuga pollo cocida",
        catalog_version="v1",
        food_group="meats",
        food_subgroup="poultry",
        preparation_state=CatalogFood.PREPARATION_COOKED,
        solver_enabled=True,
        solver_min_portion_g=Decimal("60"),
        solver_max_portion_g=Decimal("300"),
        solver_portion_step_g=Decimal("10"),
        protein_g_per_100g=Decimal("31.000"),
        carbs_g_per_100g=Decimal("0.000"),
        fat_g_per_100g=Decimal("3.600"),
        calories_kcal_per_100g=Decimal("165.000"),
        status=CatalogFood.STATUS_PUBLISHED,
        source_type=CatalogFood.SOURCE_NATURAL_VERIFIED,
        data_quality_score=95,
    )
    CatalogFoodPortion.objects.create(
        catalog_food=food,
        label="1 porción",
        grams=Decimal("120.000"),
        source="reviewed",
        is_default=True,
    )
    CatalogFoodAlias.objects.create(
        catalog_food=food,
        name="pollo cocido",
        normalized_name="pollo cocido",
        language="es",
        is_primary=True,
    )
    CatalogFoodSource.objects.create(
        catalog_food=food,
        source_type=CatalogFood.SOURCE_NATURAL_VERIFIED,
        source_name="Tabla oficial",
        source_food_id="pollo-cocido-release-test",
        source_version="2026",
        license_status=CatalogFoodSource.LICENSE_ALLOWED,
    )
    return food
