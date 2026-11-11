"""Compare stored SR Legacy evidence with the official USDA JSON archive.

Usage: python verify_solver_usda_sr_legacy.py --database db.sqlite3 --archive sr-legacy.zip
The database is opened read-only. The archive is streamed to avoid loading it
into memory, and this script does not alter either input.
"""

from __future__ import annotations

import argparse
import collections
import io
import json
import sqlite3
import zipfile
from decimal import Decimal
from pathlib import Path


NUTRIENT_IDS = {
    "protein_g": 1003,
    "carbs_g": 1005,
    "fat_g": 1004,
    "fiber_g": 1079,
    "sugar_g": 2000,
    "saturated_fat_g": 1258,
    "sodium_mg": 1093,
}


def foods_from_archive(archive: Path):
    with zipfile.ZipFile(archive) as zipped:
        names = [name for name in zipped.namelist() if name.endswith(".json")]
        if len(names) != 1:
            raise ValueError("Expected one official SR Legacy JSON file in the archive")
        with io.TextIOWrapper(zipped.open(names[0]), encoding="utf-8") as stream:
            decoder = json.JSONDecoder()
            buffer = ""
            position = 0
            scanned = 0
            while True:
                if position >= len(buffer) - 8192:
                    buffer = buffer[position:] + stream.read(131072)
                    position = 0
                if scanned == 0:
                    position = buffer.index("[") + 1
                while position < len(buffer) and buffer[position] in " \r\n\t,":
                    position += 1
                if position < len(buffer) and buffer[position] == "]":
                    break
                while True:
                    try:
                        food, end = decoder.raw_decode(buffer, position)
                        break
                    except json.JSONDecodeError:
                        chunk = stream.read(131072)
                        if not chunk:
                            raise
                        buffer = buffer[position:] + chunk
                        position = 0
                position = end
                scanned += 1
                yield food


def _portions(rows, *, local: bool):
    return collections.Counter(
        (
            str(Decimal(str(row["amount"])).normalize()),
            row["modifier"],
            str(Decimal(str(row["grams" if local else "gramWeight"])).normalize()),
        )
        for row in rows
    )


def verify(database: Path, archive: Path):
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as db:
        stored = {
            int(food_id): json.loads(payload)
            for food_id, payload in db.execute(
                "SELECT source_food_id, evidence_payload FROM food_catalog_catalogfoodsource "
                "WHERE source_type='usda' AND source_food_id GLOB '[0-9]*'"
            )
        }
    found = {}
    scanned = 0
    for food in foods_from_archive(archive):
        scanned += 1
        if food["fdcId"] in stored:
            found[food["fdcId"]] = food
    issues = []
    portions_checked = 0
    nutrients_checked = 0
    for food_id, official in found.items():
        local = stored[food_id]
        if local["source_description"] != official["description"]:
            issues.append((food_id, "description"))
        local_portions = _portions(local.get("source_portions", []), local=True)
        official_portions = _portions(official.get("foodPortions", []), local=False)
        portions_checked += sum(local_portions.values())
        if local_portions != official_portions:
            issues.append((food_id, "portions"))
        nutrients = {
            row["nutrient"]["id"]: Decimal(str(row["amount"]))
            for row in official["foodNutrients"] if "amount" in row
        }
        for name, nutrient_id in NUTRIENT_IDS.items():
            value = local.get("nutrients_per_100g", {}).get(name)
            if value is None or nutrient_id not in nutrients:
                continue
            nutrients_checked += 1
            if abs(Decimal(str(value)) - nutrients[nutrient_id]) > Decimal("0.05"):
                issues.append((food_id, name))
    summary = {
        "official_foods_scanned": scanned,
        "local_source_foods": len(stored),
        "matched": len(found),
        "missing_fdc_ids": sorted(set(stored) - set(found)),
        "source_portions_checked": portions_checked,
        "nutrients_checked": nutrients_checked,
        "issue_count": len(issues),
        "issues": issues,
    }
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    args = parser.parse_args()
    summary = verify(args.database, args.archive)
    print(json.dumps(summary, ensure_ascii=False))
    if summary["missing_fdc_ids"] or summary["issue_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
