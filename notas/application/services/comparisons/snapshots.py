from types import SimpleNamespace
from typing import Any

from .payloads import normalize_payload, parse_quantity


COMPARISON_VALUE_KEYS = (
    "total_kcal",
    "ppk",
    "protein",
    "carbs",
    "fat",
    "alloc_protein",
    "alloc_carbs",
    "alloc_fat",
)


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback

    return parsed


def _snapshot_values(values: dict[str, Any]) -> dict[str, float]:
    return {
        key: _safe_float(values.get(key), fallback=0.0)
        for key in COMPARISON_VALUE_KEYS
        if key in values
    }


def snapshot_payload_from_comparable_rows(
    comparable_rows,
    *,
    include_quantities: bool = False,
) -> list[dict[str, Any]]:
    """
    Build a stable snapshot for a saved comparison.

    The regular payload stores only the selected entity ids (and quantities for foods).
    The snapshot stores the computed labels and metric values at save time, so a saved
    comparison can be reviewed later even if the source entities change.
    """
    snapshot: list[dict[str, Any]] = []

    for selection, values in comparable_rows:
        selected_id = getattr(selection, "id", None)
        name = (getattr(selection, "name", "") or "").strip()

        if not selected_id or not name:
            continue

        row: dict[str, Any] = {
            "id": int(selected_id),
            "name": name,
            "values": _snapshot_values(values),
        }

        if include_quantities:
            row["quantity"] = parse_quantity(getattr(selection, "quantity", None), fallback=100.0)

        snapshot.append(row)

    return snapshot


def normalize_snapshot_payload(payload: Any, *, include_quantities: bool = False) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []

    normalized: list[dict[str, Any]] = []

    for row in payload:
        if not isinstance(row, dict):
            continue

        base = normalize_payload([row], include_quantities=include_quantities)
        if not base:
            continue

        normalized_row = dict(base[0])
        normalized_row["name"] = str(row.get("name") or "").strip()
        values = row.get("values") if isinstance(row.get("values"), dict) else {}
        normalized_row["values"] = _snapshot_values(values)
        normalized.append(normalized_row)

    return normalized


def selection_rows_from_snapshot(payload: Any, *, include_quantities: bool = False) -> list[dict[str, Any]]:
    rows = normalize_snapshot_payload(payload, include_quantities=include_quantities)

    return [
        {
            "id": row.get("id"),
            "name": row.get("name", ""),
            "quantity": row.get("quantity") if include_quantities else None,
        }
        for row in rows
    ]


def comparable_rows_from_snapshot(payload: Any, *, include_quantities: bool = False):
    comparable_rows = []

    for index, row in enumerate(normalize_snapshot_payload(payload, include_quantities=include_quantities), start=1):
        selection = SimpleNamespace(
            id=row.get("id"),
            name=row.get("name") or "Elemento eliminado",
            quantity=row.get("quantity") if include_quantities else None,
            position=index,
        )
        comparable_rows.append((selection, row.get("values", {})))

    return comparable_rows
