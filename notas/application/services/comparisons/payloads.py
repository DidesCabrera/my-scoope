from typing import Any

from .constants import MIN_COMPARATOR_SLOTS


def parse_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None

    return parsed if parsed > 0 else None


def parse_zero_based_index(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None

    return parsed if parsed >= 0 else None


def parse_quantity(value: Any, fallback: float = 100.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback

    return parsed if parsed > 0 else fallback


def quantity_from_params(params, position: int, fallback: float = 100.0) -> float:
    value = params.get(f"qty_{position}")

    if value is None and position == 1:
        value = params.get("qty_a")
    elif value is None and position == 2:
        value = params.get("qty_b")

    return parse_quantity(value, fallback=fallback)


def normalize_payload(payload: Any, *, include_quantities: bool = False) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []

    normalized: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict):
            continue

        selected_id = parse_int(row.get("id"))
        if not selected_id:
            continue

        normalized_row = {"id": selected_id}
        if include_quantities:
            normalized_row["quantity"] = parse_quantity(row.get("quantity"), fallback=100.0)
        normalized.append(normalized_row)

    return normalized


def selection_rows_from_payload(payload: Any, *, include_quantities: bool = False) -> list[dict[str, Any]]:
    rows = normalize_payload(payload, include_quantities=include_quantities)

    while len(rows) < MIN_COMPARATOR_SLOTS:
        rows.append({"id": None, "quantity": 100.0 if include_quantities else None})

    return rows


def selection_rows_from_params(
    params,
    *,
    include_quantities: bool = False,
    default_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    indexed_positions: list[int] = []

    for key in params.keys():
        if key.startswith("item_"):
            parsed = parse_int(key.removeprefix("item_"))
            if parsed:
                indexed_positions.append(parsed)

    if indexed_positions:
        max_position = max(max(indexed_positions), MIN_COMPARATOR_SLOTS)
        rows = [
            {
                "id": parse_int(params.get(f"item_{position}")),
                "quantity": quantity_from_params(params, position) if include_quantities else None,
            }
            for position in range(1, max_position + 1)
        ]
    elif default_rows is not None:
        rows = [dict(row) for row in default_rows]
    else:
        rows = [
            {
                "id": parse_int(params.get("a")),
                "quantity": quantity_from_params(params, 1) if include_quantities else None,
            },
            {
                "id": parse_int(params.get("b")),
                "quantity": quantity_from_params(params, 2) if include_quantities else None,
            },
        ]

    remove_index = parse_zero_based_index(params.get("remove_index"))

    if remove_index is not None and len(rows) > MIN_COMPARATOR_SLOTS:
        if remove_index < len(rows):
            rows.pop(remove_index)

    if params.get("comparator_action") == "add":
        rows.append({"id": None, "quantity": 100.0 if include_quantities else None})

    while len(rows) < MIN_COMPARATOR_SLOTS:
        rows.append({"id": None, "quantity": 100.0 if include_quantities else None})

    return rows


def selected_payload_from_selections(selections, *, include_quantities: bool = False) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []

    for selection in selections:
        selected_id = getattr(selection, "id", None)
        if not selected_id:
            continue

        row = {"id": int(selected_id)}
        if include_quantities:
            row["quantity"] = float(getattr(selection, "quantity", None) or 100.0)
        payload.append(row)

    return payload


def payload_has_enough_items(payload: list[dict[str, Any]]) -> bool:
    return len([row for row in payload if row.get("id")]) >= MIN_COMPARATOR_SLOTS
