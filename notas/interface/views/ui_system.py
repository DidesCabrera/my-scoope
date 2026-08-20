from dataclasses import asdict

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
