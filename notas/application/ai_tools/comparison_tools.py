from __future__ import annotations

from typing import Any

from notas.application.ai_tools.runtime import run_ai_tool
from notas.application.services.comparisons.snapshots import normalize_snapshot_payload
from notas.domain.models import SavedComparison

SUPPORTED_COMPARISON_KINDS = {
    SavedComparison.KIND_FOODS,
    SavedComparison.KIND_MEALS,
    SavedComparison.KIND_DAILYPLANS,
}

COMPARISON_KIND_LABELS = {
    SavedComparison.KIND_FOODS: "Alimentos",
    SavedComparison.KIND_MEALS: "Comidas",
    SavedComparison.KIND_DAILYPLANS: "Planes diarios",
}


def _normalize_kind(kind: str | None) -> str | None:
    normalized = str(kind or "").strip().lower()
    if not normalized:
        return None
    if normalized not in SUPPORTED_COMPARISON_KINDS:
        supported = ", ".join(sorted(SUPPORTED_COMPARISON_KINDS))
        raise ValueError(f"unsupported_saved_comparison_kind:{normalized}. Supported kinds: {supported}.")
    return normalized


def _coerce_limit(limit: Any, *, default: int = 20, maximum: int = 50) -> int:
    try:
        parsed = int(limit)
    except (TypeError, ValueError):
        parsed = default
    if parsed < 1:
        return default
    return min(parsed, maximum)


def _include_quantities(kind: str) -> bool:
    return kind == SavedComparison.KIND_FOODS


def _snapshot_rows(comparison: SavedComparison) -> list[dict[str, Any]]:
    return normalize_snapshot_payload(
        comparison.snapshot_payload,
        include_quantities=_include_quantities(comparison.kind),
    )


def _payload_rows(comparison: SavedComparison) -> list[dict[str, Any]]:
    payload = comparison.payload if isinstance(comparison.payload, list) else []
    rows: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        item_id = row.get("id")
        if not item_id:
            continue
        payload_row = {"id": item_id}
        if _include_quantities(comparison.kind):
            payload_row["quantity"] = row.get("quantity", 100.0)
        rows.append(payload_row)
    return rows


def _preview_items(comparison: SavedComparison, *, limit: int = 4) -> list[dict[str, Any]]:
    snapshot_rows = _snapshot_rows(comparison)
    if snapshot_rows:
        return [
            {
                "id": row.get("id"),
                "name": row.get("name") or f"Elemento {index}",
                "quantity": row.get("quantity") if _include_quantities(comparison.kind) else None,
            }
            for index, row in enumerate(snapshot_rows[:limit], start=1)
        ]

    return [
        {
            "id": row.get("id"),
            "name": f"ID {row.get('id')}",
            "quantity": row.get("quantity") if _include_quantities(comparison.kind) else None,
        }
        for row in _payload_rows(comparison)[:limit]
    ]


def _comparison_summary(comparison: SavedComparison) -> dict[str, Any]:
    snapshot_rows = _snapshot_rows(comparison)
    payload_rows = _payload_rows(comparison)
    item_count = len(snapshot_rows or payload_rows)
    return {
        "id": comparison.id,
        "name": comparison.name,
        "kind": comparison.kind,
        "kind_label": COMPARISON_KIND_LABELS.get(comparison.kind, comparison.kind),
        "item_count": item_count,
        "items_preview": _preview_items(comparison),
        "has_snapshot": bool(snapshot_rows),
        "created_at": comparison.created_at.isoformat() if comparison.created_at else None,
        "updated_at": comparison.updated_at.isoformat() if comparison.updated_at else None,
    }


def _comparison_card(comparison: SavedComparison) -> dict[str, Any]:
    snapshot_rows = _snapshot_rows(comparison)
    rows = snapshot_rows or _payload_rows(comparison)
    return {
        "type": "saved_comparison_card",
        "title": comparison.name,
        "subtitle": COMPARISON_KIND_LABELS.get(comparison.kind, comparison.kind),
        "comparison_id": comparison.id,
        "kind": comparison.kind,
        "status": "snapshot" if snapshot_rows else "payload_only",
        "items": [
            {
                "id": row.get("id"),
                "name": row.get("name") or f"ID {row.get('id')}",
                "quantity": row.get("quantity") if _include_quantities(comparison.kind) else None,
                "values": row.get("values", {}),
            }
            for row in rows
        ],
        "source_boundary": {
            "source": "SavedComparison.snapshot_payload" if snapshot_rows else "SavedComparison.payload",
            "writes_allowed": False,
            "read_only": True,
            "renders_existing_comparison": True,
        },
    }


def _list_saved_comparisons_data(
    user,
    kind: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    normalized_kind = _normalize_kind(kind)
    normalized_limit = _coerce_limit(limit)

    queryset = SavedComparison.objects.filter(owner=user)
    if normalized_kind:
        queryset = queryset.filter(kind=normalized_kind)

    comparisons = list(queryset.order_by("-updated_at", "-id")[: normalized_limit + 1])
    visible = comparisons[:normalized_limit]
    return {
        "saved_comparisons": [_comparison_summary(comparison) for comparison in visible],
        "kind": normalized_kind,
        "limit": normalized_limit,
        "truncated": len(comparisons) > normalized_limit,
        "source_boundary": {
            "source": "SavedComparison",
            "writes_allowed": False,
            "read_only": True,
            "owner_scoped": True,
        },
    }


def list_saved_comparisons_tool(
    user,
    kind: str | None = None,
    limit: int = 20,
):
    return run_ai_tool(
        _list_saved_comparisons_data,
        user,
        kind=kind,
        limit=limit,
        user=user,
    )


def _read_saved_comparison_data(user, comparison_id: int) -> dict[str, Any]:
    comparison = SavedComparison.objects.get(owner=user, id=comparison_id)
    snapshot_rows = _snapshot_rows(comparison)
    payload_rows = _payload_rows(comparison)
    return {
        "saved_comparison": {
            **_comparison_summary(comparison),
            "payload": payload_rows,
            "snapshot_payload": snapshot_rows,
        },
        "comparison_card": _comparison_card(comparison),
        "source_boundary": {
            "source": "SavedComparison",
            "writes_allowed": False,
            "read_only": True,
            "owner_scoped": True,
        },
    }


def read_saved_comparison_tool(user, comparison_id: int):
    return run_ai_tool(
        _read_saved_comparison_data,
        user,
        comparison_id,
        user=user,
    )
