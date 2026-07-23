from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Mapping

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ai_assistant.models import AIPreparedAction
from notas.domain.models import (
    DailyPlan,
    Food,
    Meal,
    NutritionProposal,
    Program,
    ProgramCalendarization,
    SavedComparison,
)


PREPARED_ACTION_TTL = timedelta(minutes=30)


@dataclass(frozen=True)
class PreparedActionSpec:
    action_key: str
    target_type: str
    title: str
    required_arguments: tuple[str, ...] = ()
    destructive: bool = False
    creates_entity: bool = False


PREPARED_ACTION_SPECS = {
    spec.action_key: spec
    for spec in (
        PreparedActionSpec("food.create", "food", "Crear alimento", ("name", "protein", "carbs", "fat"), creates_entity=True),
        PreparedActionSpec("food.update", "food", "Actualizar alimento"),
        PreparedActionSpec("food.delete", "food", "Eliminar alimento", destructive=True),
        PreparedActionSpec("meal.create", "meal", "Crear comida", ("name",), creates_entity=True),
        PreparedActionSpec("meal.rename", "meal", "Renombrar comida", ("name",)),
        PreparedActionSpec("meal.delete", "meal", "Eliminar comida", destructive=True),
        PreparedActionSpec("dailyplan.create", "dailyplan", "Crear plan diario", ("name",), creates_entity=True),
        PreparedActionSpec("dailyplan.rename", "dailyplan", "Renombrar plan diario", ("name",)),
        PreparedActionSpec("dailyplan.delete", "dailyplan", "Eliminar plan diario", destructive=True),
        PreparedActionSpec("program.create", "program", "Crear programa", ("name",), creates_entity=True),
        PreparedActionSpec("program.rename", "program", "Renombrar programa", ("name",)),
        PreparedActionSpec("program.delete", "program", "Eliminar programa", destructive=True),
        PreparedActionSpec("program.add_week", "program", "Agregar semana al programa"),
        PreparedActionSpec("program.duplicate_week", "program", "Duplicar semana del programa", ("week_number",)),
        PreparedActionSpec("program.remove_week", "program", "Eliminar semana del programa", ("week_number",), destructive=True),
        PreparedActionSpec("calendar.pause", "calendarization", "Pausar calendarización"),
        PreparedActionSpec("calendar.resume", "calendarization", "Reanudar calendarización"),
        PreparedActionSpec("calendar.cancel", "calendarization", "Cancelar calendarización", destructive=True),
        PreparedActionSpec("comparison.rename", "saved_comparison", "Renombrar comparación", ("name",)),
        PreparedActionSpec("proposal.approve", "proposal", "Aprobar propuesta"),
        PreparedActionSpec("proposal.reject", "proposal", "Rechazar propuesta", destructive=True),
        PreparedActionSpec("proposal.cancel", "proposal", "Cancelar propuesta", destructive=True),
        PreparedActionSpec("proposal.delete", "proposal", "Eliminar propuesta", destructive=True),
        PreparedActionSpec("proposal.apply", "proposal", "Aplicar propuesta aprobada"),
    )
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
    return {
        "id": str(action.public_id),
        "action_key": action.action_key,
        "title": action.title,
        "summary": action.summary,
        "target_type": action.target_type,
        "target_id": action.target_id,
        "preview": dict(action.preview or {}),
        "destructive": action.destructive,
        "status": action.status,
        "expires_at": action.expires_at.isoformat(),
        "result": dict(action.result or {}),
    }


def _resolve_owned_target(*, user, target_type: str, target_id: int, for_update: bool = False):
    querysets = {
        "food": Food.objects.filter(created_by=user, is_active=True),
        "meal": Meal.objects.filter(created_by=user),
        "dailyplan": DailyPlan.objects.filter(created_by=user),
        "program": Program.objects.filter(created_by=user),
        "calendarization": ProgramCalendarization.objects.filter(user=user),
        "saved_comparison": SavedComparison.objects.filter(owner=user),
        "proposal": NutritionProposal.objects.filter(
            Q(created_by=user) | Q(dailyplan__created_by=user)
        ).distinct(),
    }
    queryset = querysets[target_type]
    if for_update:
        queryset = queryset.select_for_update()
    target = queryset.filter(pk=target_id).first()
    if target is None:
        raise ValueError(f"prepared_action_{target_type}_not_available")
    return target


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

    if key.startswith("meal."):
        from notas.application.services.commands.meal_commands import create_draft_meal, delete_meal, rename_meal
        if key == "meal.create":
            result = create_draft_meal(user=user, name=arguments["name"])
            return {"meal_id": result.meal.id, "meal_name": result.meal.name}
        if key == "meal.rename":
            result = rename_meal(meal=target, name=arguments["name"])
            return {"meal_id": result.meal.id, "meal_name": result.meal.name}
        result = delete_meal(meal=target)
        return {"meal_id": result.meal_id}

    if key.startswith("dailyplan."):
        from notas.application.services.commands.dailyplan_commands import create_draft_dailyplan, delete_dailyplan, rename_dailyplan
        if key == "dailyplan.create":
            result = create_draft_dailyplan(user=user, name=arguments["name"])
            return {"dailyplan_id": result.dailyplan.id, "dailyplan_name": result.dailyplan.name}
        if key == "dailyplan.rename":
            result = rename_dailyplan(dailyplan=target, name=arguments["name"])
            return {"dailyplan_id": result.dailyplan.id, "dailyplan_name": result.dailyplan.name}
        result = delete_dailyplan(dailyplan=target)
        return {"dailyplan_id": result.dailyplan_id}

    if key.startswith("program."):
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

    if key.startswith("calendar."):
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

    if key == "comparison.rename":
        from notas.application.services.commands.saved_comparison_commands import rename_saved_comparison
        result = rename_saved_comparison(comparison=target, name=arguments["name"])
        return {"comparison_id": result.comparison.id, "name": result.comparison.name}

    if key.startswith("proposal."):
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

    raise ValueError("prepared_action_unsupported")
