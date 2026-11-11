"""Build a reviewable first pass from an existing local Food Catalog snapshot.

This tool never edits the database. It deliberately leaves unknown allergens
unknown and marks uncooked animal foods and dry legumes as preparation-required.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from collections import Counter
from decimal import Decimal
from pathlib import Path

VERSION = "myscoope.solver_food_curation.v1"
FIELDS = (
    "catalog_ref", "display_name", "source_type", "source_food_id", "source_url",
    "preparation_state", "default_portion_g", "proposed_default_portion_g",
    "proposed_default_portion_label", "proposed_default_portion_source", "default_change_reason", "source_portion_count",
    "proposed_food_form", "proposed_functional_roles", "proposed_meal_affinities",
    "proposed_dietary_tags", "positive_allergen_evidence", "allergen_review_state",
    "proposed_min_g", "proposed_max_g", "proposed_step_g", "portion_mode",
    "solver_use", "review_reason", "policy_version",
)

FISH = {"Anchoa cruda", "Bacalao crudo", "Lenguado crudo", "Salmón crudo", "Tilapia cruda", "Trucha arcoíris cruda"}
SOY = {"Soya cocida", "Soya seca", "Tempeh cocido", "Tofu blando", "Tofu firme"}
CONDIMENT_FRUIT = {"Lima cruda", "Limón crudo"}
VEGETABLE_STARCH = {"Camote crudo", "Choclo amarillo cocido", "Choclo amarillo crudo", "Papa cruda con piel", "Papa horneada con piel", "Taro cocido", "Yuca cruda", "Ñame cocido"}
VEGETABLE_LEGUME = {"Arvejas verdes cocidas", "Habas cocidas"}
PREPARATION_REQUIRED_PLANTS = {"Berenjena cruda", "Camote crudo", "Choclo amarillo crudo", "Habas crudas", "Hongo morchella crudo", "Okra cruda", "Papa cruda con piel", "Yuca cruda", "Zapallo butternut crudo", "Zapallo camote crudo"}
RECIPE_SEASONING = {"Ajo crudo", "Ají verde crudo", "Alga kelp cruda", "Cebolla cocida", "Cebolla cruda", "Cebollín crudo", "Lima cruda", "Limón crudo", "Puerro cocido", "Puerro crudo"}
RAW_MUSHROOMS = {"Champiñón blanco crudo", "Champiñón crimini crudo", "Hongo morchella crudo", "Hongo ostra crudo", "Hongo shiitake crudo"}


def _round(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.001")))


def _target_portion(name: str, group: str) -> Decimal:
    if name in RECIPE_SEASONING:
        return Decimal("10")
    if name.startswith("Mantequilla"):
        return Decimal("14")
    if name.startswith("Crema"):
        return Decimal("20")
    if name.startswith(("Queso", "Mozzarella", "Requesón", "Ricotta")):
        return Decimal("30")
    if name.startswith("Yogur"):
        return Decimal("170")
    if name.startswith("Leche"):
        return Decimal("240")
    if group == "fruits_and_fruit_juices":
        return Decimal("40") if name.endswith("seca") or name.endswith("seco") else Decimal("150")
    if group == "vegetables_and_vegetable_products":
        return Decimal("150") if name in VEGETABLE_STARCH else Decimal("100")
    if group in {"cereals", "tubers", "legumes"}:
        return Decimal("40") if name == "Avena tradicional" else Decimal("150")
    if group == "fats":
        return Decimal("15") if name == "Aceite de oliva" else Decimal("30")
    if group == "legumes_and_legume_products":
        return Decimal("60") if name.endswith("seca") or name.endswith("secos") else Decimal("150")
    return Decimal("150")


def _selected_portion(row: sqlite3.Row, source_portions: list[dict]) -> tuple[Decimal, str, str]:
    current = Decimal(str(row["default_portion_g"]))
    target = _target_portion(row["display_name"], row["food_group"])
    if row["display_name"].startswith("Yogur"):
        for option in source_portions:
            if "container (6 oz)" in str(option.get("modifier", "")):
                return Decimal(str(option["grams"])), "1 envase (6 oz)", "Envase individual USDA; política de unidad entera."
    if row["display_name"] in {"Higo seco", "Ciruela seca", "Damasco seco"}:
        for option in source_portions:
            if str(option.get("amount")) == "1" and "cup" in str(option.get("modifier", "")):
                return Decimal(str(option["grams"])) / 4, "1/4 taza", "Cuarto de taza USDA: peso de 1 taza dividido por cuatro; orientación MyPlate."
    if target * Decimal("0.5") <= current <= target * Decimal("2"):
        return current, row["default_portion_label"], ""
    candidates = []
    for option in source_portions:
        try:
            grams = Decimal(str(option["grams"]))
        except (KeyError, ValueError, ArithmeticError):
            continue
        if target * Decimal("0.5") <= grams <= target * Decimal("2"):
            label = " ".join(filter(None, (str(option.get("amount", "")), str(option.get("modifier", ""))))).strip()
            candidates.append((abs(grams - target), grams, label))
    if not candidates:
        return current, row["default_portion_label"], "Default fuera de rango editorial y sin medida USDA alternativa; revisión necesaria."
    _, grams, label = min(candidates)
    return grams, label, f"Medida USDA alternativa más próxima a objetivo editorial {target} g."


def _profile(row: sqlite3.Row) -> dict[str, str]:
    name, group, state = row["display_name"], row["food_group"], row["preparation_state"]
    default = Decimal(str(row["default_portion_g"]))
    source = json.loads(row["evidence_payload"] or "{}")
    source_portions = source.get("source_portions", [])
    selected, selected_label, change_reason = _selected_portion(row, source_portions)
    roles: list[str]
    affinities: list[str]
    tags: list[str] = []
    use = "direct_candidate"
    reasons: list[str] = []
    form = "ingredient"

    if group == "fruits_and_fruit_juices":
        roles, affinities = ["fruit"], ["breakfast", "snack"]
        if name in CONDIMENT_FRUIT:
            roles, affinities = ["vegetable"], ["main", "dinner"]
            form = "condiment"
        tags = ["vegan", "vegetarian", "pescatarian"]
    elif group == "vegetables_and_vegetable_products":
        roles, affinities = ["vegetable"], ["main", "dinner"]
        if name in VEGETABLE_STARCH:
            roles = ["starch_or_carbohydrate"]
        elif name in VEGETABLE_LEGUME:
            roles = ["supporting_protein", "starch_or_carbohydrate"]
        if name in RECIPE_SEASONING:
            form = "condiment"
        tags = ["vegan", "vegetarian", "pescatarian"]
    elif group == "legumes_and_legume_products":
        roles, affinities = ["supporting_protein", "starch_or_carbohydrate"], ["main", "dinner"]
        if name.startswith("Tofu") or name.startswith("Tempeh"):
            roles = ["primary_protein"]
        tags = ["vegan", "vegetarian", "pescatarian"]
    elif group == "dairy_and_egg_products":
        tags = ["vegetarian", "pescatarian"]
        if name.startswith(("Mantequilla", "Crema")):
            roles, affinities = ["added_or_dense_fat"], ["breakfast", "main", "dinner"]
        elif name.startswith("Leche"):
            roles, affinities, form = ["supporting_protein"], ["breakfast", "snack"], "beverage"
        elif name.startswith("Yogur"):
            roles, affinities = ["supporting_protein"], ["breakfast", "snack"]
        else:
            roles, affinities = ["supporting_protein", "added_or_dense_fat"], ["breakfast", "snack", "main", "dinner"]
    elif group == "cereals":
        roles = ["starch_or_carbohydrate"]
        affinities = ["breakfast", "snack"] if name == "Avena tradicional" else ["main", "dinner"]
        tags = ["vegan", "vegetarian", "pescatarian"]
    elif group == "tubers":
        roles, affinities = ["starch_or_carbohydrate"], ["main", "dinner"]
        tags = ["vegan", "vegetarian", "pescatarian"]
    elif group == "legumes":
        roles, affinities = ["supporting_protein", "starch_or_carbohydrate"], ["main", "dinner"]
        tags = ["vegan", "vegetarian", "pescatarian"]
    elif group == "dairy":
        roles, affinities = ["supporting_protein"], ["breakfast", "snack"]
        tags = ["vegetarian", "pescatarian"]
        if name.startswith("Leche"):
            form = "beverage"
    elif group == "fats":
        roles = ["added_or_dense_fat"]
        affinities = ["breakfast", "snack"] if name in {"Almendras", "Nueces", "Mantequilla de maní natural"} else ["main", "dinner"]
        tags = ["vegan", "vegetarian", "pescatarian"]
        if name == "Aceite de oliva":
            form = "condiment"
    elif group == "fruit":
        roles, affinities = ["fruit"], ["breakfast", "snack"]
        tags = ["vegan", "vegetarian", "pescatarian"]
    elif group == "vegetables":
        roles, affinities = ["vegetable"], ["main", "dinner"]
        tags = ["vegan", "vegetarian", "pescatarian"]
    elif group == "protein":
        roles, affinities = ["primary_protein"], ["main", "dinner"]
        if name in {"Huevo entero", "Clara de huevo"}:
            affinities = ["breakfast", "main", "dinner"]
            tags = ["vegetarian", "pescatarian"]
        elif name in {"Atún en agua drenado", "Salmón cocido"}:
            tags = ["pescatarian"]
    else:
        roles, affinities = ["primary_protein"], ["main", "dinner"]
        if group == "finfish_and_shellfish_products":
            tags = ["pescatarian"]

    if (state == "dry" and group not in {"fruits_and_fruit_juices", "cereals", "fats"}) or (state == "raw" and group in {
        "beef_products", "pork_products", "poultry_products", "lamb_veal_and_game_products", "finfish_and_shellfish_products",
    }) or name in PREPARATION_REQUIRED_PLANTS or name in RAW_MUSHROOMS:
        use = "preparation_required"
        reasons.append("Debe vincularse a una preparación comestible antes de ser candidato directo.")
    if name in RECIPE_SEASONING:
        use = "recipe_component"
        reasons.append("Uso culinario como componente; no como porción independiente.")
    if row["default_portion_label"] == "100 g (base nutricional)":
        reasons.append("Porción de 100 g sólo como base nutricional; revisar medida doméstica.")

    allergen = ""
    if group == "dairy_and_egg_products":
        allergen = "milk"
    elif group == "dairy":
        allergen = "milk"
    elif name in {"Huevo entero", "Clara de huevo"}:
        allergen = "egg"
    elif name in {"Atún en agua drenado", "Salmón cocido"}:
        allergen = "fish"
    elif name in {"Almendras", "Nueces"}:
        allergen = "nuts"
    elif name == "Mantequilla de maní natural":
        allergen = "peanut"
    elif name in FISH:
        allergen = "fish"
    elif group == "finfish_and_shellfish_products":
        allergen = "shellfish"
    elif name in SOY:
        allergen = "soy"

    # Whole foods and generic yogurt are sold in varied amounts. Do not assume
    # that a source household measure represents an indivisible retail package.
    minimum = max(Decimal("1"), selected * Decimal("0.5"))
    maximum = max(selected, selected * Decimal("2"))
    step = Decimal("1") if selected <= 20 else Decimal("5") if selected <= 100 else Decimal("10")
    portion_mode = "flexible_weight"
    if name.startswith("Yogur"):
        minimum, maximum, step = selected, selected * 2, selected
        portion_mode = "whole_unit"
    if form == "condiment":
        maximum = selected
    if change_reason:
        reasons.append(change_reason)
    if not source_portions and row["source_type"] == "usda":
        reasons.append("USDA no registra medida doméstica para este FDC ID.")

    return {
        "catalog_ref": row["catalog_ref"], "display_name": name,
        "source_type": row["source_type"],
        "source_food_id": row["source_food_id"] or "", "source_url": row["source_url"] or "",
        "preparation_state": state, "default_portion_g": _round(default),
        "proposed_default_portion_g": _round(selected),
        "proposed_default_portion_label": selected_label,
        "proposed_default_portion_source": "USDA SR Legacy 2018-04 + MyPlate, derivación de 1/4 taza" if name in {"Higo seco", "Ciruela seca", "Damasco seco"} else row["source_url"] or "",
        "default_change_reason": change_reason,
        "source_portion_count": str(len(source_portions)),
        "proposed_food_form": form,
        "proposed_functional_roles": "|".join(roles),
        "proposed_meal_affinities": "|".join(affinities),
        "proposed_dietary_tags": "|".join(tags),
        "positive_allergen_evidence": allergen,
        "allergen_review_state": "positive_identity_candidate" if allergen else "unknown",
        "proposed_min_g": _round(minimum), "proposed_max_g": _round(maximum),
        "proposed_step_g": _round(step), "portion_mode": portion_mode,
        "solver_use": use, "review_reason": " ".join(reasons), "policy_version": VERSION,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with sqlite3.connect(f"file:{args.database}?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("""SELECT f.*, p.grams AS default_portion_g, p.label AS default_portion_label,
                   s.source_food_id, s.source_url, s.evidence_payload
                   FROM food_catalog_catalogfood f
                   JOIN food_catalog_catalogfoodportion p ON p.catalog_food_id=f.id AND p.is_default=1
                   JOIN food_catalog_catalogfoodsource s ON s.catalog_food_id=f.id
                   ORDER BY f.catalog_ref""").fetchall()
    output = [_profile(row) for row in rows]
    if len(output) != 219 or len({row["catalog_ref"] for row in output}) != len(output):
        raise SystemExit("Expected 219 unique source-linked foods")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)
    print({"rows": len(output), "solver_use": dict(Counter(row["solver_use"] for row in output))})


if __name__ == "__main__":
    main()
