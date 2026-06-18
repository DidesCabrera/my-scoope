from dataclasses import dataclass
from datetime import datetime

from django.urls import reverse
from django.utils import timezone

from notas.domain.models import (
    DailyPlanMealShare,
    DailyPlanShare,
    FoodShare,
    MealShare,
)
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
from notas.presentation.composition.viewmodel.food.list_foods_builder import build_food_list_vm
from notas.presentation.config.viewmodel_config import (
    DAILYPLAN_VIEWMODE_SHARED_LIST,
    FOOD_VIEWMODE_PERSONAL_LIST,
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
    sender_label: str
    direction: str
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


def _build_sent_actions(*, open_url: str, label: str = "Ir a detail"):
    return [
        {
            "key": "attachment_detail",
            "label": label,
            "icon": "chevron-right",
            "url": open_url,
            "method": "get",
            "desktop_position": "inline",
            "mobile_position": "inline",
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


def _inbox_attachment_detail_url(kind: str, share_id: int) -> str:
    return reverse("inbox_attachment_detail", args=[kind, share_id])


def _inbox_sent_detail_url(kind: str, share_id: int) -> str:
    return reverse("inbox_sent_detail", args=[kind, share_id])


def _inbox_sent_attachment_detail_url(kind: str, share_id: int) -> str:
    return reverse("inbox_sent_attachment_detail", args=[kind, share_id])


def _build_dailyplan_attachment_card(share: DailyPlanShare, *, open_url: str | None = None, save_url: str | None = None):
    content_data = build_dailyplan_list_content_data(
        [share.dailyplan],
        share.accepted_by or share.sender,
        DAILYPLAN_VIEWMODE_SHARED_LIST,
    )
    list_vm = build_dailyplan_list_vm(content_data)
    if not list_vm.child_cards:
        return None

    open_url = open_url or reverse("dailyplan_shared_detail", args=[share.dailyplan_id])
    save_url = save_url or reverse("inbox_save_attachment", args=["dailyplan", share.id])
    card = list_vm.child_cards[0]
    card.actions = _build_attachment_actions(open_url=open_url, save_url=save_url)
    if card.titulo:
        card.titulo.url = open_url
    return card


def _build_meal_attachment_card(share: MealShare, *, open_url: str | None = None, save_url: str | None = None):
    content_data = build_meal_list_content_data(
        [share.meal],
        share.accepted_by or share.sender,
        MEAL_VIEWMODE_SHARED_LIST,
    )
    list_vm = build_meal_list_vm(content_data)
    if not list_vm.child_cards:
        return None

    open_url = open_url or reverse("meal_share_detail", args=[share.meal_id])
    save_url = save_url or reverse("inbox_save_attachment", args=["meal", share.id])
    card = list_vm.child_cards[0]
    card.actions = _build_attachment_actions(open_url=open_url, save_url=save_url)
    if card.titulo:
        card.titulo.url = open_url
    return card


def _build_food_attachment_card(share: FoodShare, *, open_url: str | None = None, save_url: str | None = None):
    list_vm = build_food_list_vm(
        [share.food],
        share.accepted_by or share.sender,
        FOOD_VIEWMODE_PERSONAL_LIST,
    )
    if not list_vm.child_cards:
        return None

    open_url = open_url or reverse("food_detail", args=[share.food_id])
    save_url = save_url or reverse("inbox_save_attachment", args=["food", share.id])
    card = list_vm.child_cards[0]
    card.actions = _build_attachment_actions(open_url=open_url, save_url=save_url)
    if card.titulo:
        card.titulo.url = open_url
    return card


def _build_dpm_attachment_card(share: DailyPlanMealShare, *, open_url: str | None = None, save_url: str | None = None):
    content_data = build_meal_list_content_data(
        [share.dailyplan_meal.meal],
        share.accepted_by or share.sender,
        MEAL_VIEWMODE_SHARED_LIST,
    )
    list_vm = build_meal_list_vm(content_data)
    if not list_vm.child_cards:
        return None

    open_url = open_url or reverse("dailyplanmeal_share_detail", args=[share.id])
    save_url = save_url or reverse("inbox_save_attachment", args=["dpm", share.id])
    card = list_vm.child_cards[0]
    card.actions = _build_attachment_actions(open_url=open_url, save_url=save_url)
    if card.titulo:
        card.titulo.url = open_url
    return card


def _build_dailyplan_item(share: DailyPlanShare) -> InboxItem:
    detail_url = reverse("inbox_detail", args=["dailyplan", share.id])
    dismiss_url = reverse("inbox_delete", args=["dailyplan", share.id])
    favorite_url = reverse("inbox_toggle_favorite", args=["dailyplan", share.id])
    open_url = _inbox_attachment_detail_url("dailyplan", share.id)
    save_url = reverse("inbox_save_attachment", args=["dailyplan", share.id])
    attachment = InboxAttachment(
        kind="dailyplan",
        label="Plan diario compartido",
        name=share.dailyplan.name,
        icon="clipboard-list",
        open_url=open_url,
        save_url=save_url,
    )

    summary = _share_message(
        share,
        f"{share.sender.username} compartió un plan diario contigo.",
    )
    attachment_card = _build_dailyplan_attachment_card(share, open_url=open_url, save_url=save_url)

    return InboxItem(
        id=f"dailyplan-{share.id}",
        share_id=share.id,
        kind="dailyplan",
        kind_label="Plan diario",
        icon="clipboard-list",
        created_at=share.created_at,
        received_at_label=_format_received_at(share.created_at),
        sender=share.sender.username,
        sender_label="",
        direction="received",
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
    open_url = _inbox_attachment_detail_url("meal", share.id)
    save_url = reverse("inbox_save_attachment", args=["meal", share.id])
    attachment = InboxAttachment(
        kind="meal",
        label="Comida compartida",
        name=share.meal.name,
        icon="utensils",
        open_url=open_url,
        save_url=save_url,
    )

    summary = _share_message(
        share,
        f"{share.sender.username} compartió una comida contigo.",
    )
    attachment_card = _build_meal_attachment_card(share, open_url=open_url, save_url=save_url)

    return InboxItem(
        id=f"meal-{share.id}",
        share_id=share.id,
        kind="meal",
        kind_label="Comida",
        icon="utensils",
        created_at=share.created_at,
        received_at_label=_format_received_at(share.created_at),
        sender=share.sender.username,
        sender_label="",
        direction="received",
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



def _build_food_item(share: FoodShare) -> InboxItem:
    detail_url = reverse("inbox_detail", args=["food", share.id])
    dismiss_url = reverse("inbox_delete", args=["food", share.id])
    favorite_url = reverse("inbox_toggle_favorite", args=["food", share.id])
    open_url = _inbox_attachment_detail_url("food", share.id)
    save_url = reverse("inbox_save_attachment", args=["food", share.id])
    attachment = InboxAttachment(
        kind="food",
        label="Alimento compartido",
        name=share.food.name,
        icon="carrot",
        open_url=open_url,
        save_url=save_url,
    )
    summary = _share_message(share, f"{share.sender.username} compartió un alimento contigo.")
    attachment_card = _build_food_attachment_card(share, open_url=open_url, save_url=save_url)
    return InboxItem(
        id=f"food-{share.id}",
        share_id=share.id,
        kind="food",
        kind_label="Alimento",
        icon="carrot",
        created_at=share.created_at,
        received_at_label=_format_received_at(share.created_at),
        sender=share.sender.username,
        sender_label="",
        direction="received",
        title=(share.subject or share.food.name),
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
        actions=_build_actions(item_id=f"food-{share.id}", detail_url=detail_url, dismiss_url=dismiss_url, favorite_url=favorite_url, is_favorite=share.is_favorite),
    )


def _build_dpm_item(share: DailyPlanMealShare) -> InboxItem:
    dpm = share.dailyplan_meal
    detail_url = reverse("inbox_detail", args=["dpm", share.id])
    dismiss_url = reverse("inbox_delete", args=["dpm", share.id])
    favorite_url = reverse("inbox_toggle_favorite", args=["dpm", share.id])
    open_url = _inbox_attachment_detail_url("dpm", share.id)
    save_url = reverse("inbox_save_attachment", args=["dpm", share.id])
    attachment = InboxAttachment(
        kind="dpm",
        label="Comida de plan compartida",
        name=dpm.meal.name,
        icon="utensils",
        open_url=open_url,
        save_url=save_url,
    )
    summary = _share_message(share, f"{share.sender.username} compartió una comida de plan contigo.")
    attachment_card = _build_dpm_attachment_card(share, open_url=open_url, save_url=save_url)
    return InboxItem(
        id=f"dpm-{share.id}",
        share_id=share.id,
        kind="dpm",
        kind_label="Comida de plan",
        icon="utensils",
        created_at=share.created_at,
        received_at_label=_format_received_at(share.created_at),
        sender=share.sender.username,
        sender_label="",
        direction="received",
        title=(share.subject or dpm.meal.name),
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
        actions=_build_actions(item_id=f"dpm-{share.id}", detail_url=detail_url, dismiss_url=dismiss_url, favorite_url=favorite_url, is_favorite=share.is_favorite),
    )

def _build_sent_dailyplan_item(share: DailyPlanShare) -> InboxItem:
    detail_url = _inbox_sent_detail_url("dailyplan", share.id)
    open_url = _inbox_sent_attachment_detail_url("dailyplan", share.id)
    attachment = InboxAttachment(
        kind="dailyplan",
        label="Plan diario enviado",
        name=share.dailyplan.name,
        icon="clipboard-list",
        open_url=open_url,
        save_url="",
    )

    summary = _share_message(
        share,
        f"Compartiste un plan diario con {share.recipient_email}.",
    )
    attachment_card = _build_dailyplan_attachment_card(share, open_url=open_url, save_url="")
    if attachment_card:
        attachment_card.actions = _build_sent_actions(open_url=open_url)

    return InboxItem(
        id=f"sent-dailyplan-{share.id}",
        share_id=share.id,
        kind="dailyplan",
        kind_label="Plan diario",
        icon="clipboard-list",
        created_at=share.created_at,
        received_at_label=_format_received_at(share.created_at),
        sender=share.recipient_email,
        sender_label="Para",
        direction="sent",
        title=(share.subject or share.dailyplan.name),
        summary=summary,
        message=summary,
        is_favorite=False,
        is_read=True,
        detail_url=detail_url,
        dismiss_url="",
        favorite_url="",
        attachment=attachment,
        attachment_card=attachment_card,
        attachment_cards=[attachment_card] if attachment_card else [],
        actions=_build_sent_actions(open_url=detail_url, label="Ver enviado"),
    )


def _build_sent_meal_item(share: MealShare) -> InboxItem:
    detail_url = _inbox_sent_detail_url("meal", share.id)
    open_url = _inbox_sent_attachment_detail_url("meal", share.id)
    attachment = InboxAttachment(
        kind="meal",
        label="Comida enviada",
        name=share.meal.name,
        icon="utensils",
        open_url=open_url,
        save_url="",
    )

    summary = _share_message(
        share,
        f"Compartiste una comida con {share.recipient_email}.",
    )
    attachment_card = _build_meal_attachment_card(share, open_url=open_url, save_url="")
    if attachment_card:
        attachment_card.actions = _build_sent_actions(open_url=open_url)

    return InboxItem(
        id=f"sent-meal-{share.id}",
        share_id=share.id,
        kind="meal",
        kind_label="Comida",
        icon="utensils",
        created_at=share.created_at,
        received_at_label=_format_received_at(share.created_at),
        sender=share.recipient_email,
        sender_label="Para",
        direction="sent",
        title=(share.subject or share.meal.name),
        summary=summary,
        message=summary,
        is_favorite=False,
        is_read=True,
        detail_url=detail_url,
        dismiss_url="",
        favorite_url="",
        attachment=attachment,
        attachment_card=attachment_card,
        attachment_cards=[attachment_card] if attachment_card else [],
        actions=_build_sent_actions(open_url=detail_url, label="Ver enviado"),
    )



def _build_sent_food_item(share: FoodShare) -> InboxItem:
    detail_url = _inbox_sent_detail_url("food", share.id)
    open_url = _inbox_sent_attachment_detail_url("food", share.id)
    attachment = InboxAttachment(kind="food", label="Alimento enviado", name=share.food.name, icon="carrot", open_url=open_url, save_url="")
    summary = _share_message(share, f"Compartiste un alimento con {share.recipient_email}.")
    attachment_card = _build_food_attachment_card(share, open_url=open_url, save_url="")
    if attachment_card:
        attachment_card.actions = _build_sent_actions(open_url=open_url)
    return InboxItem(
        id=f"sent-food-{share.id}", share_id=share.id, kind="food", kind_label="Alimento", icon="carrot", created_at=share.created_at,
        received_at_label=_format_received_at(share.created_at), sender=share.recipient_email, sender_label="Para", direction="sent",
        title=(share.subject or share.food.name), summary=summary, message=summary, is_favorite=False, is_read=True, detail_url=detail_url,
        dismiss_url="", favorite_url="", attachment=attachment, attachment_card=attachment_card, attachment_cards=[attachment_card] if attachment_card else [],
        actions=_build_sent_actions(open_url=detail_url, label="Ver enviado"),
    )


def _build_sent_dpm_item(share: DailyPlanMealShare) -> InboxItem:
    dpm = share.dailyplan_meal
    detail_url = _inbox_sent_detail_url("dpm", share.id)
    open_url = _inbox_sent_attachment_detail_url("dpm", share.id)
    attachment = InboxAttachment(kind="dpm", label="Comida de plan enviada", name=dpm.meal.name, icon="utensils", open_url=open_url, save_url="")
    summary = _share_message(share, f"Compartiste una comida de plan con {share.recipient_email}.")
    attachment_card = _build_dpm_attachment_card(share, open_url=open_url, save_url="")
    if attachment_card:
        attachment_card.actions = _build_sent_actions(open_url=open_url)
    return InboxItem(
        id=f"sent-dpm-{share.id}", share_id=share.id, kind="dpm", kind_label="Comida de plan", icon="utensils", created_at=share.created_at,
        received_at_label=_format_received_at(share.created_at), sender=share.recipient_email, sender_label="Para", direction="sent",
        title=(share.subject or dpm.meal.name), summary=summary, message=summary, is_favorite=False, is_read=True, detail_url=detail_url,
        dismiss_url="", favorite_url="", attachment=attachment, attachment_card=attachment_card, attachment_cards=[attachment_card] if attachment_card else [],
        actions=_build_sent_actions(open_url=detail_url, label="Ver enviado"),
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



def _food_share_queryset(user):
    return (
        FoodShare.objects
        .filter(accepted_by=user, dismissed=False, removed=False)
        .select_related("food", "food__created_by", "sender", "accepted_by")
    )


def _dpm_share_queryset(user):
    return (
        DailyPlanMealShare.objects
        .filter(accepted_by=user, dismissed=False, removed=False)
        .select_related("dailyplan_meal", "dailyplan_meal__meal", "dailyplan_meal__dailyplan", "dailyplan_meal__meal__created_by", "sender", "accepted_by")
        .prefetch_related("dailyplan_meal__meal__meal_food_set__food")
    )


def _food_share_sent_queryset(user):
    return (
        FoodShare.objects
        .filter(sender=user, removed=False)
        .select_related("food", "food__created_by", "sender", "accepted_by")
    )


def _dpm_share_sent_queryset(user):
    return (
        DailyPlanMealShare.objects
        .filter(sender=user, removed=False)
        .select_related("dailyplan_meal", "dailyplan_meal__meal", "dailyplan_meal__dailyplan", "dailyplan_meal__meal__created_by", "sender", "accepted_by")
        .prefetch_related("dailyplan_meal__meal__meal_food_set__food")
    )

def _dailyplan_share_sent_queryset(user):
    return (
        DailyPlanShare.objects
        .filter(sender=user, removed=False)
        .select_related("dailyplan", "dailyplan__created_by", "dailyplan__original_author", "sender", "accepted_by")
        .prefetch_related("dailyplan__dailyplan_meals__meal__meal_food_set__food")
    )


def _meal_share_sent_queryset(user):
    return (
        MealShare.objects
        .filter(sender=user, removed=False)
        .select_related("meal", "meal__created_by", "meal__original_author", "sender", "accepted_by")
        .prefetch_related("meal__meal_food_set__food")
    )


def build_inbox_items(user, *, favorites_only: bool = False, scope: str = "received"):
    if scope == "sent":
        items = [
            *[
                _build_sent_dailyplan_item(share)
                for share in _dailyplan_share_sent_queryset(user)
            ],
            *[
                _build_sent_meal_item(share)
                for share in _meal_share_sent_queryset(user)
            ],
            *[
                _build_sent_food_item(share)
                for share in _food_share_sent_queryset(user)
            ],
            *[
                _build_sent_dpm_item(share)
                for share in _dpm_share_sent_queryset(user)
            ],
        ]
    else:
        dailyplan_shares = _dailyplan_share_queryset(user)
        meal_shares = _meal_share_queryset(user)
        food_shares = _food_share_queryset(user)
        dpm_shares = _dpm_share_queryset(user)

        if favorites_only:
            dailyplan_shares = dailyplan_shares.filter(is_favorite=True)
            meal_shares = meal_shares.filter(is_favorite=True)
            food_shares = food_shares.filter(is_favorite=True)
            dpm_shares = dpm_shares.filter(is_favorite=True)

        items = [
            *[
                _build_dailyplan_item(share)
                for share in dailyplan_shares
            ],
            *[
                _build_meal_item(share)
                for share in meal_shares
            ],
            *[
                _build_food_item(share)
                for share in food_shares
            ],
            *[
                _build_dpm_item(share)
                for share in dpm_shares
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

    if kind == "food":
        share = get_object_or_404(
            _food_share_queryset(user),
            id=share_id,
        )
        return _build_food_item(share)

    if kind == "dpm":
        share = get_object_or_404(
            _dpm_share_queryset(user),
            id=share_id,
        )
        return _build_dpm_item(share)

    raise ValueError("unsupported_inbox_kind")


def get_sent_inbox_item_or_404(user, *, kind: str, share_id: int):
    from django.shortcuts import get_object_or_404

    if kind == "dailyplan":
        share = get_object_or_404(
            _dailyplan_share_sent_queryset(user),
            id=share_id,
        )
        return _build_sent_dailyplan_item(share)

    if kind == "meal":
        share = get_object_or_404(
            _meal_share_sent_queryset(user),
            id=share_id,
        )
        return _build_sent_meal_item(share)

    if kind == "food":
        share = get_object_or_404(
            _food_share_sent_queryset(user),
            id=share_id,
        )
        return _build_sent_food_item(share)

    if kind == "dpm":
        share = get_object_or_404(
            _dpm_share_sent_queryset(user),
            id=share_id,
        )
        return _build_sent_dpm_item(share)

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

    if kind == "food":
        return get_object_or_404(
            _food_share_queryset(user),
            id=share_id,
        )

    if kind == "dpm":
        return get_object_or_404(
            _dpm_share_queryset(user),
            id=share_id,
        )

    raise ValueError("unsupported_inbox_kind")

def get_sent_inbox_share_or_404(user, *, kind: str, share_id: int):
    from django.shortcuts import get_object_or_404

    if kind == "dailyplan":
        return get_object_or_404(
            _dailyplan_share_sent_queryset(user),
            id=share_id,
        )

    if kind == "meal":
        return get_object_or_404(
            _meal_share_sent_queryset(user),
            id=share_id,
        )

    if kind == "food":
        return get_object_or_404(
            _food_share_sent_queryset(user),
            id=share_id,
        )

    if kind == "dpm":
        return get_object_or_404(
            _dpm_share_sent_queryset(user),
            id=share_id,
        )

    raise ValueError("unsupported_inbox_kind")

