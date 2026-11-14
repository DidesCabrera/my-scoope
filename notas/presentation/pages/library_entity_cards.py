"""Present preparation and supplement library rows with the shared web card contract."""

from decimal import Decimal

from django.urls import reverse

_DOSE_UNITS = {
    "capsule": ("cápsula", "cápsulas"), "tablet": ("comprimido", "comprimidos"),
    "softgel": ("cápsula blanda", "cápsulas blandas"), "gummy": ("gomita", "gomitas"),
    "sachet": ("sobre", "sobres"), "scoop": ("medida", "medidas"),
    "drop": ("gota", "gotas"), "tsp": ("cucharadita", "cucharaditas"),
    "iu": ("UI", "UI"),
}


def _number_label(value):
    formatted = format(value, "f")
    return formatted.rstrip("0").rstrip(".") if "." in formatted else formatted


def preparation_kpis(version, *, portion=False, weight=None):
    """Adapt a recipe version to components/dash_kpi.html."""
    factor = version.default_portion_g / version.yield_g if portion else Decimal("1")
    protein = version.protein_g * factor
    carbs = version.carbs_g * factor
    fat = version.fat_g * factor
    kcal_protein = protein * 4
    kcal_carbs = carbs * 4
    kcal_fat = fat * 9
    total = kcal_protein + kcal_carbs + kcal_fat
    return {
        "tot_kcal": total,
        "g_protein": protein,
        "g_carbs": carbs,
        "g_fat": fat,
        "kcal_protein": kcal_protein,
        "kcal_carbs": kcal_carbs,
        "kcal_fat": kcal_fat,
        "alloc_protein": kcal_protein / total * 100 if total else 0,
        "alloc_carbs": kcal_carbs / total * 100 if total else 0,
        "alloc_fat": kcal_fat / total * 100 if total else 0,
        "ppk": protein / Decimal(str(weight)) if weight else None,
    }


def _actions(detail_url, *, edit_url=None):
    actions = []
    if edit_url:
        actions.append({
            "key": "edit", "label": "Editar", "icon": "pencil", "method": "get",
            "url": edit_url, "desktop_position": "menu", "mobile_position": "menu",
        })
    actions.append({
        "key": "detail", "label": "Ver detalle", "icon": "chevron-right", "method": "get",
        "url": detail_url, "desktop_position": "inline", "mobile_position": "inline",
    })
    return actions


def preparation_card(preparation, *, weight=None):
    version = preparation.current_version
    detail_url = reverse("preparation_detail", args=[preparation.pk])
    ingredients = []
    if version:
        portion_factor = version.default_portion_g / version.yield_g
        ingredients = [
            {"name": item.get("name", "Alimento"), "quantity_g": Decimal(str(item.get("quantity_g", 0))) * portion_factor}
            for item in version.ingredients_snapshot
        ]
    return {
        "id": preparation.pk,
        "title": {"name": preparation.name, "label": "preparation", "icon": "cooking-pot", "url": detail_url},
        "subtitle": (
            f"Porción habitual · {_number_label(version.default_portion_g)} g" if version else "Pendiente de ingredientes"
        ),
        "ingredient_count": len(ingredients),
        "ingredients": ingredients,
        "kpis": preparation_kpis(version, portion=True, weight=weight) if version else None,
        "actions": _actions(
            detail_url,
            edit_url=reverse("preparation_edit", args=[preparation.pk]) if not preparation.is_global else None,
        ),
        "hide_overflow": preparation.is_global,
    }


def preparation_food_rows(ingredients, kpis, *, weight=None):
    """Adapt frozen recipe ingredients to the shared food panel grids."""
    rows = []
    for ingredient in ingredients:
        protein = ingredient.get("protein", Decimal("0"))
        carbs = ingredient.get("carbs", Decimal("0"))
        fat = ingredient.get("fat", Decimal("0"))
        calories = ingredient.get("calories", Decimal("0"))
        kcal_protein = protein * 4
        kcal_carbs = carbs * 4
        kcal_fat = fat * 9
        rows.append({
            "child": {"id": ingredient["food_id"]},
            "rel": {
                "name": ingredient["name"], "quantity": ingredient["quantity_g"], "quantity_unit": "g",
                "total_kcal": calories,
                "g_protein": protein, "g_carbs": carbs, "g_fat": fat,
                "ppk": protein / Decimal(str(weight)) if weight else None,
                "kcal_share": calories / kpis["tot_kcal"] * 100 if kpis["tot_kcal"] else 0,
                "kcal_distribution": {
                    "protein": kcal_protein / calories * 100 if calories else 0,
                    "carbs": kcal_carbs / calories * 100 if calories else 0,
                    "fat": kcal_fat / calories * 100 if calories else 0,
                },
                "alloc_protein": kcal_protein / kpis["kcal_protein"] * 100 if kpis["kcal_protein"] else 0,
                "alloc_carbs": kcal_carbs / kpis["kcal_carbs"] * 100 if kpis["kcal_carbs"] else 0,
                "alloc_fat": kcal_fat / kpis["kcal_fat"] * 100 if kpis["kcal_fat"] else 0,
            },
        })
    return rows


def preparation_ingredient_cards(ingredients, *, weight=None):
    """Give each recipe ingredient the same Food entity card used in other details."""
    cards = []
    for ingredient in ingredients:
        protein = ingredient.get("protein", Decimal("0"))
        carbs = ingredient.get("carbs", Decimal("0"))
        fat = ingredient.get("fat", Decimal("0"))
        kcal_protein = protein * 4
        kcal_carbs = carbs * 4
        kcal_fat = fat * 9
        total = kcal_protein + kcal_carbs + kcal_fat
        detail_url = reverse("food_detail", args=[ingredient["food_id"]])
        cards.append({
            "child_id": f"preparation-food-{ingredient['food_id']}",
            "titulo": {"name": ingredient["name"], "label": "food", "icon": "carrot", "food_id": ingredient["food_id"], "url": detail_url},
            "related_data": {"quantity": ingredient["quantity_g"], "unit": "g"},
            "kpis": {
                "tot_kcal": total, "g_protein": protein, "g_carbs": carbs, "g_fat": fat,
                "kcal_protein": kcal_protein, "kcal_carbs": kcal_carbs, "kcal_fat": kcal_fat,
                "alloc_protein": kcal_protein / total * 100 if total else 0,
                "alloc_carbs": kcal_carbs / total * 100 if total else 0,
                "alloc_fat": kcal_fat / total * 100 if total else 0,
                "ppk": protein / Decimal(str(weight)) if weight else None,
            },
            "nutrition_facts": {
                "basis_label": f"Para {_number_label(ingredient['quantity_g'])} g",
                "saturated_fat": None, "sugar": None, "fiber": None, "sodium": None,
            },
            "hide_overflow_actions": True,
            "actions": _actions(detail_url),
        })
    return cards


def supplement_card(supplement):
    detail_url = reverse("supplement_detail", args=[supplement.pk])
    dose_label = ""
    if supplement.default_quantity and supplement.default_unit:
        units = _DOSE_UNITS.get(supplement.default_unit, (supplement.default_unit, supplement.default_unit))
        unit = units[0] if supplement.default_quantity == 1 else units[1]
        dose_label = f"{_number_label(supplement.default_quantity)} {unit}"
    return {
        "id": supplement.pk,
        "title": {"name": supplement.name, "label": "supplement", "icon": "pill", "url": detail_url},
        "subtitle": supplement.brand,
        "component_count": len(supplement.components or []),
        "dose_label": dose_label,
        "actions": _actions(detail_url, edit_url=reverse("supplement_edit", args=[supplement.pk])),
    }


def supplement_preset_card(preset):
    detail_url = reverse("supplement_preset_detail", args=[preset.pk])
    items = list(preset.items.all())
    return {
        "id": preset.pk,
        "title": {"name": preset.name, "label": "supplement", "eyebrow": "Ingesta de suplementos", "icon": "pill-bottle", "url": detail_url},
        "item_count": len(items),
        "summary": ", ".join((item.supplement_snapshot or {}).get("name") or "Suplemento guardado" for item in items),
        "actions": _actions(detail_url, edit_url=reverse("supplement_preset_edit", args=[preset.pk])),
    }
