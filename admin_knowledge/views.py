from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET

from admin_knowledge.services import build_document_detail, build_knowledge_index


@staff_member_required
@require_GET
def overview(request):
    knowledge = build_knowledge_index(query=request.GET.get("q", ""))
    return render(
        request,
        "admin_knowledge/overview.html",
        {"knowledge": knowledge},
    )


@staff_member_required
@require_GET
def document_detail(request, document_path):
    try:
        knowledge = build_document_detail(document_path)
    except (FileNotFoundError, OSError, UnicodeError) as exc:
        raise Http404("Knowledge document not found.") from exc
    return render(
        request,
        "admin_knowledge/document.html",
        {"knowledge": knowledge},
    )
