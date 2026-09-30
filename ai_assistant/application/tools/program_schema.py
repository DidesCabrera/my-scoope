"""Assistant input contract for weekly requirements; no opaque instructions in notes."""

from copy import deepcopy

PROGRAM_SPECIFICATION_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "description": "Complete weekly requirements. Ask whether protein uses measured or projected weight. Never infer a weight-loss guarantee. All limits are mandatory. Generate a linear weekly trajectory only with the user's agreement.",
    "required": ["version", "duration_weeks", "meals_per_day", "weight_basis", "measured_weight_kg",
                 "protein_min_ppk", "protein_max_ppk", "fat_max_percent", "calorie_tolerance_percent",
                 "fruit_min_g", "vegetable_min_g", "weekly_fruit_species", "weekly_vegetable_species",
                 "max_family_per_week_per_slot", "weeks", "energy_source"],
    "properties": {
        "version": {"type": "integer", "enum": [1]},
        "duration_weeks": {"type": "integer", "minimum": 1, "maximum": 8},
        "meals_per_day": {"type": "integer", "minimum": 1, "maximum": 6},
        "weight_basis": {"type": "string", "enum": ["measured", "projected"],
                         "description": "User-chosen protein reference: projected uses each week's projected_weight_kg; measured uses measured_weight_kg throughout. A measured starting weight does NOT imply measured basis. Honor an explicit projected reference; ask only if unspecified."},
        "measured_weight_kg": {"type": "number", "minimum": 20, "maximum": 400},
        "protein_min_ppk": {"type": "number", "minimum": .1, "maximum": 3.5},
        "protein_max_ppk": {"type": "number", "minimum": .1, "maximum": 3.5},
        "fat_max_percent": {"type": "number", "minimum": 1, "maximum": 100},
        "calorie_tolerance_percent": {"type": "number", "minimum": 0, "maximum": 10},
        "fruit_min_g": {"type": "number", "minimum": 0, "maximum": 2000},
        "vegetable_min_g": {"type": "number", "minimum": 0, "maximum": 3000},
        "weekly_fruit_species": {"type": "integer", "minimum": 0, "maximum": 7},
        "weekly_vegetable_species": {"type": "integer", "minimum": 0, "maximum": 14},
        "max_family_per_week_per_slot": {"type": "integer", "minimum": 1, "maximum": 7},
        "energy_source": {"type": "string", "enum": ["manual", "estimated"]},
        "macro_distribution": {"type": "object", "additionalProperties": False,
                               "required": ["protein", "carbs", "fat"], "properties": {
                                   key: {"type": "number", "minimum": .01, "maximum": 99.99} for key in ("protein", "carbs", "fat")}},
        "macro_tolerance_percent": {"type": "number", "minimum": 0, "maximum": 20},
        "weeks": {"type": "array", "minItems": 1, "maxItems": 8, "items": {
            "type": "object", "additionalProperties": False, "required": ["week", "kcal", "projected_weight_kg"],
            "properties": {"week": {"type": "integer", "minimum": 1, "maximum": 8},
                           "kcal": {"type": "number", "minimum": 800, "maximum": 8000},
                           "projected_weight_kg": {"type": ["number", "null"], "minimum": 20, "maximum": 400}},
        }},
    },
}


def strict_program_specification_schema():
    """Expose the same weekly contract through OpenAI's strict, nullable transport."""
    schema = deepcopy(PROGRAM_SPECIFICATION_SCHEMA)
    schema["type"] = ["object", "null"]
    schema["required"] = list(schema["properties"])
    for key in ("macro_distribution", "macro_tolerance_percent"):
        field = schema["properties"][key]
        field["type"] = [field["type"], "null"]
    return schema
