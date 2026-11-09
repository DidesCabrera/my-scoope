"""One bounded, repeatable staging pilot for the Chilean completo italiano."""

from decimal import Decimal
from uuid import UUID

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from food_catalog.application.curation import transition_catalog_food_status
from food_catalog.infrastructure.preparations import publish_preparation_version
from food_catalog.models import (
    CatalogFood,
    CatalogFoodPortion,
    CatalogFoodSource,
    CatalogPreparation,
    CatalogPreparationIngredient,
    CatalogPreparationVersion,
)

# Stable identities make a retry safe after a deployment or interrupted command.
PILOT_REF = UUID("2d0bb5e6-94c4-56a6-a08b-2f51079194f7")
REVIEWER_USERNAME = "catalog-completo-pilot"
FOODS = (
    {
        "ref": UUID("1dc16288-9ce7-5869-8c63-3952c74b5d11"),
        "name": "Pan de completo",
        "canonical": "pan de completo",
        "brand": "",
        "protein": "9.430", "carbs": "49.200", "fat": "3.590", "sodium": "450.000", "calories": "267.000",
        "allergens": ["gluten", "wheat"], "portion": "45.000", "portion_label": "1 pan de completo mediano",
        "source_type": CatalogFood.SOURCE_USDA, "source_name": "USDA FoodData Central, FNDDS 2021-2023",
        "source_id": "2707656", "source_url": "https://fdc.nal.usda.gov/food-details/2707656/nutrients",
        "license": "CC0 / public domain",
        "note": "Roll, white, hot dog bun. Nutrient proxy for a Chilean pan de completo; wheat/gluten is a food-identity assessment, not a brand label.",
    },
    {
        "ref": UUID("516a956a-c9b6-51b1-8de4-b2dcc5e35ff6"),
        "name": "Vienesa tradicional PF",
        "canonical": "vienesa tradicional pf",
        "brand": "PF", "protein": "13.800", "carbs": "2.400", "fat": "16.000", "sodium": "972.000", "calories": "209.000",
        "allergens": ["soy"], "portion": "50.000", "portion_label": "1 vienesa",
        "source_type": CatalogFood.SOURCE_ADMIN_IMPORT, "source_name": "PF Alimentos, Salchichas Tradicional 250 g",
        "source_id": "7801930000916", "source_url": "https://tiendapfalimentos.cl/salchichas-tradicional-pf-24x250gr.html",
        "license": "Manufacturer label facts; provenance retained",
        "note": "Per 100 g label; 50 g serving. Contains soy; made on lines also processing milk and egg. Use cooked per manufacturer instructions; label values are the available packaged-food proxy.",
    },
    {
        "ref": UUID("3a5de672-2e68-5265-a26b-20a9afbf38b5"),
        "name": "Mayonesa regular",
        "canonical": "mayonesa regular",
        "brand": "", "protein": "0.960", "carbs": "0.570", "fat": "74.800", "sodium": "635.000", "calories": "680.000",
        "allergens": ["egg"], "portion": "14.000", "portion_label": "1 cucharada",
        "source_type": CatalogFood.SOURCE_USDA, "source_name": "USDA FoodData Central, FNDDS 2021-2023",
        "source_id": "2710204", "source_url": "https://fdc.nal.usda.gov/food-details/2710204/nutrients",
        "license": "CC0 / public domain",
        "note": "Mayonnaise, regular; FNDDS generic nutrient proxy. Egg is part of standard mayonnaise; verify the particular Chilean brand before production.",
    },
)


class Command(BaseCommand):
    help = "Validate or apply the bounded completo italiano catalog pilot (central authority only)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        if settings.ROOT_URLCONF != "miapp.catalog_urls":
            raise CommandError("Only the central Food Catalog authority may run this pilot.")
        self._validate_existing()
        if not options["apply"]:
            self.stdout.write("Pilot valid: 3 new foods, 2 allergen reviews (Palta, Tomate), 1 preparation; no changes made.")
            return
        with transaction.atomic():
            reviewer = _reviewer()
            foods = [_create_food(item, reviewer) for item in FOODS]
            palta = _review_natural_allergens("Palta")
            tomate = _review_natural_allergens("Tomate")
            preparation, created = CatalogPreparation.objects.get_or_create(
                catalog_ref=PILOT_REF, defaults={"display_name": "Completo italiano"}
            )
            if created:
                version = CatalogPreparationVersion.objects.create(
                    preparation=preparation, version=1, yield_g=Decimal("179"),
                    default_portion_g=Decimal("179"), household_label="completo mediano",
                    source_name="My Scoope, piloto curado con USDA FNDDS y PF Alimentos",
                    yield_evidence=(
                        "Estimación editorial de masa comestible ensamblada: pan 45 g + vienesa 50 g "
                        "+ palta 40 g + tomate 30 g + mayonesa 14 g = 179 g. "
                        "No es un peso medido; no se aplicó merma por calentamiento."
                    ),
                    preparation_notes=(
                        "Piloto de staging; referencias nutricionales no equivalen a una marca chilena específica. "
                        "La vienesa PF declara soya y contacto cruzado posible con leche y huevo. "
                        "Revisar pesos y etiquetas antes de producción."
                    ),
                )
                for order, (food, grams, state, condiment) in enumerate((
                    (foods[0], "45", CatalogFood.PREPARATION_READY_TO_EAT, False),
                    (foods[1], "50", CatalogFood.PREPARATION_COOKED, False),
                    (palta, "40", CatalogFood.PREPARATION_READY_TO_EAT, False),
                    (tomate, "30", CatalogFood.PREPARATION_READY_TO_EAT, False),
                    (foods[2], "14", CatalogFood.PREPARATION_READY_TO_EAT, True),
                )):
                    CatalogPreparationIngredient.objects.create(
                        version=version, food=food, quantity_g=Decimal(grams),
                        preparation_state=state, is_condiment=condiment, order=order,
                    )
                publish_preparation_version(version, actor=reviewer)
        self.stdout.write(self.style.SUCCESS(
            f"Completo italiano pilot ready: preparation_ref={PILOT_REF}; "
            "3 foods published, 5 ingredients, 179 g; no release built."
        ))

    def _validate_existing(self):
        for name in ("Palta", "Tomate"):
            matches = CatalogFood.objects.filter(display_name=name, country="CL", status=CatalogFood.STATUS_PUBLISHED)
            if matches.count() != 1:
                raise CommandError(f"Expected exactly one published CL food named {name}.")
            if matches.get().allergens not in ([], ["none"]):
                raise CommandError(f"{name} has allergen data requiring manual review.")
        for item in FOODS:
            if CatalogFood.objects.filter(catalog_ref=item["ref"]).exclude(display_name=item["name"]).exists():
                raise CommandError(f"Pilot identity collision: {item['name']}.")
            if CatalogFood.objects.filter(canonical_name=item["canonical"], brand_name=item["brand"], country="CL").exclude(catalog_ref=item["ref"]).exists():
                raise CommandError(f"Existing food needs manual deduplication: {item['name']}.")
        existing = CatalogPreparation.objects.filter(catalog_ref=PILOT_REF).first()
        if existing and (existing.display_name != "Completo italiano" or not existing.current_version):
            raise CommandError("Existing pilot preparation requires manual review.")


def _reviewer():
    user, created = get_user_model().objects.get_or_create(
        username=REVIEWER_USERNAME,
        defaults={"email": "", "is_staff": True, "is_active": False},
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    if not user.is_staff or user.is_active:
        raise CommandError("Pilot reviewer identity is not a disabled staff account.")
    return user


def _create_food(item, reviewer):
    food, created = CatalogFood.objects.get_or_create(
        catalog_ref=item["ref"],
        defaults={
            "display_name": item["name"], "canonical_name": item["canonical"],
            "brand_name": item["brand"], "is_branded": bool(item["brand"]),
            "country": "CL", "language": "es",
            "preparation_state": (CatalogFood.PREPARATION_COOKED if item["brand"] else CatalogFood.PREPARATION_READY_TO_EAT),
            "food_form": (CatalogFood.FOOD_FORM_CONDIMENT if item["name"] == "Mayonesa regular" else CatalogFood.FOOD_FORM_INGREDIENT),
            "protein_g_per_100g": Decimal(item["protein"]),
            "carbs_g_per_100g": Decimal(item["carbs"]),
            "fat_g_per_100g": Decimal(item["fat"]),
            "sodium_mg_per_100g": Decimal(item["sodium"]),
            "calories_kcal_per_100g": Decimal(item["calories"]),
            "allergens": item["allergens"], "source_type": item["source_type"],
            "data_quality_score": 80, "status": CatalogFood.STATUS_VERIFIED,
            "solver_enabled": False,
        },
    )
    if not created:
        if food.status != CatalogFood.STATUS_PUBLISHED or food.display_name != item["name"]:
            raise CommandError(f"Existing pilot food requires manual review: {item['name']}.")
        return food
    CatalogFoodSource.objects.create(
        catalog_food=food, source_type=item["source_type"], source_name=item["source_name"],
        source_food_id=item["source_id"], source_url=item["source_url"],
        license_name=item["license"], license_status=CatalogFoodSource.LICENSE_ALLOWED,
        evidence_payload={"curation_note": item["note"], "pilot_only": True},
    )
    CatalogFoodPortion.objects.create(
        catalog_food=food, label=item["portion_label"], grams=Decimal(item["portion"]),
        household_amount=Decimal("1"), household_measure="unit", is_default=True,
        source=item["source_name"][:80],
    )
    result = transition_catalog_food_status(food, CatalogFood.STATUS_PUBLISHED, user=reviewer)
    if result.errors:
        raise CommandError(f"Cannot publish {item['name']}: {', '.join(result.errors)}")
    return food


def _review_natural_allergens(name):
    food = CatalogFood.objects.get(display_name=name, country="CL", status=CatalogFood.STATUS_PUBLISHED)
    if food.allergens == []:
        food.allergens = ["none"]
        food.save(update_fields=["allergens"])
        CatalogFoodSource.objects.create(
            catalog_food=food, source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
            source_name="My Scoope pilot allergen assessment",
            source_food_id=f"completo-italiano:{name.lower()}:allergens",
            license_status=CatalogFoodSource.LICENSE_ALLOWED,
            evidence_payload={
                "basis": "Single-ingredient fresh fruit/vegetable; no regulated major allergen ingredient added.",
                "meaning_of_none": "No major allergen ingredient identified; individual allergy remains possible.",
                "pilot_only": True,
            },
        )
    return food
