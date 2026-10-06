from dataclasses import dataclass

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render

from notas.application.learning_catalog import CATALOGS, find_article
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import LEARNING_DETAIL_VIEWMODE, LEARNING_VIEWMODE
from notas.presentation.viewmodels.base_vm import BaseVM

CATALOG_META = {
    "nutrition": {"title": "Fundamentos Nutricionales", "description": "Conceptos básicos para interpretar energía, nutrientes y seguimiento.", "icon": "heart-pulse"},
    "manuals": {"title": "Manuales de uso", "description": "Guías breves para entender los módulos y flujos principales de My Scoope.", "icon": "book-marked"},
}


@dataclass
class LearningContentVM:
    catalogs: list[dict] | None = None
    title: str = ""
    description: str = ""
    icon: str = ""
    articles: tuple = ()
    article: object | None = None
    kind: str = ""


@login_required
def learning_home(request):
    catalogs = [
        {"key": key, **meta, "count": len(CATALOGS[key])}
        for key, meta in CATALOG_META.items()
    ]
    return _render(request, LearningContentVM(catalogs=catalogs))


@login_required
def learning_catalog(request, kind):
    meta = CATALOG_META.get(kind)
    if meta is None:
        raise Http404
    return _render(request, LearningContentVM(**meta, articles=CATALOGS[kind], kind=kind), template="notas/learning/catalog.html")


@login_required
def learning_article(request, kind, slug):
    article = find_article(kind, slug)
    meta = CATALOG_META.get(kind)
    if article is None or meta is None:
        raise Http404
    content = LearningContentVM(title=meta["title"], article=article, kind=kind)
    return _render(request, content, template="notas/learning/article.html", detail=True)


def _render(request, content, *, template="notas/learning/home.html", detail=False):
    viewmode = LEARNING_DETAIL_VIEWMODE if detail else LEARNING_VIEWMODE
    return render(request, template, BaseVM(ui=build_ui_vm(viewmode), content=content).as_context())
