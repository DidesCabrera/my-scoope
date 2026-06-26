from __future__ import annotations


from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from notas.application.services.access.capabilities import get_capabilities
from notas.application.services.commands.program_commands import (
    add_week_to_program,
    assign_dailyplan_to_program_slot,
    copy_program as copy_program_command,
    create_weekly_program,
    delete_program,
    duplicate_week_in_program,
    fork_program as fork_program_command,
    remove_program_day,
    remove_week_from_program,
    rename_program,
    reorder_program_weeks,
)
from notas.application.services.commands.share_commands import create_program_share
from notas.application.services.nutrition.weight import get_current_weight
from notas.domain.models import Program, ProgramDay
from notas.interface.forms.forms import ProgramShareForm
from notas.presentation.config.viewmodel_config import (
    PROGRAM_VIEWMODE_CONFIGURE,
    PROGRAM_VIEWMODE_CREATE,
    PROGRAM_VIEWMODE_PERSONAL_DETAIL,
    PROGRAM_VIEWMODE_PERSONAL_LIST,
    PROGRAM_VIEWMODE_SHARE,
)
from notas.presentation.viewmodels.programs import (
    available_dailyplans as program_available_dailyplans,
    build_program_day_child_card as build_program_day_child_card_vm,
    build_program_detail_content as build_program_detail_content_vm,
    build_program_list_cards as build_program_list_cards_vm,
    build_program_week_detail_content as build_program_week_detail_content_vm,
)
from notas.presentation.viewmodels.program_actions import (
    action as _action,
    program_detail_actions as _program_detail_actions,
    program_header as _header,
    program_list_actions as _program_list_actions,
    program_vm_context as _vm_context,
    program_week_detail_actions as _program_week_detail_actions,
)
from notas.application.services.cache.program_summary import refresh_program_summary_cache


# ==================================================
# REQUEST HELPERS
# ==================================================

def _normalize_list_mode(request_get=None):
    mode = (request_get or {}).get("mode", "list")
    return mode if mode in {"list", "reorder", "delete"} else "list"


def _safe_return_to(request, fallback_name, mode=None):
    fallback_url = reverse(fallback_name)
    if mode:
        fallback_url = f"{fallback_url}?mode={mode}"

    return_to = request.POST.get("return_to") or request.GET.get("return_to") or ""
    if return_to and url_has_allowed_host_and_scheme(
        url=return_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return return_to

    return fallback_url


# ==================================================
# NUTRITION HELPERS
# ==================================================



# ==================================================
# LIST
# ==================================================

@login_required
def program_list(request):
    list_mode = _normalize_list_mode(request.GET)

    base_programs = (
        Program.objects
        .filter(
            Q(created_by=request.user)
            | Q(shares__accepted_by=request.user, shares__removed=False)
        )
        .distinct()
        .order_by("list_order", "-created_at", "-id")
    )

    if list_mode in {"reorder", "delete"}:
        programs = base_programs.only("id", "name", "list_order", "created_at")
    else:
        programs = (
            base_programs
            .select_related("created_by", "original_author", "forked_from")
            .prefetch_related("shares")
        )

    child_cards = build_program_list_cards_vm(
        programs,
        request.user,
        list_mode=list_mode,
        current_weight=get_current_weight(request.user),
    )
    content = {
        "header": _header(_program_list_actions(list_mode)),
        "child_cards": child_cards,
        "list_mode": list_mode,
    }

    context = _vm_context(
        PROGRAM_VIEWMODE_PERSONAL_LIST,
        content=content,
    )

    return render(request, "notas/programs/list.html", context)


@login_required
@require_POST
def program_list_reorder(request):
    ordered_ids = request.POST.getlist("order[]")

    if not ordered_ids:
        return HttpResponseBadRequest("No order received.")

    programs = {
        program.id: program
        for program in Program.objects.filter(
            created_by=request.user,
            id__in=ordered_ids,
        )
    }

    for index, raw_id in enumerate(ordered_ids):
        try:
            program_id = int(raw_id)
        except (TypeError, ValueError):
            continue

        program = programs.get(program_id)
        if not program:
            continue

        if program.list_order != index:
            program.list_order = index
            program.save(update_fields=["list_order"])

    return HttpResponse(status=204)


@login_required
@require_POST
def program_list_bulk_delete(request):
    selected_ids = request.POST.getlist("selected_ids[]")

    if not selected_ids:
        messages.info(request, "No seleccionaste programas para eliminar.")
        return redirect(_safe_return_to(request, "program_list", mode="delete"))

    programs = Program.objects.filter(
        created_by=request.user,
        id__in=selected_ids,
    )

    deleted_count = 0
    for program in programs:
        delete_program(program=program)
        deleted_count += 1

    if deleted_count:
        messages.success(request, f"{deleted_count} programa(s) eliminado(s).")
    else:
        messages.info(request, "No se eliminaron programas.")

    return redirect(_safe_return_to(request, "program_list", mode="delete"))


# ==================================================
# CREATE / DETAIL / CONFIGURE
# ==================================================

@login_required
def program_create(request):
    viewmode = PROGRAM_VIEWMODE_CREATE
    content = {"header": _header([])}

    if request.method == "POST":
        name = request.POST.get("name")

        try:
            result = create_weekly_program(
                user=request.user,
                name=name,
            )
        except ValueError:
            messages.error(request, "El nombre es obligatorio.")
            return redirect("program_create")

        return redirect("program_detail", pk=result.program.pk)

    context = _vm_context(viewmode, content=content)
    return render(request, "notas/programs/create.html", context)


@login_required
def program_rename(request, pk):
    program = get_object_or_404(
        Program,
        pk=pk,
        created_by=request.user,
    )

    return_to = (
        request.POST.get("return_to")
        or request.GET.get("return_to")
        or ""
    )
    fallback_url = reverse("program_detail", kwargs={"pk": program.pk})

    if return_to and not url_has_allowed_host_and_scheme(
        url=return_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return_to = ""

    redirect_url = return_to or fallback_url

    if request.method == "POST":
        name = request.POST.get("name", "")

        try:
            rename_program(
                program=program,
                name=name,
            )
        except ValueError:
            messages.error(request, "El nombre no puede estar vacío.")
            rename_url = reverse("program_rename", kwargs={"pk": program.pk})
            if return_to:
                rename_url = f"{rename_url}?return_to={return_to}"
            return redirect(rename_url)

        messages.success(request, "Nombre actualizado correctamente.")
        return redirect(redirect_url)

    content = {
        "header": _header([
            _action(
                key="back_detail",
                label="Volver",
                url=redirect_url,
                icon="chevron-left",
                order=10,
                is_back=True,
            )
        ]),
        "program": program,
        "return_to": return_to,
    }

    context = _vm_context(
        PROGRAM_VIEWMODE_CREATE,
        content=content,
        instance=program,
    )
    return render(request, "notas/programs/rename.html", context)


@login_required
def program_detail(request, pk):
    program = get_object_or_404(
        Program.objects.select_related("created_by", "original_author", "forked_from"),
        pk=pk,
    )

    if program.created_by_id != request.user.id and not program.shares.filter(
        accepted_by=request.user,
        removed=False,
    ).exists():
        return HttpResponseForbidden()

    content = build_program_detail_content_vm(
        program=program,
        user=request.user,
        header=_header(_program_detail_actions(program, request.user)),
    )

    context = _vm_context(
        PROGRAM_VIEWMODE_PERSONAL_DETAIL,
        content=content,
        instance=program,
    )

    return render(request, "notas/programs/detail.html", context)


@login_required
def program_week_detail(request, pk, week_number):
    program = get_object_or_404(
        Program.objects.select_related("created_by", "original_author", "forked_from"),
        pk=pk,
    )

    if program.created_by_id != request.user.id and not program.shares.filter(
        accepted_by=request.user,
        removed=False,
    ).exists():
        return HttpResponseForbidden()

    try:
        week_number = int(week_number)
    except (TypeError, ValueError):
        return HttpResponseBadRequest("Invalid week number.")

    if week_number < 1 or week_number > program.normalized_duration_weeks:
        return HttpResponseBadRequest("Invalid week number.")

    content = build_program_week_detail_content_vm(
        program=program,
        user=request.user,
        week_number=week_number,
        header=_header(_program_week_detail_actions(program, request.user, week_number)),
    )
    if content is None:
        return HttpResponseBadRequest("Invalid week number.")

    context = _vm_context(
        PROGRAM_VIEWMODE_PERSONAL_DETAIL,
        content=content,
        instance=program,
    )

    return render(request, "notas/programs/week_detail.html", context)


@login_required
@require_POST
def program_add_week(request, pk):
    program = get_object_or_404(Program, pk=pk, created_by=request.user)
    add_week_to_program(program=program)
    messages.success(request, f"Semana {program.normalized_duration_weeks} agregada al programa.")
    return redirect(f"{reverse('program_detail', args=[program.pk])}#week-{program.normalized_duration_weeks}")


@login_required
@require_POST
def program_remove_week(request, pk, week_number):
    program = get_object_or_404(Program, pk=pk, created_by=request.user)

    try:
        removed_week_number = int(week_number)
        remove_week_from_program(program=program, week_number=removed_week_number)
    except ValueError as exc:
        if str(exc) == "program_cannot_remove_last_week":
            messages.error(request, "El programa debe conservar al menos una semana.")
        else:
            messages.error(request, "La semana seleccionada no es válida.")
        return redirect("program_detail", pk=program.pk)

    messages.success(request, f"Semana {removed_week_number} eliminada del programa.")
    next_week = min(removed_week_number, program.normalized_duration_weeks)
    return redirect(f"{reverse('program_detail', args=[program.pk])}#week-{next_week}")


@login_required
@require_POST
def program_duplicate_week(request, pk, week_number):
    program = get_object_or_404(Program, pk=pk, created_by=request.user)

    try:
        result = duplicate_week_in_program(
            program=program,
            week_number=week_number,
            user=request.user,
        )
    except ValueError:
        messages.error(request, "La semana seleccionada no es válida.")
        return redirect("program_detail", pk=program.pk)

    messages.success(request, f"Semana {result.source_week_number} duplicada.")
    return redirect(f"{reverse('program_detail', args=[program.pk])}#week-{result.new_week_number}")


@login_required
@require_POST
def program_reorder_weeks(request, pk):
    program = get_object_or_404(Program, pk=pk, created_by=request.user)
    ordered_weeks = request.POST.getlist("order[]")

    if not ordered_weeks:
        return HttpResponseBadRequest("No order received.")

    try:
        reorder_program_weeks(program=program, ordered_week_numbers=ordered_weeks)
    except ValueError:
        return HttpResponseBadRequest("Invalid week order.")

    return HttpResponse(status=204)


@login_required
def configure_program(request, pk):
    program = get_object_or_404(
        Program.objects.prefetch_related("program_dailyplan"),
        pk=pk,
        created_by=request.user,
    )

    caps = get_capabilities(request.user)

    if request.method == "POST":
        is_public = bool(request.POST.get("is_public"))
        is_forkable = bool(request.POST.get("is_forkable"))
        is_copiable = bool(request.POST.get("is_copiable"))
        duration_weeks = request.POST.get("duration_weeks")

        if is_public and not caps.can_publish():
            messages.error(request, "No puedes publicar este programa.")
            return redirect("configure_program", pk=pk)

        if is_copiable and not caps.can_copy():
            messages.error(request, "Tu plan no permite copias.")
            return redirect("configure_program", pk=pk)

        try:
            duration_weeks = int(duration_weeks)
        except (TypeError, ValueError):
            messages.error(request, "La duración debe ser un número de semanas válido.")
            return redirect("configure_program", pk=pk)

        if duration_weeks < 1:
            messages.error(request, "La duración debe ser de al menos 1 semana.")
            return redirect("configure_program", pk=pk)

        max_filled_week = (
            program.program_dailyplan.order_by("-week_number").values_list("week_number", flat=True).first()
            or 1
        )
        if duration_weeks < max_filled_week:
            messages.error(request, "No puedes reducir la duración por debajo de la última semana con planes asignados.")
            return redirect("configure_program", pk=pk)

        program.is_public = is_public
        program.is_forkable = is_forkable
        program.is_copiable = is_copiable
        program.duration_weeks = duration_weeks

        if program.is_draft and program.program_dailyplan.exists():
            program.is_draft = False

        program.save(
            update_fields=[
                "is_public",
                "is_forkable",
                "is_copiable",
                "is_draft",
                "duration_weeks",
            ]
        )
        refresh_program_summary_cache(program)
        messages.success(request, "Programa guardado.")
        return redirect("program_detail", pk=pk)

    content = {
        "header": _header([
            _action(
                key="back_detail",
                label="Volver",
                url=reverse("program_detail", args=[program.id]),
                icon="chevron-left",
                order=10,
                is_back=True,
            )
        ]),
        "program": program,
        "caps": caps,
    }
    context = _vm_context(
        PROGRAM_VIEWMODE_CONFIGURE,
        content=content,
        instance=program,
    )
    return render(request, "notas/programs/configure.html", context)


# ==================================================
# SLOT ACTIONS
# ==================================================

@login_required
@require_POST
def add_dailyplan_to_program(request, pk):
    program = get_object_or_404(Program, pk=pk, created_by=request.user)

    dailyplan_id = request.POST.get("dailyplan_id")
    week_number = request.POST.get("week_number")
    day_numbers = [day for day in request.POST.getlist("day_numbers") if day]
    if not day_numbers:
        day_number = request.POST.get("day_number")
        day_numbers = [day_number] if day_number else []

    source_dailyplan = get_object_or_404(
        program_available_dailyplans(request.user),
        pk=dailyplan_id,
    )

    if not day_numbers:
        messages.error(request, "Debes seleccionar al menos un día.")
        return redirect("program_detail", pk=program.pk)

    try:
        for day_number in day_numbers:
            assign_dailyplan_to_program_slot(
                program=program,
                source_dailyplan=source_dailyplan,
                user=request.user,
                week_number=week_number,
                day_number=day_number,
            )
    except ValueError:
        messages.error(request, "La semana o el día seleccionado no es válido.")
        return redirect("program_detail", pk=program.pk)

    if len(day_numbers) == 1:
        messages.success(request, "Plan diario asignado al programa.")
    else:
        messages.success(request, "Plan diario asignado a los días seleccionados.")
    return redirect(f"{reverse('program_detail', args=[program.pk])}#week-{week_number}")


@login_required
@require_POST
def remove_dailyplan_from_program(request, pk, program_day_id):
    program_day = get_object_or_404(
        ProgramDay.objects.select_related("program", "dailyplan"),
        pk=program_day_id,
        program_id=pk,
        program__created_by=request.user,
    )
    week_number = program_day.week_number
    program = program_day.program

    remove_program_day(program_day=program_day)
    messages.success(request, "Día removido del programa.")
    return redirect(f"{reverse('program_detail', args=[program.pk])}#week-{week_number}")


@login_required
def program_day_card(request, pk, program_day_id):
    program_day = get_object_or_404(
        ProgramDay.objects
        .select_related(
            "program",
            "program__created_by",
            "program__original_author",
            "program__forked_from",
            "dailyplan",
            "dailyplan__created_by",
            "dailyplan__original_author",
            "dailyplan__forked_from",
        )
        .prefetch_related("dailyplan__dailyplan_meals__meal__meal_food_set__food"),
        pk=program_day_id,
        program_id=pk,
    )
    program = program_day.program

    if program.created_by_id != request.user.id and not program.shares.filter(
        accepted_by=request.user,
        removed=False,
    ).exists():
        return HttpResponseForbidden()

    card = build_program_day_child_card_vm(program_day.dailyplan, request.user, program_day=program_day)
    html = render_to_string(
        "components/program_day_selected_card.html",
        {
            "child_card": card,
            "week_number": program_day.week_number,
            "day_number": program_day.day_number,
        },
        request=request,
    )
    return JsonResponse({"html": html})


# ==================================================
# COPY / SHARE / DELETE
# ==================================================

@login_required
@require_POST
def fork_program(request, program_id):
    original = get_object_or_404(
        Program.objects.prefetch_related("program_dailyplan__dailyplan"),
        id=program_id,
    )

    if original.created_by_id != request.user.id and not original.is_forkable:
        return HttpResponseForbidden()

    forked = fork_program_command(original, request.user)
    messages.success(request, "Programa duplicado.")
    return redirect("program_detail", pk=forked.id)


@login_required
@require_POST
def copy_program(request, pk):
    program = get_object_or_404(
        Program.objects.prefetch_related("program_dailyplan__dailyplan"),
        pk=pk,
    )

    if program.created_by_id != request.user.id and not program.is_copiable:
        return HttpResponseForbidden()

    copied = copy_program_command(program, request.user)
    messages.success(request, "Programa copiado.")
    return redirect("program_detail", pk=copied.pk)


@login_required
@require_POST
def program_remove(request, pk):
    program = get_object_or_404(Program, pk=pk, created_by=request.user)
    delete_program(program=program)
    messages.success(request, "Programa eliminado.")
    return redirect(_safe_return_to(request, "program_list"))


@login_required
def program_share(request, pk):
    program = get_object_or_404(Program, pk=pk, created_by=request.user)
    form = ProgramShareForm(request.POST or None, initial={"subject": program.name})

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["recipient_email"]
        share_subject = form.cleaned_data.get("subject", program.name)
        message = form.cleaned_data.get("message", "")

        result = create_program_share(
            sender=request.user,
            recipient_email=email,
            program=program,
            subject=share_subject,
            message=message,
        )

        email_sent = False
        try:
            email_sent = bool(send_mail(
                subject=share_subject,
                message=message or f"Te compartieron el programa semanal {program.name} en My Scoope.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            ))
        except Exception:
            email_sent = False

        if result.share.accepted_by_id:
            messages.success(request, "Compartiste este programa. Ya está disponible para el usuario asociado a ese correo.")
        elif email_sent:
            messages.success(request, "Compartiste este programa y se envió el correo de invitación.")
        else:
            messages.warning(request, "Se creó la invitación, pero no se pudo enviar el correo.")

        return redirect("program_detail", pk=program.pk)

    if request.method == "POST":
        messages.error(request, "No se pudo compartir. Revisa el correo ingresado.")

    content = {
        "header": _header([
            _action(
                key="back_detail",
                label="Volver",
                url=reverse("program_detail", args=[program.id]),
                icon="chevron-left",
                order=10,
                is_back=True,
            )
        ]),
        "program": program,
        "form": form,
    }

    context = _vm_context(PROGRAM_VIEWMODE_SHARE, content=content, instance=program)
    return render(request, "notas/programs/share.html", context)
