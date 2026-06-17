from dataclasses import dataclass
from datetime import datetime

from django.urls import reverse
from django.utils import timezone

from notas.domain.models import DailyPlanShare, MealShare


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
    is_favorite: bool
    detail_url: str
    dismiss_url: str
    favorite_url: str
    attachment: InboxAttachment
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

    return InboxItem(
        id=f"dailyplan-{share.id}",
        share_id=share.id,
        kind="dailyplan",
        kind_label="Plan diario",
        icon="clipboard-list",
        created_at=share.created_at,
        received_at_label=_format_received_at(share.created_at),
        sender=share.sender.username,
        title=share.dailyplan.name,
        summary=f"{share.sender.username} compartió un plan diario contigo.",
        is_favorite=share.is_favorite,
        detail_url=detail_url,
        dismiss_url=dismiss_url,
        favorite_url=favorite_url,
        attachment=attachment,
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

    return InboxItem(
        id=f"meal-{share.id}",
        share_id=share.id,
        kind="meal",
        kind_label="Comida",
        icon="utensils",
        created_at=share.created_at,
        received_at_label=_format_received_at(share.created_at),
        sender=share.sender.username,
        title=share.meal.name,
        summary=f"{share.sender.username} compartió una comida contigo.",
        is_favorite=share.is_favorite,
        detail_url=detail_url,
        dismiss_url=dismiss_url,
        favorite_url=favorite_url,
        attachment=attachment,
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
        .select_related("dailyplan", "sender")
    )


def _meal_share_queryset(user):
    return (
        MealShare.objects
        .filter(
            accepted_by=user,
            dismissed=False,
            removed=False,
        )
        .select_related("meal", "sender")
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
