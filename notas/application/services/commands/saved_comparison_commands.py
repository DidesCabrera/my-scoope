from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.utils import timezone

from notas.application.services.comparisons.payloads import (
    payload_has_enough_items,
    selected_payload_from_selections,
)
from notas.application.services.comparisons.snapshots import snapshot_payload_from_comparable_rows
from notas.domain.models import SavedComparison


class SavedComparisonCommandError(ValueError):
    pass


@dataclass(frozen=True)
class SavedComparisonCreateResult:
    comparison: SavedComparison


@dataclass(frozen=True)
class SavedComparisonUpdateResult:
    comparison: SavedComparison


@dataclass(frozen=True)
class SavedComparisonRenameResult:
    comparison: SavedComparison


def build_saved_comparison_name(
    *,
    entity_plural_label: str,
    selections: list[Any],
) -> str:
    selected_names = [selection.name for selection in selections if getattr(selection, "id", None) and selection.name]

    if not selected_names:
        timestamp = timezone.localtime().strftime("%d/%m/%Y %H:%M")
        return f"Comparación de {entity_plural_label} · {timestamp}"

    visible_names = " vs ".join(selected_names[:2])
    extra_count = max(len(selected_names) - 2, 0)
    suffix = f" + {extra_count}" if extra_count else ""

    return f"{visible_names}{suffix}"


def _payload_and_snapshot(
    *,
    selections: list[Any],
    comparable_rows,
    include_quantities: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    payload = selected_payload_from_selections(selections, include_quantities=include_quantities)

    if not payload_has_enough_items(payload):
        raise SavedComparisonCommandError("saved_comparison_requires_two_items")

    snapshot_payload = snapshot_payload_from_comparable_rows(
        comparable_rows,
        include_quantities=include_quantities,
    )

    if not payload_has_enough_items(snapshot_payload):
        raise SavedComparisonCommandError("saved_comparison_snapshot_requires_two_items")

    return payload, snapshot_payload


@transaction.atomic
def create_saved_comparison(
    *,
    owner,
    kind: str,
    entity_plural_label: str,
    selections: list[Any],
    comparable_rows,
    include_quantities: bool = False,
) -> SavedComparisonCreateResult:
    payload, snapshot_payload = _payload_and_snapshot(
        selections=selections,
        comparable_rows=comparable_rows,
        include_quantities=include_quantities,
    )

    comparison = SavedComparison.objects.create(
        owner=owner,
        kind=kind,
        name=build_saved_comparison_name(
            entity_plural_label=entity_plural_label,
            selections=selections,
        ),
        payload=payload,
        snapshot_payload=snapshot_payload,
    )

    return SavedComparisonCreateResult(comparison=comparison)


@transaction.atomic
def update_saved_comparison(
    *,
    comparison: SavedComparison,
    selections: list[Any],
    comparable_rows,
    include_quantities: bool = False,
) -> SavedComparisonUpdateResult:
    payload, snapshot_payload = _payload_and_snapshot(
        selections=selections,
        comparable_rows=comparable_rows,
        include_quantities=include_quantities,
    )

    comparison.payload = payload
    comparison.snapshot_payload = snapshot_payload
    comparison.save(update_fields=["payload", "snapshot_payload", "updated_at"])

    return SavedComparisonUpdateResult(comparison=comparison)


@transaction.atomic
def rename_saved_comparison(
    *,
    comparison: SavedComparison,
    name: str,
) -> SavedComparisonRenameResult:
    clean_name = (name or "").strip()

    if not clean_name:
        raise SavedComparisonCommandError("saved_comparison_name_required")

    comparison.name = clean_name
    comparison.save(update_fields=["name", "updated_at"])

    return SavedComparisonRenameResult(comparison=comparison)
