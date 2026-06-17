from dataclasses import dataclass
from datetime import datetime

from django.urls import reverse
from django.utils import timezone

from notas.domain.models import DailyPlanShare, MealShare
from notas.presentation.composition.viewmodel.dailyplan.dailyplan_content import (
    build_dailyplan_list_content_data,
)
from notas.presentation.composition.viewmodel.dailyplan.list_dailyplan_builder import (
    build_dailyplan_list_vm,
)
from notas.presentation.composition.viewmodel.meal.meal_content import (
    build_meal_list_content_data,
)
from notas.presentation.composition.viewmodel.meal.list_meal_builder import (
    build_meal_list_vm,
)
from notas.presentation.config.viewmodel_config import (
    DAILYPLAN_VIEWMODE_SHARED_LIST,
    MEAL_VIEWMODE_SHARED_LIST,
)


@dataclass(frozen=True)
class InboxAttachment:
    kind: str
    label: str
    name: str
    icon: str
    open_url: str
    save_url: str


@dataclass(frozen=True)
class InboxItem:
    id: str
    share_id: int
    kind: str
    kind_label: str
    icon: str
    created_at: datetime
    received_at_label: str
    sender: str
    title: str
    summary: str
    message: str
    is_favorite: bool
    is_read: bool
    detail_url: str
    dismiss_url: str
    favorite_url: str
    attachment: InboxAttachment
    attachment_card: object
    attachment_cards: list
    actions: list[dict]


def _format_received_at(value) -> str:
    if value is None:
        return "Sin fecha"

    received_at = timezone.localtime(value) if timezone.is_aware(value) else value
    return received_at.strftime("%d-%m-%Y")


def _favorite_label(is_favorite: bool) -> str:
    return "Quitar favorito" if is_favorite else "Marcar como favorito"


def _build_actions(*, item_id: str, detail_url: str, dismiss_url: str, favorite_url: str, is_favorite: bool):
    return [
        {
            "key": "detail",
            "label": "Ver inbox",
            "icon": "arrow-right",
            "url": detail_url,
            "method": "get",
            "desktop_position": "inline",
            "mobile_position": "inline",
        },
        {
            "key": "favorite",
            "label": _favorite_label(is_favorite),
            "icon": "star",
            "url": favorite_url,
            "method": "post",
            "desktop_position": "menu",
            "mobile_position": "menu",
            "extra_class": "is-active" if is_favorite else "",
        },
        {
            "key": "delete",
            "label": "Eliminar inbox",
            "icon": "trash-2",
            "url": dismiss_url,
            "method": "post",
            "desktop_position": "menu",
            "mobile_position": "menu",
        },
    ]


def _build_attachment_actions(*, open_url: str, save_url: str):
    return [
        {
            "key": "save_attachment",
            "label": "Guardar en Mi librería",
            "icon": "bookmark",
            "url": save_url,
            "method": "post",
            "desktop_position": "inline",
            "mobile_position": "inline",
        },
        {
            "key": "attachment_detail",
            "label": "Ir a detail",
            "icon": "chevron-right",
            "url": open_url,
            "method": "get",
            "desktop_position": "inline",
            "mobile_position": "inline",
        },
    ]


def _share_message(share, fallback: str) -> str:
    return (getattr(share, "message", "") or "").strip() or fallback


def _build_dailyplan_attachment_card(share: DailyPlanShare):
    content_data = build_dailyplan_list_content_data(
        [share.dailyplan],
        share.accepted_by or share.sender,
        DAILYPLAN_VIEWMODE_SHARED_LIST,
    )
    list_vm = build_dailyplan_list_vm(content_data)
    if not list_vm.child_cards:
        return None

    open_url = reverse("dailyplan_shared_detail", args=[share.dailyplan_id])
    save_url = reverse("inbox_save_attachment", args=["dailyplan", share.id])
    card = list_vm.child_cards[0]
    card.actions = _build_attachment_actions(open_url=open_url, save_url=save_url)
    if card.titulo:
        card.titulo.url = open_url
    return card


def _build_meal_attachment_card(share: MealShare):
    content_data = build_meal_list_content_data(
        [share.meal],
        share.accepted_by or share.sender,
        MEAL_VIEWMODE_SHARED_LIST,
    )
    list_vm = build_meal_list_vm(content_data)
    if not list_vm.child_cards:
        return None

    open_url = reverse("meal_share_detail", args=[share.meal_id])
    save_url = reverse("inbox_save_attachment", args=["meal", share.id])
    card = list_vm.child_cards[0]
    card.actions = _build_attachment_actions(open_url=open_url, save_url=save_url)
    if card.titulo:
        card.titulo.url = open_url
    return card


def _build_dailyplan_item(share: DailyPlanShare) -> InboxItem:
    detail_url = reverse("inbox_detail", args=["dailyplan", share.id])
    dismiss_url = reverse("inbox_delete", args=["dailyplan", share.id])
    favorite_url = reverse("inbox_toggle_favorite", args=["dailyplan", share.id])
    attachment = InboxAttachment(
        kind="dailyplan",
        label="Plan diario compartido",
        name=share.dailyplan.name,
        icon="clipboard-list",
        open_url=reverse("dailyplan_shared_detail", args=[share.dailyplan_id]),
        save_url=reverse("inbox_save_attachment", args=["dailyplan", share.id]),
    )

    summary = _share_message(
        share,
        f"{share.sender.username} compartió un plan diario contigo.",
    )
    attachment_card = _build_dailyplan_attachment_card(share)

    return InboxItem(
        id=f"dailyplan-{share.id}",
        share_id=share.id,
        kind="dailyplan",
        kind_label="Plan diario",
        icon="clipboard-list",
        created_at=share.created_at,
        received_at_label=_format_received_at(share.created_at),
        sender=share.sender.username,
        title=(share.subject or share.dailyplan.name),
        summary=summary,
        message=summary,
        is_favorite=share.is_favorite,
        is_read=share.is_read,
        detail_url=detail_url,
        dismiss_url=dismiss_url,
        favorite_url=favorite_url,
        attachment=attachment,
        attachment_card=attachment_card,
        attachment_cards=[attachment_card] if attachment_card else [],
        actions=_build_actions(
            item_id=f"dailyplan-{share.id}",
            detail_url=detail_url,
            dismiss_url=dismiss_url,
            favorite_url=favorite_url,
            is_favorite=share.is_favorite,
        ),
    )


def _build_meal_item(share: MealShare) -> InboxItem:
    detail_url = reverse("inbox_detail", args=["meal", share.id])
    dismiss_url = reverse("inbox_delete", args=["meal", share.id])
    favorite_url = reverse("inbox_toggle_favorite", args=["meal", share.id])
    attachment = InboxAttachment(
        kind="meal",
        label="Comida compartida",
        name=share.meal.name,
        icon="utensils",
        open_url=reverse("meal_share_detail", args=[share.meal_id]),
        save_url=reverse("inbox_save_attachment", args=["meal", share.id]),
    )

    summary = _share_message(
        share,
        f"{share.sender.username} compartió una comida contigo.",
    )
    attachment_card = _build_meal_attachment_card(share)

    return InboxItem(
        id=f"meal-{share.id}",
        share_id=share.id,
        kind="meal",
        kind_label="Comida",
        icon="utensils",
        created_at=share.created_at,
        received_at_label=_format_received_at(share.created_at),
        sender=share.sender.username,
        title=(share.subject or share.meal.name),
        summary=summary,
        message=summary,
        is_favorite=share.is_favorite,
        is_read=share.is_read,
        detail_url=detail_url,
        dismiss_url=dismiss_url,
        favorite_url=favorite_url,
        attachment=attachment,
        attachment_card=attachment_card,
        attachment_cards=[attachment_card] if attachment_card else [],
        actions=_build_actions(
            item_id=f"meal-{share.id}",
            detail_url=detail_url,
            dismiss_url=dismiss_url,
            favorite_url=favorite_url,
            is_favorite=share.is_favorite,
        ),
    )


def _dailyplan_share_queryset(user):
    return (
        DailyPlanShare.objects
        .filter(
            accepted_by=user,
            dismissed=False,
            removed=False,
        )
        .select_related("dailyplan", "dailyplan__created_by", "dailyplan__original_author", "sender", "accepted_by")
        .prefetch_related("dailyplan__dailyplan_meals__meal__meal_food_set__food")
    )


def _meal_share_queryset(user):
    return (
        MealShare.objects
        .filter(
            accepted_by=user,
            dismissed=False,
            removed=False,
        )
        .select_related("meal", "meal__created_by", "meal__original_author", "sender", "accepted_by")
        .prefetch_related("meal__meal_food_set__food")
    )


def build_inbox_items(user, *, favorites_only: bool = False):
    dailyplan_shares = _dailyplan_share_queryset(user)
    meal_shares = _meal_share_queryset(user)

    if favorites_only:
        dailyplan_shares = dailyplan_shares.filter(is_favorite=True)
        meal_shares = meal_shares.filter(is_favorite=True)

    items = [
        *[
            _build_dailyplan_item(share)
            for share in dailyplan_shares
        ],
        *[
            _build_meal_item(share)
            for share in meal_shares
        ],
    ]

    items.sort(key=lambda item: item.created_at, reverse=True)
    return items


def get_inbox_item_or_404(user, *, kind: str, share_id: int):
    from django.shortcuts import get_object_or_404

    if kind == "dailyplan":
        share = get_object_or_404(
            _dailyplan_share_queryset(user),
            id=share_id,
        )
        return _build_dailyplan_item(share)

    if kind == "meal":
        share = get_object_or_404(
            _meal_share_queryset(user),
            id=share_id,
        )
        return _build_meal_item(share)

    raise ValueError("unsupported_inbox_kind")


def get_inbox_share_or_404(user, *, kind: str, share_id: int):
    from django.shortcuts import get_object_or_404

    if kind == "dailyplan":
        return get_object_or_404(
            _dailyplan_share_queryset(user),
            id=share_id,
        )

    if kind == "meal":
        return get_object_or_404(
            _meal_share_queryset(user),
            id=share_id,
        )

    raise ValueError("unsupported_inbox_kind")
