from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from django.db import transaction
from django.db.models import Q, Subquery
from django.utils import timezone

from ai_assistant.application.prepared_action_contracts import (
    PREPARED_ACTION_SPECS,
    PREPARED_ACTION_TTL,
    PreparedActionSpec,
)
from ai_assistant.models import AIPreparedAction
from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    Food,
    Meal,
    MealFood,
    NutritionProposal,
    Program,
    ProgramCalendarization,
    SavedComparison,
)

WORKSPACE_PATCH_ACTION_KEY = "workspace.patch"
WORKSPACE_PATCH_CONTRACT_VERSION = "ai_assistant_workspace_patch.v1"
WORKSPACE_PATCH_MAX_OPERATIONS = 24

_WORKSPACE_PATCH_ACTIONS = {
    ("food", "create"): "food.create",
    ("food", "update"): "food.update",
    ("food", "delete"): "food.delete",
    ("meal", "create"): "meal.create",
    ("meal", "rename"): "meal.rename",
    ("meal", "delete"): "meal.delete",
    ("meal", "add_food"): "meal.add_food",
    ("meal", "update_food"): "meal.update_food",
    ("meal", "remove_food"): "meal.remove_food",
    ("dailyplan", "create"): "dailyplan.create",
    ("dailyplan", "rename"): "dailyplan.rename",
    ("dailyplan", "delete"): "dailyplan.delete",
    ("dailyplan", "add_meal"): "dailyplan.add_meal",
    ("dailyplan", "update_meal"): "dailyplan.update_meal",
    ("dailyplan", "remove_meal"): "dailyplan.remove_meal",
    ("program", "create"): "program.create",
    ("program", "rename"): "program.rename",
    ("program", "delete"): "program.delete",
    ("program", "add_week"): "program.add_week",
    ("program", "duplicate_week"): "program.duplicate_week",
    ("program", "remove_week"): "program.remove_week",
    ("calendarization", "pause"): "calendar.pause",
    ("calendarization", "resume"): "calendar.resume",
    ("calendarization", "cancel"): "calendar.cancel",
    ("saved_comparison", "rename"): "comparison.rename",
    ("proposal", "approve"): "proposal.approve",
    ("proposal", "reject"): "proposal.reject",
    ("proposal", "cancel"): "proposal.cancel",
    ("proposal", "delete"): "proposal.delete",
    ("proposal", "apply"): "proposal.apply",
}

_MEDIUM_RISK_ACTIONS = {
    "calendar.pause",
    "calendar.resume",
    "proposal.approve",
    "proposal.apply",
}

_ALLOWED_ACTION_ARGUMENTS = {
    "food.create": {"name", "protein", "carbs", "fat"},
    "food.update": {"name", "protein", "carbs", "fat"},
    "meal.create": {"name"},
    "meal.rename": {"name"},
    "meal.add_food": {"food_id", "quantity"},
    "meal.update_food": {"food_id", "quantity"},
    # Public workspace patches identify a removal using the owned meal plus
    # the food that appears in it. The join-row id is an implementation detail
    # and must not leak into assistant or MCP requests.
    "meal.remove_food": {"food_id"},
    "dailyplan.create": {"name"},
    "dailyplan.rename": {"name"},
    "dailyplan.add_meal": {"meal_id", "hour", "note"},
    "dailyplan.update_meal": {"meal_id", "hour", "note"},
    "program.create": {"name", "duration_weeks"},
    "program.rename": {"name"},
    "program.duplicate_week": {"week_number"},
    "program.remove_week": {"week_number"},
}

_REFERENCEABLE_ARGUMENTS = {
    "meal.add_food": {"food_id": "food"},
    "dailyplan.add_meal": {"meal_id": "meal"},
}


def prepare_product_action(
    *,
    user,
    action_key: str,
    target_id: int | None = None,
    parameters: Mapping[str, Any] | None = None,
) -> AIPreparedAction:
    normalized_key = str(action_key or "").strip().lower()
    spec = PREPARED_ACTION_SPECS.get(normalized_key)
    if spec is None:
        raise ValueError("prepared_action_unsupported")
    arguments = dict(parameters or {})
    missing = [
        key
        for key in spec.required_arguments
        if arguments.get(key) is None or str(arguments.get(key)).strip() == ""
    ]
    if missing:
        raise ValueError(f"prepared_action_missing_arguments:{','.join(missing)}")

    target = None
    before = {}
    target_version = ""
    if not spec.creates_entity:
        if target_id is None:
            raise ValueError("prepared_action_target_required")
        target = _resolve_owned_target(
            user=user,
            target_type=spec.target_type,
            target_id=target_id,
        )
        before = _target_snapshot(spec.target_type, target)
        target_version = _snapshot_version(before)

    after = _preview_after(spec, before=before, arguments=arguments)
    summary = _build_summary(spec, before=before, after=after)
    return AIPreparedAction.objects.create(
        user=user,
        action_key=spec.action_key,
        title=spec.title,
        summary=summary,
        target_type=spec.target_type,
        target_id=getattr(target, "id", None),
        target_version=target_version,
        arguments=arguments,
        preview={
            "before": before,
            "after": after,
            "writes_applied": False,
            "requires_explicit_confirmation": True,
        },
        destructive=spec.destructive,
        expires_at=timezone.now() + PREPARED_ACTION_TTL,
    )


def prepare_workspace_patch(
    *,
    user,
    title: str,
    summary: str,
    operations: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
) -> AIPreparedAction:
    """Prepare an atomic multi-operation patch without mutating product state."""

    raw_operations = tuple(operations or ())
    if not raw_operations:
        raise ValueError("workspace_patch_requires_operations")
    if len(raw_operations) > WORKSPACE_PATCH_MAX_OPERATIONS:
        raise ValueError("workspace_patch_too_many_operations")

    normalized_operations = []
    operation_ids: set[str] = set()
    prior_operations: dict[str, dict[str, Any]] = {}
    aggregate_risk = "low"
    for index, raw_operation in enumerate(raw_operations, start=1):
        operation = _normalize_workspace_patch_operation(
            user=user,
            raw_operation=raw_operation,
            fallback_operation_id=f"operation_{index}",
            prior_operations=prior_operations,
        )
        operation_id = operation["operation_id"]
        if operation_id in operation_ids:
            raise ValueError("workspace_patch_duplicate_operation_id")
        operation_ids.add(operation_id)
        normalized_operations.append(operation)
        prior_operations[operation_id] = operation
        aggregate_risk = _highest_risk(aggregate_risk, operation["risk_level"])

    clean_title = " ".join(str(title or "").split())[:180]
    clean_summary = " ".join(str(summary or "").split())[:1000]
    if not clean_title:
        raise ValueError("workspace_patch_title_required")
    if not clean_summary:
        clean_summary = f"{len(normalized_operations)} cambios preparados para revisión."

    return AIPreparedAction.objects.create(
        user=user,
        action_key=WORKSPACE_PATCH_ACTION_KEY,
        title=clean_title,
        summary=clean_summary,
        target_type="workspace",
        arguments={
            "contract_version": WORKSPACE_PATCH_CONTRACT_VERSION,
            "operations": normalized_operations,
        },
        preview={
            "contract_version": WORKSPACE_PATCH_CONTRACT_VERSION,
            "operations": [
                {
                    "operation_id": operation["operation_id"],
                    "action_key": operation["action_key"],
                    "title": operation["title"],
                    "before": operation["before"],
                    "after": operation["after"],
                    "risk_level": operation["risk_level"],
                    "references": operation["references"],
                }
                for operation in normalized_operations
            ],
            "operation_count": len(normalized_operations),
            "risk_level": aggregate_risk,
            "writes_applied": False,
            "requires_explicit_confirmation": True,
            "approval_policy": {
                "decision": "confirm_in_trusted_ui",
                "reason": "workspace_patch_v1_requires_confirmation",
                "future_auto_apply_eligible": aggregate_risk == "low",
            },
        },
        destructive=aggregate_risk == "high",
        expires_at=timezone.now() + PREPARED_ACTION_TTL,
    )


@transaction.atomic
def commit_prepared_action(*, user, public_id) -> AIPreparedAction:
    action = (
        AIPreparedAction.objects
        .select_for_update()
        .filter(public_id=public_id, user=user)
        .first()
    )
    if action is None:
        raise ValueError("prepared_action_not_found")
    if action.status != AIPreparedAction.Status.PREPARED:
        raise ValueError("prepared_action_not_pending")
    if action.is_expired:
        action.status = AIPreparedAction.Status.EXPIRED
        action.save(update_fields=["status", "updated_at"])
        raise ValueError("prepared_action_expired")

    if action.action_key == WORKSPACE_PATCH_ACTION_KEY:
        return _commit_workspace_patch_action(action=action, user=user)

    spec = PREPARED_ACTION_SPECS.get(action.action_key)
    if spec is None:
        raise ValueError("prepared_action_unsupported")
    target = None
    if not spec.creates_entity:
        target = _resolve_owned_target(
            user=user,
            target_type=spec.target_type,
            target_id=action.target_id,
            for_update=True,
        )
        current_version = _snapshot_version(_target_snapshot(spec.target_type, target))
        if current_version != action.target_version:
            raise ValueError("prepared_action_target_changed")

    try:
        result = _dispatch_commit(
            spec,
            user=user,
            target=target,
            arguments=dict(action.arguments or {}),
        )
    except Exception:
        action.status = AIPreparedAction.Status.FAILED
        action.save(update_fields=["status", "updated_at"])
        raise

    action.status = AIPreparedAction.Status.COMMITTED
    action.result = result
    action.committed_at = timezone.now()
    action.save(update_fields=["status", "result", "committed_at", "updated_at"])
    return action


def cancel_prepared_action(*, user, public_id) -> AIPreparedAction:
    action = AIPreparedAction.objects.filter(public_id=public_id, user=user).first()
    if action is None:
        raise ValueError("prepared_action_not_found")
    if action.status != AIPreparedAction.Status.PREPARED:
        raise ValueError("prepared_action_not_pending")
    action.status = AIPreparedAction.Status.CANCELLED
    action.save(update_fields=["status", "updated_at"])
    return action


def serialize_prepared_action(action: AIPreparedAction) -> dict:
    preview = dict(action.preview or {})
    return {
        "id": str(action.public_id),
        "action_key": action.action_key,
        "title": action.title,
        "summary": action.summary,
        "target_type": action.target_type,
        "target_id": action.target_id,
        "preview": preview,
        "risk_level": str(preview.get("risk_level") or ("high" if action.destructive else "medium")),
        "approval_policy": dict(preview.get("approval_policy") or {}),
        "destructive": action.destructive,
        "status": action.status,
        "expires_at": action.expires_at.isoformat(),
        "result": dict(action.result or {}),
    }


def _normalize_workspace_patch_operation(
    *,
    user,
    raw_operation: Mapping[str, Any],
    fallback_operation_id: str,
    prior_operations: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(raw_operation, Mapping):
        raise ValueError("workspace_patch_operation_invalid")
    resource = str(raw_operation.get("resource") or "").strip().lower()
    action = str(raw_operation.get("action") or "").strip().lower()
    action_key = _WORKSPACE_PATCH_ACTIONS.get((resource, action))
    if action_key is None:
        raise ValueError(f"workspace_patch_operation_unsupported:{resource}.{action}")
    spec = PREPARED_ACTION_SPECS[action_key]
    operation_id = (
        "_".join(str(raw_operation.get("operation_id") or fallback_operation_id).strip().split())[:80]
        or fallback_operation_id
    )
    parameters = dict(raw_operation.get("parameters") or {})
    raw_references = raw_operation.get("references") or {}
    if not isinstance(raw_references, Mapping):
        raise ValueError("workspace_patch_references_invalid")
    references = {
        str(key).strip(): str(value).strip()
        for key, value in raw_references.items()
        if value is not None and str(key).strip() and str(value).strip()
    }
    # Provider-native strict schemas require nullable reference fields on every
    # operation. If the provider redundantly fills one while also supplying the
    # concrete public ID, the explicit ID is safer and ownership-validated.
    # Normalize that harmless redundancy instead of rejecting an otherwise
    # deterministic patch (notably remove_food + add_food replacements).
    if raw_operation.get("target_id") is not None:
        references.pop("target_id", None)
    for parameter_name in parameters:
        references.pop(str(parameter_name), None)
    allowed_arguments = _ALLOWED_ACTION_ARGUMENTS.get(action_key, set())
    unknown_arguments = sorted(set(parameters).difference(allowed_arguments))
    if unknown_arguments:
        raise ValueError(f"workspace_patch_unknown_arguments:{','.join(unknown_arguments)}")
    allowed_references = {"target_id", *_REFERENCEABLE_ARGUMENTS.get(action_key, {})}
    unknown_references = sorted(set(references).difference(allowed_references))
    if unknown_references:
        raise ValueError(f"workspace_patch_unknown_references:{','.join(unknown_references)}")
    _validate_workspace_patch_references(
        spec=spec,
        action_key=action_key,
        references=references,
        prior_operations=prior_operations,
    )
    missing = [
        key
        for key in spec.required_arguments
        if key not in references
        and (parameters.get(key) is None or str(parameters.get(key)).strip() == "")
    ]
    if missing:
        raise ValueError(f"prepared_action_missing_arguments:{','.join(missing)}")

    target = None
    before = {}
    target_version = ""
    target_id = raw_operation.get("target_id")
    target_reference = references.get("target_id")
    if not spec.creates_entity:
        if target_id is not None and target_reference:
            raise ValueError("workspace_patch_target_reference_conflict")
        if target_id is None and not target_reference:
            raise ValueError("prepared_action_target_required")
        if target_reference:
            before = {
                "target_type": spec.target_type,
                "pending_operation_reference": target_reference,
            }
        else:
            if action_key == "meal.remove_food":
                target = _resolve_owned_meal_food(
                    user=user,
                    meal_id=int(target_id),
                    food_id=parameters.get("food_id"),
                )
            else:
                target = _resolve_owned_target(
                    user=user,
                    target_type=spec.target_type,
                    target_id=int(target_id),
                )
            before = _target_snapshot(spec.target_type, target)
            target_version = _snapshot_version(before)

    preview_arguments = dict(parameters)
    preview_arguments.update(
        {
            key: {"operation_reference": reference}
            for key, reference in references.items()
            if key != "target_id"
        }
    )

    return {
        "operation_id": operation_id,
        "resource": resource,
        "action": action,
        "action_key": action_key,
        "title": spec.title,
        "target_type": spec.target_type,
        "target_id": getattr(target, "id", None),
        "target_version": target_version,
        "parameters": parameters,
        "references": references,
        "before": before,
        "after": _preview_after(spec, before=before, arguments=preview_arguments),
        "risk_level": _workspace_patch_risk(spec),
    }


def _validate_workspace_patch_references(
    *,
    spec: PreparedActionSpec,
    action_key: str,
    references: Mapping[str, str],
    prior_operations: Mapping[str, Mapping[str, Any]],
) -> None:
    if spec.creates_entity and "target_id" in references:
        raise ValueError("workspace_patch_create_target_reference_invalid")
    expected_types = {
        "target_id": spec.target_type,
        **_REFERENCEABLE_ARGUMENTS.get(action_key, {}),
    }
    for field_name, reference_id in references.items():
        referenced = prior_operations.get(reference_id)
        if referenced is None:
            raise ValueError(f"workspace_patch_reference_not_available:{reference_id}")
        referenced_spec = PREPARED_ACTION_SPECS.get(str(referenced.get("action_key") or ""))
        if referenced_spec is None or not referenced_spec.creates_entity:
            raise ValueError(f"workspace_patch_reference_not_create:{reference_id}")
        if referenced_spec.target_type != expected_types[field_name]:
            raise ValueError(f"workspace_patch_reference_type_mismatch:{field_name}")


def _commit_workspace_patch_action(*, action: AIPreparedAction, user) -> AIPreparedAction:
    arguments = dict(action.arguments or {})
    if arguments.get("contract_version") != WORKSPACE_PATCH_CONTRACT_VERSION:
        raise ValueError("workspace_patch_contract_unsupported")
    operations = tuple(arguments.get("operations") or ())
    if not operations:
        raise ValueError("workspace_patch_requires_operations")

    direct_targets: dict[str, Any] = {}
    operation_specs: dict[str, PreparedActionSpec] = {}
    prior_operations: dict[str, Mapping[str, Any]] = {}
    for operation in operations:
        spec = PREPARED_ACTION_SPECS.get(str(operation.get("action_key") or ""))
        if spec is None:
            raise ValueError("workspace_patch_operation_unsupported")
        operation_id = str(operation.get("operation_id") or "")
        references = dict(operation.get("references") or {})
        _validate_workspace_patch_references(
            spec=spec,
            action_key=spec.action_key,
            references=references,
            prior_operations=prior_operations,
        )
        target = None
        if not spec.creates_entity and "target_id" not in references:
            target = _resolve_owned_target(
                user=user,
                target_type=spec.target_type,
                target_id=int(operation.get("target_id")),
                for_update=True,
            )
            current_version = _snapshot_version(_target_snapshot(spec.target_type, target))
            if current_version != str(operation.get("target_version") or ""):
                raise ValueError("prepared_action_target_changed")
            direct_targets[operation_id] = target
        operation_specs[operation_id] = spec
        prior_operations[operation_id] = operation

    results = []
    results_by_operation: dict[str, dict[str, Any]] = {}
    try:
        for operation in operations:
            operation_id = str(operation["operation_id"])
            spec = operation_specs[operation_id]
            references = dict(operation.get("references") or {})
            target = direct_targets.get(operation_id)
            target_reference = references.get("target_id")
            if target_reference:
                target_id = _referenced_entity_id(
                    operation_id=target_reference,
                    target_type=spec.target_type,
                    results_by_operation=results_by_operation,
                )
                target = _resolve_owned_target(
                    user=user,
                    target_type=spec.target_type,
                    target_id=target_id,
                    for_update=True,
                )
            resolved_arguments = dict(operation.get("parameters") or {})
            for field_name, reference_id in references.items():
                if field_name == "target_id":
                    continue
                target_type = _REFERENCEABLE_ARGUMENTS[spec.action_key][field_name]
                resolved_arguments[field_name] = _referenced_entity_id(
                    operation_id=reference_id,
                    target_type=target_type,
                    results_by_operation=results_by_operation,
                )
            result = _dispatch_commit(
                spec,
                user=user,
                target=target,
                arguments=resolved_arguments,
            )
            results_by_operation[operation_id] = result
            results.append({
                "operation_id": operation_id,
                "action_key": operation["action_key"],
                "result": result,
            })
    except Exception:
        action.status = AIPreparedAction.Status.FAILED
        action.save(update_fields=["status", "updated_at"])
        raise

    action.status = AIPreparedAction.Status.COMMITTED
    action.result = {
        "contract_version": WORKSPACE_PATCH_CONTRACT_VERSION,
        "operation_count": len(results),
        "operations": results,
        "atomic": True,
    }
    action.committed_at = timezone.now()
    action.save(update_fields=["status", "result", "committed_at", "updated_at"])
    return action


def _referenced_entity_id(
    *,
    operation_id: str,
    target_type: str,
    results_by_operation: Mapping[str, Mapping[str, Any]],
) -> int:
    result = results_by_operation.get(operation_id)
    if result is None:
        raise ValueError(f"workspace_patch_reference_result_missing:{operation_id}")
    result_key = f"{target_type}_id"
    value = result.get(result_key)
    if value is None:
        raise ValueError(f"workspace_patch_reference_result_invalid:{operation_id}")
    return int(value)


def _workspace_patch_risk(spec: PreparedActionSpec) -> str:
    if spec.destructive:
        return "high"
    if spec.action_key in _MEDIUM_RISK_ACTIONS:
        return "medium"
    return "low"


def _highest_risk(left: str, right: str) -> str:
    order = {"low": 0, "medium": 1, "high": 2}
    return left if order[left] >= order[right] else right


def _resolve_owned_target(*, user, target_type: str, target_id: int, for_update: bool = False):
    owned_proposal_ids = NutritionProposal.objects.filter(
        Q(created_by=user) | Q(dailyplan__created_by=user)
    ).values("pk")
    querysets = {
        "food": Food.objects.filter(created_by=user, is_active=True),
        "meal": Meal.objects.filter(created_by=user),
        "meal_food": MealFood.objects.filter(meal__created_by=user).select_related("meal", "food"),
        "dailyplan": DailyPlan.objects.filter(created_by=user),
        "dailyplan_meal": DailyPlanMeal.objects.filter(dailyplan__created_by=user).select_related("dailyplan", "meal"),
        "program": Program.objects.filter(created_by=user),
        "calendarization": ProgramCalendarization.objects.filter(user=user),
        "saved_comparison": SavedComparison.objects.filter(owner=user),
        "proposal": NutritionProposal.objects.filter(pk__in=Subquery(owned_proposal_ids)),
    }
    queryset = querysets[target_type]
    if for_update:
        queryset = queryset.select_for_update()
    target = queryset.filter(pk=target_id).first()
    if target is None:
        raise ValueError(f"prepared_action_{target_type}_not_available")
    return target


def _resolve_owned_meal_food(*, user, meal_id: int, food_id: Any):
    """Resolve a meal-food row without exposing its internal id to callers."""

    try:
        normalized_food_id = int(food_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("prepared_action_missing_arguments:food_id") from exc
    matches = MealFood.objects.filter(
        meal_id=meal_id,
        meal__created_by=user,
        food_id=normalized_food_id,
    ).select_related("meal", "food")
    count = matches.count()
    if count == 0:
        raise ValueError("prepared_action_meal_food_not_available")
    if count > 1:
        raise ValueError("prepared_action_meal_food_ambiguous")
    return matches.first()


def _target_snapshot(target_type: str, target) -> dict:
    if target_type == "food":
        return {
            "id": target.id,
            "name": target.name,
            "protein": float(target.protein),
            "carbs": float(target.carbs),
            "fat": float(target.fat),
            "is_active": target.is_active,
        }
    if target_type in {"meal", "dailyplan", "program"}:
        payload = {"id": target.id, "name": target.name, "is_draft": target.is_draft}
        if target_type == "program":
            payload["duration_weeks"] = target.normalized_duration_weeks
        if target_type == "dailyplan":
            payload["is_public"] = target.is_public
        return payload
    if target_type == "meal_food":
        return {
            "id": target.id,
            "meal_id": target.meal_id,
            "food_id": target.food_id,
            "food_name": target.food.name,
            "quantity": float(target.quantity),
        }
    if target_type == "dailyplan_meal":
        return {
            "id": target.id,
            "dailyplan_id": target.dailyplan_id,
            "meal_id": target.meal_id,
            "meal_name": target.meal.name,
            "hour": target.hour.isoformat() if target.hour else None,
            "note": target.note or "",
        }
    if target_type == "calendarization":
        return {
            "id": target.id,
            "program_name": target.program_name_snapshot,
            "status": target.status,
            "daily_notifications_enabled": target.daily_notifications_enabled,
            "meal_notifications_enabled": target.meal_notifications_enabled,
        }
    if target_type == "saved_comparison":
        return {"id": target.id, "name": target.name, "kind": target.kind}
    if target_type == "proposal":
        return {
            "id": target.id,
            "title": target.title,
            "status": target.status,
            "dailyplan_id": target.dailyplan_id,
            "intent": str((target.proposed_payload or {}).get("intent") or ""),
        }
    raise ValueError("prepared_action_target_type_unsupported")


def _preview_after(spec: PreparedActionSpec, *, before: dict, arguments: dict) -> dict:
    if spec.creates_entity:
        return {"will_create": spec.target_type, **arguments}
    if spec.action_key.endswith(".rename"):
        return {**before, "name": str(arguments["name"]).strip()}
    if spec.action_key == "food.update":
        allowed = {"name", "protein", "carbs", "fat"}
        updates = {key: arguments[key] for key in allowed if key in arguments}
        if not updates:
            raise ValueError("prepared_action_update_requires_changes")
        return {**before, **updates}
    if spec.action_key == "meal.add_food":
        return {**before, "will_add_food": dict(arguments)}
    if spec.action_key == "meal.update_food":
        return {
            **before,
            "food_id": arguments.get("food_id", before["food_id"]),
            "quantity": arguments["quantity"],
        }
    if spec.action_key == "dailyplan.add_meal":
        return {**before, "will_add_meal": dict(arguments)}
    if spec.action_key == "dailyplan.update_meal":
        updates = {key: arguments[key] for key in ("meal_id", "hour", "note") if key in arguments}
        if not updates:
            raise ValueError("prepared_action_update_requires_changes")
        return {**before, **updates}
    if spec.action_key == "program.add_week":
        return {**before, "duration_weeks": int(before["duration_weeks"]) + 1}
    if spec.action_key == "program.duplicate_week":
        return {
            **before,
            "duration_weeks": int(before["duration_weeks"]) + 1,
            "duplicates_week": int(arguments["week_number"]),
        }
    if spec.action_key == "program.remove_week":
        return {
            **before,
            "duration_weeks": max(int(before["duration_weeks"]) - 1, 1),
            "removes_week": int(arguments["week_number"]),
        }
    status_updates = {
        "calendar.pause": "paused",
        "calendar.resume": "active_or_scheduled",
        "calendar.cancel": "cancelled",
        "proposal.approve": "approved",
        "proposal.reject": "rejected",
        "proposal.cancel": "cancelled",
        "proposal.apply": "applied",
    }
    if spec.action_key in status_updates:
        return {**before, "status": status_updates[spec.action_key]}
    if spec.destructive:
        return {**before, "will_be_deleted": True}
    return dict(before)


def _build_summary(spec: PreparedActionSpec, *, before: dict, after: dict) -> str:
    if spec.creates_entity:
        return f"{spec.title}: {after.get('name') or spec.target_type}."
    target_name = before.get("name") or before.get("title") or before.get("program_name") or before.get("id")
    if spec.destructive:
        return f"{spec.title}: {target_name}. Esta acción es destructiva y requiere confirmación."
    return f"{spec.title}: {target_name}. No se aplicó ningún cambio todavía."


def _snapshot_version(snapshot: dict) -> str:
    payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _dispatch_commit(spec: PreparedActionSpec, *, user, target, arguments: dict) -> dict:
    key = spec.action_key
    if key.startswith("food."):
        return _dispatch_food_commit(key=key, user=user, target=target, arguments=arguments)

    if key.startswith("meal."):
        return _dispatch_meal_commit(key=key, user=user, target=target, arguments=arguments)

    if key.startswith("dailyplan."):
        return _dispatch_dailyplan_commit(key=key, user=user, target=target, arguments=arguments)

    if key.startswith("program."):
        return _dispatch_program_commit(key=key, user=user, target=target, arguments=arguments)

    if key.startswith("calendar."):
        return _dispatch_calendar_commit(key=key, user=user, target=target)

    if key == "comparison.rename":
        from notas.application.services.commands.saved_comparison_commands import rename_saved_comparison
        result = rename_saved_comparison(comparison=target, name=arguments["name"])
        return {"comparison_id": result.comparison.id, "name": result.comparison.name}

    if key.startswith("proposal."):
        return _dispatch_proposal_commit(key=key, user=user, target=target)

    raise ValueError("prepared_action_unsupported")


def _dispatch_food_commit(*, key: str, user, target, arguments: dict) -> dict:
    from notas.application.services.commands.food_commands import create_food, delete_food, update_food

    if key == "food.create":
        result = create_food(user=user, **arguments)
        return {"food_id": result.food.id, "food_name": result.food.name}
    if key == "food.update":
        values = {
            "name": arguments.get("name", target.name),
            "protein": arguments.get("protein", target.protein),
            "carbs": arguments.get("carbs", target.carbs),
            "fat": arguments.get("fat", target.fat),
        }
        result = update_food(food=target, **values)
        return {"food_id": result.food.id, "food_name": result.food.name}
    result = delete_food(food=target)
    return {"food_id": result.food_id}


def _dispatch_meal_commit(*, key: str, user, target, arguments: dict) -> dict:
    from notas.application.queries.read_boundaries import get_readable_food_queryset
    from notas.application.services.commands.meal_commands import (
        create_draft_meal,
        create_meal_food,
        delete_meal,
        delete_meal_food,
        rename_meal,
        update_meal_food,
    )

    if key == "meal.create":
        result = create_draft_meal(user=user, name=arguments["name"])
        return {"meal_id": result.meal.id, "meal_name": result.meal.name}
    if key == "meal.rename":
        result = rename_meal(meal=target, name=arguments["name"])
        return {"meal_id": result.meal.id, "meal_name": result.meal.name}
    if key == "meal.add_food":
        food = get_readable_food_queryset(user).filter(pk=arguments["food_id"]).first()
        if food is None:
            raise ValueError("prepared_action_food_not_available")
        result = create_meal_food(meal=target, food=food, quantity=arguments["quantity"])
        return {"meal_id": result.meal.id, "meal_food_id": result.meal_food.id}
    if key == "meal.update_food":
        if arguments.get("food_id") is not None:
            food_available = get_readable_food_queryset(user).filter(pk=arguments["food_id"]).exists()
            if not food_available:
                raise ValueError("prepared_action_food_not_available")
        result = update_meal_food(
            meal_food=target,
            quantity=arguments["quantity"],
            food_id=arguments.get("food_id"),
        )
        return {"meal_id": result.meal.id, "meal_food_id": result.meal_food.id}
    if key == "meal.remove_food":
        result = delete_meal_food(meal_food=target)
        return {"meal_id": result.meal.id, "meal_food_id": result.meal_food_id}
    result = delete_meal(meal=target)
    return {"meal_id": result.meal_id}


def _dispatch_dailyplan_commit(*, key: str, user, target, arguments: dict) -> dict:
    from notas.application.services.commands.dailyplan_commands import (
        add_existing_meal_to_dailyplan,
        create_draft_dailyplan,
        delete_dailyplan,
        remove_dailyplan_meal,
        rename_dailyplan,
        update_dailyplan_meal,
    )

    if key == "dailyplan.create":
        result = create_draft_dailyplan(user=user, name=arguments["name"])
        return {"dailyplan_id": result.dailyplan.id, "dailyplan_name": result.dailyplan.name}
    if key == "dailyplan.rename":
        result = rename_dailyplan(dailyplan=target, name=arguments["name"])
        return {"dailyplan_id": result.dailyplan.id, "dailyplan_name": result.dailyplan.name}
    if key == "dailyplan.add_meal":
        meal = _resolve_owned_target(user=user, target_type="meal", target_id=int(arguments["meal_id"]))
        result = add_existing_meal_to_dailyplan(
            dailyplan=target,
            meal=meal,
            user=user,
            hour=arguments.get("hour"),
            note=arguments.get("note"),
        )
        return {"dailyplan_id": result.dailyplan.id, "dailyplan_meal_id": result.dailyplan_meal.id}
    if key == "dailyplan.update_meal":
        result = update_dailyplan_meal(
            dailyplan_meal=target,
            user=user,
            meal_id=arguments.get("meal_id"),
            hour=arguments.get("hour"),
            note=arguments.get("note"),
        )
        return {"dailyplan_id": result.dailyplan.id, "dailyplan_meal_id": result.dailyplan_meal.id}
    if key == "dailyplan.remove_meal":
        result = remove_dailyplan_meal(dailyplan_meal=target)
        return {"dailyplan_id": result.dailyplan.id, "dailyplan_meal_id": result.dailyplan_meal_id}
    result = delete_dailyplan(dailyplan=target)
    return {"dailyplan_id": result.dailyplan_id}


def _dispatch_program_commit(*, key: str, user, target, arguments: dict) -> dict:
    from notas.application.services.commands.program_commands import (
        add_week_to_program,
        create_weekly_program,
        delete_program,
        duplicate_week_in_program,
        remove_week_from_program,
        rename_program,
    )

    if key == "program.create":
        result = create_weekly_program(
            user=user,
            name=arguments["name"],
            duration_weeks=arguments.get("duration_weeks"),
        )
        return {"program_id": result.program.id, "program_name": result.program.name}
    if key == "program.rename":
        program = rename_program(program=target, name=arguments["name"])
        return {"program_id": program.id, "program_name": program.name}
    if key == "program.add_week":
        program = add_week_to_program(program=target)
        return {"program_id": program.id, "duration_weeks": program.normalized_duration_weeks}
    if key == "program.duplicate_week":
        result = duplicate_week_in_program(program=target, week_number=arguments["week_number"], user=user)
        return {"program_id": result.program.id, "new_week_number": result.new_week_number}
    if key == "program.remove_week":
        result = remove_week_from_program(program=target, week_number=arguments["week_number"])
        return {"program_id": result.program.id, "removed_week_number": result.removed_week_number}
    return {"program_id": delete_program(program=target)}


def _dispatch_calendar_commit(*, key: str, user, target) -> dict:
    from notas.application.services.commands.calendarization_commands import (
        cancel_calendarization,
        pause_calendarization,
        resume_calendarization,
    )

    command = {
        "calendar.pause": pause_calendarization,
        "calendar.resume": resume_calendarization,
        "calendar.cancel": cancel_calendarization,
    }[key]
    calendarization = command(user=user, calendarization_id=target.id)
    return {"calendarization_id": calendarization.id, "status": calendarization.status}


def _dispatch_proposal_commit(*, key: str, user, target) -> dict:
    from notas.application.services.commands.proposal_commands import (
        apply_approved_create_dailyplan_proposal,
        apply_approved_create_meal_proposal,
        apply_approved_proposal,
        approve_proposal,
        cancel_proposal,
        delete_proposal,
        reject_proposal,
    )

    if key == "proposal.approve":
        result = approve_proposal(user=user, proposal=target)
        return {"proposal_id": result.proposal.id, "status": result.proposal.status}
    if key == "proposal.reject":
        result = reject_proposal(user=user, proposal=target)
        return {"proposal_id": result.proposal.id, "status": result.proposal.status}
    if key == "proposal.cancel":
        result = cancel_proposal(user=user, proposal=target)
        return {"proposal_id": result.proposal.id, "status": result.proposal.status}
    if key == "proposal.delete":
        proposal_id = target.id
        delete_proposal(user=user, proposal=target)
        return {"proposal_id": proposal_id}
    intent = str((target.proposed_payload or {}).get("intent") or "")
    if intent == "create_meal":
        result = apply_approved_create_meal_proposal(user=user, proposal=target)
    elif intent == "create_dailyplan":
        result = apply_approved_create_dailyplan_proposal(user=user, proposal=target)
    else:
        result = apply_approved_proposal(user=user, proposal=target)
    return result.as_dict()
