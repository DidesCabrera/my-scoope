"""Audit and retire duplicate global Food Catalog snapshots.

Retirement keeps historical food IDs and their nutrition values intact. Private
foods are deliberately outside this operation.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import Lower, Trim

from notas.application.services.food_catalog_snapshots import get_catalog_food_refs_by_id
from notas.domain.models import Food


@dataclass(frozen=True)
class DuplicateSnapshotGroup:
    catalog_food_id: int | None
    catalog_food_ref: str | None
    survivor_id: int
    retired_ids: tuple[int, ...]


@dataclass(frozen=True)
class FoodDuplicateAudit:
    groups: tuple[DuplicateSnapshotGroup, ...]
    conflicts: tuple[str, ...]
    possible_name_duplicates: tuple[tuple[str, int], ...]
    retired_count: int = 0


def _snapshot_groups(foods: list[Food]) -> tuple[list[DuplicateSnapshotGroup], list[str]]:
    parent = {food.pk: food.pk for food in foods}
    by_id: dict[int, int] = {}
    by_ref: dict[str, int] = {}

    def root(pk: int) -> int:
        while parent[pk] != pk:
            parent[pk] = parent[parent[pk]]
            pk = parent[pk]
        return pk

    def join(left: int, right: int) -> None:
        parent[root(right)] = root(left)

    for food in foods:
        if food.catalog_food_id is not None:
            if food.catalog_food_id in by_id:
                join(food.pk, by_id[food.catalog_food_id])
            by_id[food.catalog_food_id] = food.pk
        if food.catalog_food_ref is not None:
            ref = str(food.catalog_food_ref)
            if ref in by_ref:
                join(food.pk, by_ref[ref])
            by_ref[ref] = food.pk

    components: dict[int, list[Food]] = {}
    for food in foods:
        components.setdefault(root(food.pk), []).append(food)

    groups: list[DuplicateSnapshotGroup] = []
    conflicts: list[str] = []
    catalog_refs_by_id = get_catalog_food_refs_by_id(
        {food.catalog_food_id for food in foods if food.catalog_food_id is not None}
    )
    for food in foods:
        if (food.catalog_food_id is None) != (food.catalog_food_ref is None):
            conflicts.append(f"Food ID {food.pk} has an incomplete catalog ID/ref pair")
        elif food.catalog_food_id is not None:
            catalog_ref = catalog_refs_by_id.get(food.catalog_food_id)
            if catalog_ref is None or catalog_ref != food.catalog_food_ref:
                conflicts.append(f"Food ID {food.pk} has a missing or mismatched CatalogFood")
    for members in components.values():
        if len(members) < 2:
            continue
        ids = {food.catalog_food_id for food in members if food.catalog_food_id is not None}
        refs = {str(food.catalog_food_ref) for food in members if food.catalog_food_ref is not None}
        if len(ids) > 1 or len(refs) > 1:
            conflicts.append(f"Food IDs {[food.pk for food in members]} have conflicting catalog identities")
            continue
        catalog_id = next(iter(ids), None)
        catalog_ref = next(iter(refs), None)
        if catalog_id is not None and catalog_ref is not None and str(
            catalog_refs_by_id.get(catalog_id)
        ) != catalog_ref:
            conflicts.append(f"Food IDs {[food.pk for food in members]} have a mismatched catalog ID/ref")
            continue
        members.sort(
            key=lambda food: (
                not food.is_active,
                food.catalog_food_id is None or food.catalog_food_ref is None,
                food.catalog_sync_status != Food.CATALOG_SYNC_SNAPSHOT,
                not food.is_verified,
                -food.data_quality_score,
                food.pk,
            )
        )
        groups.append(
            DuplicateSnapshotGroup(
                catalog_food_id=catalog_id,
                catalog_food_ref=catalog_ref,
                survivor_id=members[0].pk,
                retired_ids=tuple(food.pk for food in members[1:]),
            )
        )
    return sorted(groups, key=lambda group: group.survivor_id), conflicts


@transaction.atomic
def audit_food_catalog_duplicates(*, apply: bool = False) -> FoodDuplicateAudit:
    foods = list(
        Food.objects.select_for_update()
        .filter(is_global=True)
        .filter(Q(catalog_food_id__isnull=False) | Q(catalog_food_ref__isnull=False))
        .only(
            "id", "catalog_food_id", "catalog_food_ref", "is_active", "catalog_sync_status",
            "is_verified", "data_quality_score",
        )
        .order_by("id")
    )
    groups, conflicts = _snapshot_groups(foods)
    possible_names = tuple(
        (row["normalized_name"], row["count"])
        for row in Food.objects.filter(is_global=True, is_active=True)
        .exclude(canonical_name="")
        .annotate(normalized_name=Lower(Trim("canonical_name")))
        .values("normalized_name")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
        .order_by("normalized_name")
    )
    retired_count = 0
    if apply and not conflicts:
        for group in groups:
            retired_count += Food.objects.filter(pk__in=group.retired_ids).update(
                is_active=False,
                catalog_food_id=None,
                catalog_food_ref=None,
                catalog_sync_status=Food.CATALOG_SYNC_UNLINKED,
            )
    return FoodDuplicateAudit(
        groups=tuple(groups),
        conflicts=tuple(conflicts),
        possible_name_duplicates=possible_names,
        retired_count=retired_count,
    )
