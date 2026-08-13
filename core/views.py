from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET

from core.msos import load_msos_data


@require_GET
def healthz(request):
    """Cheap process-level liveness probe for the deployment platform."""
    return JsonResponse({"status": "ok"})


def landing(request):
    return render(request, "core/landing.html")


@staff_member_required
@require_GET
def msos(request):
    return render(request, "core/msos.html", {"msos": load_msos_data()})


@staff_member_required
@require_GET
def msos_detail(request, kind, item_id):
    data = load_msos_data()

    if kind == "project":
        items = data["strategy"]["roadmap"]["projects"]
        item = next((candidate for candidate in items if candidate["code"].lower() == item_id.lower()), None)
        parent_label = "Estrategia"
        return_url = f'{reverse("msos")}#strategy'
    elif kind == "task":
        items = [
            task
            for group in data["ceo_dashboard"]["task_board"]["groups"]
            for task in group["items"]
        ]
        item = next((candidate for candidate in items if candidate.get("id") == item_id), None)
        parent_label = "CEO Dashboard"
        return_url = f'{reverse("msos")}#ceo-dashboard'
    elif kind == "front":
        readiness_task = next(
            task
            for group in data["ceo_dashboard"]["task_board"]["groups"]
            for task in group["items"]
            if task.get("id") == "launch-readiness"
        )
        items = readiness_task["detail"]["sections"][0]["blocks"]
        item = next((candidate for candidate in items if candidate.get("id") == item_id), None)
        parent_label = "Readiness para lanzamiento"
        return_url = reverse("msos_detail", args=("task", "launch-readiness"))
    elif kind == "department":
        items = data["departments"]["items"]
        item = next((candidate for candidate in items if candidate.get("id") == item_id), None)
        parent_label = "Departamentos"
        return_url = f'{reverse("msos")}#departments'
        if item is not None:
            item["detail"] = {
                "central_question": (
                    f'¿Qué necesita {item["name"]} para cumplir su responsabilidad y reducir '
                    "los riesgos que hoy limitan a la empresa?"
                ),
                "sections": [
                    {
                        "label": "Responsabilidad permanente",
                        "title": "Mandato del área",
                        "summary": item["responsibility"],
                    },
                    {
                        "label": "Foco vigente",
                        "title": "Prioridad y temas activos",
                        "summary": item["priority"],
                        "points": item["active_topics"],
                    },
                    {
                        "label": "Dirección",
                        "title": "Decisiones pendientes",
                        "points": item["pending_decisions"],
                    },
                    {
                        "label": "Atención",
                        "title": "Riesgos visibles",
                        "points": item["risks"],
                    },
                    {
                        "label": "Avance",
                        "title": "Próxima acción",
                        "summary": item["next_action"],
                    },
                ],
            }
    else:
        raise Http404("Tipo de contenido MSOS desconocido")

    if item is None:
        raise Http404("Contenido MSOS no encontrado")

    detail = item.get("detail")
    if detail:
        section_offset = 1 if detail.get("central_question") else 0
        for section_index, section in enumerate(detail.get("sections", []), start=1 + section_offset):
            section["number"] = str(section_index)
            for item_index, section_item in enumerate(section.get("blocks", []), start=1):
                section_item["number"] = f"{section_index}.{item_index}"

    return render(
        request,
        "core/msos_detail.html",
        {
            "msos": data,
            "item": item,
            "item_title": item.get("title") or item.get("name", ""),
            "item_intro": (
                item.get("summary")
                or item.get("why")
                or item.get("description")
                or item.get("responsibility", "")
            ),
            "kind": kind,
            "parent_label": parent_label,
            "return_url": return_url,
        },
    )


def privacy(request):
    return render(request, "core/privacy.html")


def terms(request):
    return render(request, "core/terms.html")


def support(request):
    return render(request, "core/support.html")
