"""Regenerate the Native UI Gallery social cards from the production renderer."""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from notas.presentation.sharing_cards import render_share_card_png  # noqa: E402


OUTPUT_DIR = ROOT_DIR / "mobile" / "src" / "assets" / "dev"

SNAPSHOTS = {
    "share-card-food.png": {
        "subject": {"type": "food", "title": "Yogur griego natural"},
        "summary": {"basis_grams": 100},
        "nutrition": {"calories": 97, "protein_grams": 9, "carbs_grams": 3.8, "fat_grams": 5},
    },
    "share-card-meal.png": {
        "subject": {"type": "meal", "title": "Desayuno proteico"},
        "summary": {"food_count": 3},
        "nutrition": {"calories": 544, "protein_grams": 35.8, "carbs_grams": 68.4, "fat_grams": 14.1},
    },
    "share-card-daily-plan.png": {
        "subject": {"type": "daily_plan", "title": "Plan equilibrado de entrenamiento"},
        "summary": {"meal_count": 3, "food_count": 9},
        "nutrition": {"calories": 1924, "protein_grams": 137.2, "carbs_grams": 219.6, "fat_grams": 55.8},
    },
    "share-card-program.png": {
        "subject": {"type": "program", "title": "Programa de recomposición"},
        "summary": {"duration_weeks": 8, "filled_days": 36},
        "nutrition": {"calories": 2140, "protein_grams": 155, "carbs_grams": 238, "fat_grams": 63},
        "days": [
            {"week_number": index // 7 + 1, "day_number": index % 7 + 1, "plan": {"nutrition": {"calories": calories}}}
            for index, calories in enumerate((2040, 2140, 1960, 2210, 2100, 2060, 1920, 2080, 2230, 2070, 2160, 2100, 2220, 1980))
        ],
    },
}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, snapshot in SNAPSHOTS.items():
        (OUTPUT_DIR / filename).write_bytes(render_share_card_png(snapshot))


if __name__ == "__main__":
    main()
