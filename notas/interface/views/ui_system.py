from dataclasses import asdict
from types import SimpleNamespace

from allauth.account.forms import ResetPasswordForm, ResetPasswordKeyForm
from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_sameorigin

from notas.presentation.composition.viewmodel.components.builder_headers import build_page_header
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import HOME_VIEWMODE
from notas.presentation.ui_system_gallery import build_ui_system_gallery_examples


@xframe_options_sameorigin
def ui_system_gallery(request):
    if not settings.DEBUG:
        raise Http404

    ui = build_ui_vm(HOME_VIEWMODE)
    ui.title = "UI System Web"
    ui.icon = "panels-top-left"

    examples = build_ui_system_gallery_examples()
    examples["embed"] = request.GET.get("embed") == "1"
    examples["focus"] = request.GET.get("focus", "")

    return render(
        request,
        "notas/dev/ui_system_gallery.html",
        {
            "vm": {
                "ui": asdict(ui),
                "content": {"header": asdict(build_page_header())},
            },
            "gallery": examples,
        },
    )


@xframe_options_sameorigin
def ui_system_auth_preview(request, screen):
    if not settings.DEBUG:
        raise Http404

    if screen == "verification-sent":
        return render(request, "account/verification_sent.html")

    if screen == "email-confirm":
        confirmation = SimpleNamespace(
            key="ui-system-preview",
            email_address=SimpleNamespace(email="felipe@myscoope.com"),
        )
        return render(
            request,
            "account/email_confirm.html",
            {"confirmation": confirmation, "can_confirm": True},
        )

    if screen == "password-reset":
        return render(
            request,
            "account/password_reset.html",
            {"form": ResetPasswordForm()},
        )

    if screen == "password-reset-sent":
        return render(request, "account/password_reset_done.html")

    if screen == "password-reset-new":
        return render(
            request,
            "account/password_reset_from_key.html",
            {
                "form": ResetPasswordKeyForm(),
                "token_fail": False,
                "action_url": "#",
            },
        )

    if screen == "password-reset-complete":
        return render(request, "account/password_reset_from_key_done.html")

    raise Http404
