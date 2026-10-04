from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction


@transaction.atomic
def rename_username(*, user, username: str):
    clean_username = username.strip()
    if not clean_username:
        raise ValueError("account_username_required")

    user_model = get_user_model()
    username_field = user_model._meta.get_field(user_model.USERNAME_FIELD)
    if len(clean_username) > username_field.max_length:
        raise ValueError("account_username_too_long")
    try:
        username_field.run_validators(clean_username)
    except ValidationError as exc:
        raise ValueError("account_username_invalid") from exc

    locked_user = user_model._default_manager.select_for_update().get(pk=user.pk)
    if user_model._default_manager.filter(username__iexact=clean_username).exclude(pk=locked_user.pk).exists():
        raise ValueError("account_username_unavailable")

    locked_user.username = clean_username
    try:
        locked_user.save(update_fields=["username"])
    except IntegrityError as exc:
        raise ValueError("account_username_unavailable") from exc
    user.username = locked_user.username
    return locked_user
