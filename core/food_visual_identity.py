"""Shared deterministic visual identity for catalog and operational foods.

The emoji is presentation metadata. ``visual_key`` is the stable semantic key
that can later point to a My Scoope illustration without changing food names or
nutrition contracts.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class FoodVisualIdentity:
    emoji: str
    visual_key: str


_NAME_RULES: tuple[tuple[tuple[str, ...], FoodVisualIdentity], ...] = (
    (("maca", "polvo"), FoodVisualIdentity("🥣", "maca_powder")),
    (("maca",), FoodVisualIdentity("🌱", "maca_root")),
    (("pechuga", "pollo"), FoodVisualIdentity("🍗", "chicken_breast")),
    (("pechuga", "pavo"), FoodVisualIdentity("🍗", "turkey_breast")),
    (("pollo",), FoodVisualIdentity("🍗", "chicken")),
    (("pavo",), FoodVisualIdentity("🍗", "turkey")),
    (("pato",), FoodVisualIdentity("🦆", "duck")),
    (("huevo",), FoodVisualIdentity("🥚", "egg")),
    (("manzana",), FoodVisualIdentity("🍎", "apple")),
    (("pera",), FoodVisualIdentity("🍐", "pear")),
    (("platano",), FoodVisualIdentity("🍌", "banana")),
    (("banana",), FoodVisualIdentity("🍌", "banana")),
    (("naranja",), FoodVisualIdentity("🍊", "orange")),
    (("mandarina",), FoodVisualIdentity("🍊", "mandarin")),
    (("clementina",), FoodVisualIdentity("🍊", "clementine")),
    (("limon",), FoodVisualIdentity("🍋", "lemon")),
    (("lima",), FoodVisualIdentity("🍋", "lime")),
    (("sandia",), FoodVisualIdentity("🍉", "watermelon")),
    (("melon",), FoodVisualIdentity("🍈", "melon")),
    (("uva",), FoodVisualIdentity("🍇", "grapes")),
    (("frutilla",), FoodVisualIdentity("🍓", "strawberry")),
    (("fresa",), FoodVisualIdentity("🍓", "strawberry")),
    (("arandano",), FoodVisualIdentity("🫐", "blueberry")),
    (("cranberry",), FoodVisualIdentity("🫐", "cranberry")),
    (("cereza",), FoodVisualIdentity("🍒", "cherry")),
    (("guinda",), FoodVisualIdentity("🍒", "sour_cherry")),
    (("durazno",), FoodVisualIdentity("🍑", "peach")),
    (("nectarina",), FoodVisualIdentity("🍑", "nectarine")),
    (("mango",), FoodVisualIdentity("🥭", "mango")),
    (("pina",), FoodVisualIdentity("🍍", "pineapple")),
    (("coco",), FoodVisualIdentity("🥥", "coconut")),
    (("kiwi",), FoodVisualIdentity("🥝", "kiwi")),
    (("palta",), FoodVisualIdentity("🥑", "avocado")),
    (("aguacate",), FoodVisualIdentity("🥑", "avocado")),
    (("tomate",), FoodVisualIdentity("🍅", "tomato")),
    (("berenjena",), FoodVisualIdentity("🍆", "eggplant")),
    (("papa",), FoodVisualIdentity("🥔", "potato")),
    (("camote",), FoodVisualIdentity("🍠", "sweet_potato")),
    (("zanahoria",), FoodVisualIdentity("🥕", "carrot")),
    (("choclo",), FoodVisualIdentity("🌽", "corn")),
    (("maiz",), FoodVisualIdentity("🌽", "corn")),
    (("aji",), FoodVisualIdentity("🌶️", "chili_pepper")),
    (("pimenton",), FoodVisualIdentity("🫑", "bell_pepper")),
    (("pepino",), FoodVisualIdentity("🥒", "cucumber")),
    (("brocoli",), FoodVisualIdentity("🥦", "broccoli")),
    (("coliflor",), FoodVisualIdentity("🥦", "cauliflower")),
    (("ajo",), FoodVisualIdentity("🧄", "garlic")),
    (("cebolla",), FoodVisualIdentity("🧅", "onion")),
    (("champinon",), FoodVisualIdentity("🍄", "mushroom")),
    (("hongo",), FoodVisualIdentity("🍄", "mushroom")),
    (("mani",), FoodVisualIdentity("🥜", "peanut")),
    (("almendra",), FoodVisualIdentity("🌰", "almond")),
    (("nuez",), FoodVisualIdentity("🌰", "walnut")),
    (("poroto",), FoodVisualIdentity("🫘", "beans")),
    (("frijol",), FoodVisualIdentity("🫘", "beans")),
    (("lenteja",), FoodVisualIdentity("🫘", "lentils")),
    (("garbanzo",), FoodVisualIdentity("🫘", "chickpeas")),
    (("arveja",), FoodVisualIdentity("🫛", "peas")),
    (("haba",), FoodVisualIdentity("🫘", "fava_beans")),
    (("arroz",), FoodVisualIdentity("🍚", "rice")),
    (("avena",), FoodVisualIdentity("🥣", "oats")),
    (("pan",), FoodVisualIdentity("🍞", "bread")),
    (("leche",), FoodVisualIdentity("🥛", "milk")),
    (("yogur",), FoodVisualIdentity("🥣", "yogurt")),
    (("queso",), FoodVisualIdentity("🧀", "cheese")),
    (("mantequilla",), FoodVisualIdentity("🧈", "butter")),
    (("salmon",), FoodVisualIdentity("🐟", "salmon")),
    (("atun",), FoodVisualIdentity("🐟", "tuna")),
    (("camaron",), FoodVisualIdentity("🦐", "shrimp")),
    (("langosta",), FoodVisualIdentity("🦞", "lobster")),
    (("centolla",), FoodVisualIdentity("🦀", "king_crab")),
    (("cangrejo",), FoodVisualIdentity("🦀", "crab")),
    (("pulpo",), FoodVisualIdentity("🐙", "octopus")),
    (("calamar",), FoodVisualIdentity("🦑", "squid")),
    (("ostra",), FoodVisualIdentity("🦪", "oyster")),
    (("almeja",), FoodVisualIdentity("🦪", "clam")),
    (("cerdo",), FoodVisualIdentity("🥩", "pork")),
    (("vacuno",), FoodVisualIdentity("🥩", "beef")),
    (("carne",), FoodVisualIdentity("🥩", "meat")),
    (("aceite",), FoodVisualIdentity("🫒", "oil")),
    (("aceituna",), FoodVisualIdentity("🫒", "olive")),
)

_GROUP_RULES: tuple[tuple[tuple[str, ...], FoodVisualIdentity], ...] = (
    (("fruit", "fruits_and_fruit_juices"), FoodVisualIdentity("🍎", "fruit_generic")),
    (("vegetables", "vegetables_and_vegetable_products"), FoodVisualIdentity("🥬", "vegetable_generic")),
    (("legumes", "legumes_and_legume_products"), FoodVisualIdentity("🫘", "legume_generic")),
    (("cereals",), FoodVisualIdentity("🌾", "cereal_generic")),
    (("tubers",), FoodVisualIdentity("🥔", "tuber_generic")),
    (("dairy", "dairy_and_egg_products"), FoodVisualIdentity("🥛", "dairy_generic")),
    (("poultry_products",), FoodVisualIdentity("🍗", "poultry_generic")),
    (("beef_products", "lamb_veal_and_game_products"), FoodVisualIdentity("🥩", "meat_generic")),
    (("pork_products",), FoodVisualIdentity("🥩", "pork_generic")),
    (("finfish_and_shellfish_products",), FoodVisualIdentity("🐟", "seafood_generic")),
    (("protein",), FoodVisualIdentity("🍽️", "protein_generic")),
    (("fats",), FoodVisualIdentity("🫒", "fat_generic")),
)

DEFAULT_FOOD_VISUAL = FoodVisualIdentity("🍽️", "food_generic")


def infer_food_visual_identity(
    display_name: str,
    *,
    food_group: str = "",
    food_subgroup: str = "",
) -> FoodVisualIdentity:
    """Return a deterministic first-version visual for a food."""

    normalized_name = _normalize(display_name)
    for terms, visual in _NAME_RULES:
        if all(_contains_term(normalized_name, term) for term in terms):
            return visual

    normalized_groups = {_normalize(food_group), _normalize(food_subgroup)}
    for groups, visual in _GROUP_RULES:
        if any(_normalize(group) in normalized_groups for group in groups):
            return visual
    return DEFAULT_FOOD_VISUAL


def resolved_food_visual_identity(
    display_name: str,
    *,
    emoji: str = "",
    visual_key: str = "",
    food_group: str = "",
    food_subgroup: str = "",
) -> FoodVisualIdentity:
    """Prefer curated metadata and fill only missing values from inference."""

    inferred = infer_food_visual_identity(
        display_name,
        food_group=food_group,
        food_subgroup=food_subgroup,
    )
    return FoodVisualIdentity(
        emoji=(emoji or inferred.emoji).strip(),
        visual_key=(visual_key or inferred.visual_key).strip(),
    )


def _contains_term(value: str, term: str) -> bool:
    return bool(re.search(rf"(?:^|\s){re.escape(term)}(?:\s|$)", value))


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = "".join(character for character in decomposed if not unicodedata.combining(character))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).split())


__all__ = [
    "DEFAULT_FOOD_VISUAL",
    "FoodVisualIdentity",
    "infer_food_visual_identity",
    "resolved_food_visual_identity",
]
