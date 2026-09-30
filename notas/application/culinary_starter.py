"""Small, explicit starter library. Rule-validated, NEVER human-validated by seeding.

Matches exact operational names and known preparation states. Missing ingredients
are reported, not substituted by an unconstrained macro search.
"""

from itertools import product

from django.db import transaction

from notas.application.culinary_library import normalized, validate_variant
from notas.application.queries.solver_food_candidates import get_solver_food_candidate_queryset
from notas.domain.models import CulinaryTemplate, CulinaryVariant


def component(group, names, minimum, maximum, step=5):
    return {"group": group, "names": names, "minimum_g": minimum, "maximum_g": maximum, "step_g": step}


FRUIT = ["Manzana", "Plátano", "Arándanos"]
STARTER = (
    ("yogurt-bowl", "Yogur con avena y fruta", ["breakfast", "snack"],
     "Mezclar la avena con el yogur y dejar hidratar; añadir la fruta lavada y cortada.", {
         "base": component("dairy", ["Yogur griego natural sin azúcar"], 150, 350),
         "cereal": component("starch", ["Avena tradicional"], 20, 65),
         "fruit": component("fruit", FRUIT, 100, 200)},
     [{"left": "cereal", "right": "base", "minimum": .06, "maximum": .3}]),
    ("porridge", "Avena cremosa con claras y fruta", ["breakfast", "snack"],
     "Cocer la avena en leche; incorporar las claras removiendo hasta que queden completamente cocidas. Servir con fruta aparte.", {
         "milk": component("dairy", ["Leche descremada"], 150, 300),
         "cereal": component("starch", ["Avena tradicional"], 25, 70),
         "protein": component("protein", ["Clara de huevo"], 80, 200),
         "fruit": component("fruit", FRUIT, 100, 180)},
     [{"left": "cereal", "right": "milk", "minimum": .08, "maximum": .4}]),
    ("oat-pancakes", "Panqueques de avena con fruta", ["breakfast", "snack"],
     "Moler la avena, mezclar con huevo y claras; cocinar por ambos lados en sartén antiadherente hasta cocción completa. Servir la fruta al lado.", {
         "cereal": component("starch", ["Avena tradicional"], 25, 65),
         "egg": component("protein", ["Huevo entero"], 50, 100, 50),
         "white": component("protein", ["Clara de huevo"], 80, 200),
         "fruit": component("fruit", FRUIT, 100, 180)},
     [{"left": "cereal", "right": "white", "minimum": .15, "maximum": .6}]),
    ("warm-plate", "Plato de cereal, proteína y brócoli", ["main", "dinner"],
     "Servir el cereal y la proteína ya cocidos con brócoli; distribuir el aceite medido como aderezo. Las cantidades son del alimento en el estado indicado.", {
         "starch": component("starch", ["Arroz blanco cocido", "Arroz integral cocido", "Quinoa cocida"], 80, 300),
         "protein": component("protein", ["Pechuga de pollo cocida", "Pechuga de pavo cocida", "Carne magra cocida"], 100, 230),
         "vegetable": component("vegetable", ["Brócoli cocido"], 100, 250),
         "fat": component("fat", ["Aceite de oliva"], 5, 15)}, []),
    ("tuber-plate", "Papas o camote con proteína y ensalada", ["main", "dinner"],
     "Calentar las papas o camote y la proteína cocida. Servir con zanahoria rallada o tomate; añadir el aceite medido a la ensalada.", {
         "starch": component("starch", ["Papa cocida sin piel", "Camote cocido"], 100, 350),
         "protein": component("protein", ["Pechuga de pollo cocida", "Pechuga de pavo cocida", "Carne magra cocida"], 100, 230),
         "vegetable": component("vegetable", ["Zanahoria cruda", "Tomate"], 100, 200),
         "fat": component("fat", ["Aceite de oliva"], 5, 15)}, []),
    ("grain-salad", "Ensalada de quinoa o arroz con atún", ["main", "dinner"],
     "Mezclar el cereal cocido y enfriado con atún drenado y tomate lavado. Añadir palta en cubos al servir. Mantener refrigerado hasta consumir.", {
         "starch": component("starch", ["Quinoa cocida", "Arroz integral cocido"], 100, 300),
         "protein": component("protein", ["Atún en agua drenado"], 100, 220),
         "vegetable": component("vegetable", ["Tomate"], 100, 200),
         "fat": component("fat", ["Palta"], 30, 70)}, []),
    ("legume-plate", "Legumbres con arroz, pollo y verduras", ["main", "dinner"],
     "Calentar las legumbres y arroz cocidos, añadir pollo cocido desmenuzado y servir con zanahoria rallada aparte.", {
         "legume": component("legume", ["Lentejas cocidas", "Porotos negros cocidos", "Garbanzos cocidos"], 80, 180),
         "starch": component("starch", ["Arroz blanco cocido"], 60, 160),
         "protein": component("protein", ["Pechuga de pollo cocida"], 80, 180),
         "vegetable": component("vegetable", ["Zanahoria cruda"], 100, 180)}, []),
)


@transaction.atomic
def seed_starter_library(*, user):
    """Idempotently create PRIVATE starter variants; preserve all existing records."""
    by_name = {}
    for food in get_solver_food_candidate_queryset(user).order_by("pk"):
        by_name.setdefault(normalized(food.name), food)
    created, skipped = 0, []
    for key, name, kinds, preparation, definitions, ratios in STARTER:
        choices, rules = {}, {}
        for role, definition in definitions.items():
            matches = [by_name[normalized(n)] for n in definition["names"] if normalized(n) in by_name
                       and by_name[normalized(n)].preparation_state != "unknown"]
            if not matches:
                skipped.append({"template": key, "component": role, "missing": definition["names"]})
            choices[role] = matches
            rules[role] = {k: v for k, v in definition.items() if k != "names"}
            rules[role]["foods"] = {str(food.pk): {"species": normalized(food.canonical_name or food.name),
                                                  "preparation_state": food.preparation_state} for food in matches}
        if any(not matches for matches in choices.values()):
            continue
        template, _ = CulinaryTemplate.objects.get_or_create(key=f"starter-{user.pk}-{key}", version=1,
            defaults={"owner": user, "name": name, "family": "protein-side-vegetable" if key in {"warm-plate", "tuber-plate"} else key, "meal_kinds": kinds,
                      "preparation": preparation, "rules": {"components": rules, "ratios": ratios}})
        # Existing version may intentionally have a different approved substitution set.
        for combination in product(*choices.values()):
            ingredients = [{"component": role, "food_id": food.pk,
                            **{k: definitions[role][k] for k in ("minimum_g", "maximum_g", "step_g")}}
                           for role, food in zip(choices, combination)]
            variant_key = "foods-" + "-".join(str(food.pk) for food in combination)
            variant, new = CulinaryVariant.objects.get_or_create(template=template, key=variant_key, version=1,
                defaults={"name": (name + ": " + ", ".join(food.name for food in combination))[:150],
                          "ingredients": ingredients, "preparation": preparation})
            if new:
                validate_variant(user=user, variant_id=variant.pk)
                created += 1
    return {"created": created, "skipped": skipped, "human_validated": False, "visibility": "private"}
