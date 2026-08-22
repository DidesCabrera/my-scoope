from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.db import transaction

from email_delivery.services import deliver_share_invitation
from mobile_api.errors import MobileAPIError
from notas.application.services.access.capabilities import get_capabilities
from notas.application.services.commands.dailyplan_commands import (
    delete_dailyplan,
    fork_dailyplan,
    rename_dailyplan,
)
from notas.application.services.commands.food_commands import delete_food
from notas.application.services.commands.meal_commands import (
    delete_meal,
    fork_meal_for_library,
    rename_meal,
)
from notas.application.services.commands.program_commands import (
    delete_program,
    fork_program,
    rename_program,
)
from notas.application.services.commands.share_commands import (
    create_dailyplan_share,
    create_food_share,
    create_meal_share,
    create_program_share,
)
from notas.application.services.notifications.share_emails import build_share_invitation_email
from notas.domain.models import DailyPlan, Food, Meal, Program

ENTITY_NAMES = {
    "foods": "alimento",
    "meals": "comida",
    "daily-plans": "plan diario",
    "programs": "programa",
}

ACTION_LABELS = {
    "rename": "Renombrar",
    "duplicate": "Duplicar",
    "share": "Compartir",
    "delete": "Eliminar",
}


def _action(key: str) -> dict:
    return {
        "key": key,
        "label": ACTION_LABELS[key],
        "destructive": key == "delete",
    }


def library_actions_payload(item, user, *, context: str) -> list[dict]:
    """Project the same action placement used by the responsive web library."""
    is_owner = item.created_by_id == user.id

    if context == "list":
        if isinstance(item, Food):
            return []
        if isinstance(item, Program) and not is_owner:
            return [_action("duplicate")] if item.is_forkable else []

        actions = []
        capabilities = get_capabilities(user)
        can_duplicate = isinstance(item, Program) or bool(capabilities and capabilities.can_fork())
        if can_duplicate:
            actions.append(_action("duplicate"))
        if is_owner:
            actions.append(_action("delete"))
        return actions

    if not is_owner:
        if isinstance(item, Program) and item.is_forkable:
            return [_action("duplicate")]
        return []

    if isinstance(item, Food):
        return [_action("share"), _action("delete")]

    actions = [_action("rename")]
    capabilities = get_capabilities(user)
    if isinstance(item, Program) or bool(capabilities and capabilities.can_fork()):
        actions.append(_action("duplicate"))
    actions.extend([_action("share"), _action("delete")])
    return actions


def _available_item(user, entity: str, item_id: int):
    if entity == "foods":
        item = Food.objects.filter(pk=item_id, created_by=user, is_active=True).first()
    elif entity == "meals":
        item = Meal.objects.filter(pk=item_id, created_by=user, is_draft=False).first()
    elif entity == "daily-plans":
        item = DailyPlan.objects.filter(pk=item_id, created_by=user, is_draft=False).first()
    elif entity == "programs":
        item = (
            Program.objects.filter(pk=item_id)
            .filter(Q(created_by=user) | Q(shares__accepted_by=user, shares__removed=False))
            .distinct()
            .first()
        )
    else:
        item = None

    if item is None:
        raise MobileAPIError(
            code="library_item_not_found",
            message="The requested library item was not found.",
            status_code=404,
        )
    return item


def _ensure_allowed(item, user, action: str) -> None:
    if action not in ACTION_LABELS:
        raise MobileAPIError(
            code="library_action_not_supported",
            message="The requested action is not supported.",
            status_code=422,
        )

    is_owner = item.created_by_id == user.id
    if action == "duplicate":
        if isinstance(item, Food):
            allowed = False
        elif isinstance(item, Program):
            allowed = is_owner or item.is_forkable
        else:
            capabilities = get_capabilities(user)
            allowed = is_owner and bool(capabilities and capabilities.can_fork())
    else:
        allowed = is_owner

    if not allowed:
        raise MobileAPIError(
            code="library_action_not_allowed",
            message="The current account cannot perform this action.",
            status_code=403,
        )


def _rename(item, name: str) -> None:
    clean_name = (name or "").strip()
    if not clean_name:
        raise MobileAPIError(
            code="library_name_required",
            message="A name is required.",
            status_code=422,
        )
    if len(clean_name) > 100:
        raise MobileAPIError(
            code="library_name_too_long",
            message="The name is too long.",
            status_code=422,
        )

    if isinstance(item, Meal):
        rename_meal(meal=item, name=clean_name)
    elif isinstance(item, DailyPlan):
        rename_dailyplan(dailyplan=item, name=clean_name)
    elif isinstance(item, Program):
        rename_program(program=item, name=clean_name)
    else:
        raise MobileAPIError(
            code="library_action_not_allowed",
            message="This item cannot be renamed.",
            status_code=403,
        )


def _duplicate(item, user):
    if isinstance(item, Meal):
        return fork_meal_for_library(item, user)
    if isinstance(item, DailyPlan):
        return fork_dailyplan(item, user)
    if isinstance(item, Program):
        return fork_program(item, user)
    raise MobileAPIError(
        code="library_action_not_allowed",
        message="This item cannot be duplicated.",
        status_code=403,
    )


def _delete(item) -> int:
    try:
        if isinstance(item, Food):
            return delete_food(food=item).food_id
        if isinstance(item, Meal):
            return delete_meal(meal=item).meal_id
        if isinstance(item, DailyPlan):
            return delete_dailyplan(dailyplan=item).dailyplan_id
        if isinstance(item, Program):
            return delete_program(program=item)
    except ValueError as exc:
        raise MobileAPIError(
            code="library_delete_blocked",
            message="This item cannot be deleted in its current state.",
            status_code=409,
            details={"reason": str(exc)},
        ) from exc
    raise MobileAPIError(
        code="library_action_not_allowed",
        message="This item cannot be deleted.",
        status_code=403,
    )


def _share(request, item, *, recipient_email: str, subject: str, message: str) -> str:
    clean_email = (recipient_email or "").strip().lower()
    try:
        validate_email(clean_email)
    except ValidationError as exc:
        raise MobileAPIError(
            code="library_share_email_invalid",
            message="A valid recipient email is required.",
            status_code=422,
        ) from exc

    clean_subject = (subject or "").strip() or item.name
    if len(clean_subject) > 160:
        raise MobileAPIError(
            code="library_share_subject_too_long",
            message="The subject is too long.",
            status_code=422,
        )

    command = {
        Food: (create_food_share, "food", "food"),
        Meal: (create_meal_share, "meal", "meal"),
        DailyPlan: (create_dailyplan_share, "dailyplan", "dailyplan"),
        Program: (create_program_share, "program", "program"),
    }.get(type(item))
    if command is None:
        raise MobileAPIError(
            code="library_action_not_allowed",
            message="This item cannot be shared.",
            status_code=403,
        )

    create_share, argument_name, kind = command
    result = create_share(
        sender=request.auth.user,
        recipient_email=clean_email,
        subject=clean_subject,
        message=(message or "").strip(),
        **{argument_name: item},
    )
    email_subject, email_message = build_share_invitation_email(
        request=request,
        share=result.share,
        kind=kind,
        item_name=item.name,
        custom_subject=clean_subject,
        custom_message=(message or "").strip(),
    )
    delivery = deliver_share_invitation(
        share=result.share,
        subject=email_subject,
        message=email_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
    )

    if result.share.accepted_by_id:
        return "Compartido. Ya está disponible en la cuenta del destinatario."
    if delivery.sent:
        return "Compartido. Enviamos la invitación por correo."
    if delivery.reason == "duplicate_share":
        return "Ya estaba compartido; no reenviamos la invitación."
    return "La invitación fue creada, pero el correo no pudo enviarse."


def perform_library_action(request, entity: str, item_id: int, payload) -> dict:
    item = _available_item(request.auth.user, entity, item_id)
    action = payload.action
    _ensure_allowed(item, request.auth.user, action)
    entity_name = ENTITY_NAMES[entity]

    if action == "rename":
        _rename(item, payload.name)
        return {"action": action, "item_id": item.id, "message": f"{entity_name.capitalize()} renombrado."}
    if action == "duplicate":
        duplicated = _duplicate(item, request.auth.user)
        return {"action": action, "item_id": duplicated.id, "message": f"{entity_name.capitalize()} duplicado."}
    if action == "delete":
        deleted_id = _delete(item)
        return {"action": action, "item_id": deleted_id, "message": f"{entity_name.capitalize()} eliminado."}

    message = _share(
        request,
        item,
        recipient_email=payload.recipient_email,
        subject=payload.subject,
        message=payload.message,
    )
    return {"action": action, "item_id": item.id, "message": message}


def _owned_library_items(user, entity: str):
    if entity == "foods":
        return Food.objects.filter(created_by=user, is_active=True)
    if entity == "meals":
        return Meal.objects.filter(created_by=user, is_draft=False, dailyplanmeal__isnull=True).distinct()
    if entity == "daily-plans":
        return DailyPlan.objects.filter(created_by=user, is_draft=False).exclude(source=DailyPlan.SOURCE_PROGRAM)
    if entity == "programs":
        return Program.objects.filter(created_by=user)
    raise MobileAPIError(code="library_not_found", message="The requested library was not found.", status_code=404)


@transaction.atomic
def reorder_library(user, entity: str, ordered_ids: list[int]) -> dict:
    if len(ordered_ids) != len(set(ordered_ids)):
        raise MobileAPIError(code="library_order_invalid", message="The order contains duplicate items.", status_code=422)
    items = {item.id: item for item in _owned_library_items(user, entity).filter(id__in=ordered_ids)}
    if set(items) != set(ordered_ids):
        raise MobileAPIError(code="library_order_not_allowed", message="One or more items cannot be reordered.", status_code=403)
    changed = []
    for index, item_id in enumerate(ordered_ids):
        item = items[item_id]
        if item.list_order != index:
            item.list_order = index
            changed.append(item)
    if changed:
        type(changed[0]).objects.bulk_update(changed, ["list_order"])
    return {"affected_ids": ordered_ids, "skipped_ids": [], "message": "Orden guardado."}


@transaction.atomic
def bulk_delete_library(user, entity: str, item_ids: list[int]) -> dict:
    requested_ids = list(dict.fromkeys(item_ids))
    items = {item.id: item for item in _owned_library_items(user, entity).filter(id__in=requested_ids)}
    if set(items) != set(requested_ids):
        raise MobileAPIError(code="library_delete_not_allowed", message="One or more items cannot be deleted.", status_code=403)
    deleted_ids, skipped_ids = [], []
    for item_id in requested_ids:
        try:
            _delete(items[item_id])
            deleted_ids.append(item_id)
        except MobileAPIError as exc:
            if exc.status_code != 409:
                raise
            skipped_ids.append(item_id)
    message = f"{len(deleted_ids)} elemento(s) eliminado(s)."
    if skipped_ids:
        message += f" {len(skipped_ids)} no se pudieron eliminar."
    return {"affected_ids": deleted_ids, "skipped_ids": skipped_ids, "message": message}
