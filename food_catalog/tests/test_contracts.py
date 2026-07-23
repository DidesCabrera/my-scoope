import ast
from decimal import Decimal
from pathlib import Path
from unittest import TestCase

from food_catalog.application.contracts import (
    CandidateSourceType,
    CatalogEvidenceItem,
    CatalogFoodCandidate,
    CatalogServingOption,
    FoodCatalogContractError,
    NutrientProfilePer100g,
    OperationalVisibility,
    PreparationState,
    PublishedFoodSnapshot,
    SourceLicenseStatus,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FOOD_CATALOG_ROOT = PROJECT_ROOT / "food_catalog"


def _python_files(root: Path) -> list[Path]:
    return [
        path
        for path in sorted(root.rglob("*.py"))
        if "__pycache__" not in path.parts
    ]


def _imports_from(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


class FoodCatalogContractTests(TestCase):
    def test_nutrient_profile_normalizes_decimal_values(self):
        nutrients = NutrientProfilePer100g(
            protein_g="31.5",
            carbs_g=0,
            fat_g="3.2",
            calories_kcal="155",
            sodium_mg="70.25",
        )

        self.assertEqual(nutrients.protein_g, Decimal("31.5"))
        self.assertEqual(nutrients.carbs_g, Decimal("0"))
        self.assertEqual(nutrients.fat_g, Decimal("3.2"))
        self.assertEqual(
            nutrients.operational_macro_defaults(),
            {
                "protein": 31.5,
                "carbs": 0.0,
                "fat": 3.2,
            },
        )
        self.assertEqual(nutrients.operational_micro_defaults()["sodium_mg_per_100g"], Decimal("70.25"))

    def test_nutrient_profile_rejects_negative_values(self):
        with self.assertRaises(FoodCatalogContractError):
            NutrientProfilePer100g(protein_g="-1", carbs_g=0, fat_g=0)

    def test_candidate_contract_tracks_license_review_status(self):
        candidate = CatalogFoodCandidate(
            candidate_ref="brand:acme:yogurt:001",
            source_type=CandidateSourceType.BRAND_SUBMITTED,
            source_name="ACME",
            source_license_status=SourceLicenseStatus.ALLOWED,
            display_name="Yogur griego natural ACME",
            nutrients_per_100g=NutrientProfilePer100g(protein_g="10", carbs_g="4", fat_g="2"),
            aliases=(" yogur griego ", ""),
            confidence_score="92.5",
        )

        self.assertTrue(candidate.can_be_published_without_license_review)
        self.assertEqual(candidate.aliases, ("yogur griego",))
        self.assertEqual(candidate.confidence_score, Decimal("92.5"))

    def test_published_snapshot_builds_operational_food_payload_without_model_imports(self):
        evidence = CatalogEvidenceItem(
            source_type=CandidateSourceType.NATURAL_VERIFIED,
            source_name="Tabla oficial",
            source_food_id="food-1",
            source_version="2026",
            license_name="Allowed internal use",
        )
        serving_option = CatalogServingOption(
            label="1 porción",
            grams="120",
            source="reviewed",
            is_default=True,
        )
        snapshot = PublishedFoodSnapshot(
            catalog_ref="catalog-food:chicken-breast-cooked",
            catalog_version="v1",
            display_name="Pechuga de pollo cocida",
            canonical_name="pechuga pollo cocida",
            food_group="meats",
            food_subgroup="poultry",
            nutrients_per_100g=NutrientProfilePer100g(
                protein_g="31",
                carbs_g="0",
                fat_g="3.6",
                fiber_g="0",
            ),
            data_quality_score=95,
            visibility=OperationalVisibility.CORE,
            preparation_state=PreparationState.COOKED,
            solver_enabled=True,
            default_portion_g="120",
            serving_options=(serving_option,),
            aliases=("pollo cocido",),
            evidence=(evidence,),
        )

        payload = snapshot.to_operational_snapshot_payload()

        self.assertEqual(payload.source_catalog_ref, "catalog-food:chicken-breast-cooked")
        self.assertEqual(
            payload.food_defaults(),
            {
                "name": "Pechuga de pollo cocida",
                "protein": 31.0,
                "carbs": 0.0,
                "fat": 3.6,
                "canonical_name": "pechuga pollo cocida",
                "is_verified": True,
                "is_active": True,
                "food_group": "meats",
                "food_subgroup": "poultry",
                "preparation_state": "cooked",
                "solver_enabled": True,
                "fiber_g_per_100g": Decimal("0"),
                "sugar_g_per_100g": None,
                "saturated_fat_g_per_100g": None,
                "sodium_mg_per_100g": None,
                "default_portion_g": Decimal("120"),
                "min_portion_g": None,
                "max_portion_g": None,
                "portion_step_g": None,
                "data_quality_score": 95,
                "visibility": "core",
                "solver_capabilities_version": "solver_food_capabilities.v1",
                "solver_capabilities": {},
            },
        )
        self.assertEqual(
            payload.snapshot_metadata()["serving_options"],
            (
                {
                    "label": "1 porción",
                    "grams": Decimal("120"),
                    "source": "reviewed",
                    "is_default": True,
                },
            ),
        )
        self.assertEqual(payload.snapshot_metadata()["aliases"], ("pollo cocido",))
        self.assertEqual(payload.snapshot_metadata()["preparation_state"], "cooked")
        self.assertTrue(payload.snapshot_metadata()["solver_enabled"])
        self.assertEqual(payload.snapshot_metadata()["solver_capabilities"], {})

    def test_contract_modules_do_not_import_operational_apps_or_mcp(self):
        forbidden_prefixes = ("notas", "mcp_server", "django")
        offenders: list[str] = []

        for path in _python_files(FOOD_CATALOG_ROOT / "application"):
            for imported in sorted(_imports_from(path)):
                if any(
                    imported == prefix or imported.startswith(f"{prefix}.")
                    for prefix in forbidden_prefixes
                ):
                    offenders.append(f"{path.relative_to(PROJECT_ROOT)} imports {imported}")

        self.assertEqual(offenders, [])
