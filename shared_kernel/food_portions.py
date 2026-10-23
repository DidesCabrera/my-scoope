"""Canonical My Scoope food groups and everyday portion measures.

The stored values are stable machine keys. Spanish labels belong to the product
contract and are shared by Food Catalog, operational foods and selectors.
"""

from __future__ import annotations

from enum import StrEnum


class MyScoopeFoodGroup(StrEnum):
    VEGETABLES = "vegetables"
    MUSHROOMS = "mushrooms"
    ALGAE = "algae"
    FRUITS = "fruits"
    CEREALS_AND_PSEUDOCEREALS = "cereals_and_pseudocereals"
    STARCHY_ROOTS_AND_TUBERS = "starchy_roots_and_tubers"
    LEGUMES_AND_DERIVATIVES = "legumes_and_derivatives"
    NUTS_AND_SEEDS = "nuts_and_seeds"
    MEATS = "meats"
    POULTRY = "poultry"
    FISH = "fish"
    SHELLFISH = "shellfish"
    EGGS = "eggs"
    DAIRY = "dairy"
    FATS_AND_OILS = "fats_and_oils"


MY_SCOOPE_FOOD_GROUP_LABELS = {
    MyScoopeFoodGroup.VEGETABLES: "Verduras y hortalizas",
    MyScoopeFoodGroup.MUSHROOMS: "Hongos",
    MyScoopeFoodGroup.ALGAE: "Algas",
    MyScoopeFoodGroup.FRUITS: "Frutas",
    MyScoopeFoodGroup.CEREALS_AND_PSEUDOCEREALS: "Cereales y pseudocereales",
    MyScoopeFoodGroup.STARCHY_ROOTS_AND_TUBERS: "Tubérculos y raíces feculentas",
    MyScoopeFoodGroup.LEGUMES_AND_DERIVATIVES: "Legumbres y derivados",
    MyScoopeFoodGroup.NUTS_AND_SEEDS: "Frutos secos y semillas",
    MyScoopeFoodGroup.MEATS: "Carnes",
    MyScoopeFoodGroup.POULTRY: "Aves",
    MyScoopeFoodGroup.FISH: "Pescados",
    MyScoopeFoodGroup.SHELLFISH: "Mariscos",
    MyScoopeFoodGroup.EGGS: "Huevos",
    MyScoopeFoodGroup.DAIRY: "Lácteos",
    MyScoopeFoodGroup.FATS_AND_OILS: "Grasas y aceites",
}

MY_SCOOPE_FOOD_GROUP_CHOICES = tuple(
    (group.value, label) for group, label in MY_SCOOPE_FOOD_GROUP_LABELS.items()
)
MY_SCOOPE_FOOD_GROUP_BY_LABEL = {
    label: group.value for group, label in MY_SCOOPE_FOOD_GROUP_LABELS.items()
}


class HouseholdMeasure(StrEnum):
    UNIT = "unit"
    CUP = "cup"
    TABLESPOON = "tablespoon"
    SLICE = "slice"
    CAN = "can"
    FILLET = "fillet"
    LEAF = "leaf"
    STRIP = "strip"
    GRAM = "g"
    MILLILITER = "ml"


HOUSEHOLD_MEASURE_LABELS = {
    HouseholdMeasure.UNIT: "unidad",
    HouseholdMeasure.CUP: "taza",
    HouseholdMeasure.TABLESPOON: "cucharada",
    HouseholdMeasure.SLICE: "rodaja",
    HouseholdMeasure.CAN: "lata",
    HouseholdMeasure.FILLET: "filete",
    HouseholdMeasure.LEAF: "hoja",
    HouseholdMeasure.STRIP: "tira",
    HouseholdMeasure.GRAM: "g",
    HouseholdMeasure.MILLILITER: "ml",
}

HOUSEHOLD_MEASURE_CHOICES = tuple(
    (measure.value, label) for measure, label in HOUSEHOLD_MEASURE_LABELS.items()
)
HOUSEHOLD_MEASURE_BY_LABEL = {
    label: measure.value for measure, label in HOUSEHOLD_MEASURE_LABELS.items()
}


def myscoope_food_group_label(value: str) -> str:
    try:
        return MY_SCOOPE_FOOD_GROUP_LABELS[MyScoopeFoodGroup(value)]
    except ValueError:
        return ""


def household_measure_label(value: str) -> str:
    try:
        return HOUSEHOLD_MEASURE_LABELS[HouseholdMeasure(value)]
    except ValueError:
        return ""


__all__ = [
    "HOUSEHOLD_MEASURE_BY_LABEL",
    "HOUSEHOLD_MEASURE_CHOICES",
    "HOUSEHOLD_MEASURE_LABELS",
    "MY_SCOOPE_FOOD_GROUP_BY_LABEL",
    "MY_SCOOPE_FOOD_GROUP_CHOICES",
    "MY_SCOOPE_FOOD_GROUP_LABELS",
    "HouseholdMeasure",
    "MyScoopeFoodGroup",
    "household_measure_label",
    "myscoope_food_group_label",
]
