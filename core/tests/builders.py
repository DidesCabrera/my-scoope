"""Small persistence builders shared by focused test suites."""

from django.contrib.auth import get_user_model


def create_test_user(
    username: str,
    *,
    email: str | None = None,
    password: str = "password123",
    **attributes,
):
    return get_user_model().objects.create_user(
        username=username,
        email=email if email is not None else username if "@" in username else "",
        password=password,
        **attributes,
    )


def create_staff_user(username: str, **attributes):
    attributes.setdefault("is_staff", True)
    return create_test_user(username, **attributes)
