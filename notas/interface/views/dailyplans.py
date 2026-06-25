from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from notas.domain.models import DailyPlan, DailyPlanMeal, Meal, DailyPlanShare
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from notas.presentation.config.viewmodel_config import *

from notas.application.services.access.capabilities import get_capabilities
from notas.application.services.nutrition.nutrition_kpis import build_nutrition_kpis_from_dailyplan

import json
from django.core.serializers.json import DjangoJSONEncoder
from notas.presentation.viewmodels.dailyplans import (
    build_dailyplan_configure_vm,
    build_dailyplan_detail_vm,
    build_dailyplan_list_vm,
)
from notas.application.services.queries.dailyplan_queries import dailyplans_with_kcal, get_dailyplan_for_edit
from notas.application.services.queries.meal_queries import meals_with_kcal

from notas.application.services.access.access import get_dailyplan_for_user

from notas.interface.forms.forms import DailyPlanShareForm
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from notas.application.services.notifications.share_emails import build_share_invitation_email
from django.utils.http import url_has_allowed_host_and_scheme

from notas.presentation.viewmodels.base_vm import BaseVM
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm

from notas.presentation.pages.dailyplan_pages import (
    get_dailyplan_detail_page_data,
    get_dailyplan_list_page_data,
    get_dailyplan_explore_list_page_data,
    get_dailyplan_shared_list_page_data,
    get_dailyplan_draft_list_page_data,
)

from notas.application.services.commands.dailyplan_commands import (
    configure_dailyplan,
    copy_dailyplan,
    create_draft_dailyplan,
    create_pending_meal_for_dailyplan,
    delete_dailyplan,
    fork_dailyplan,
    rename_dailyplan,
    save_dailyplan,
)

from notas.application.services.commands.share_commands import (
    accept_dailyplan_share,
    create_dailyplan_share,
    dismiss_dailyplan_share,
    remove_dailyplan_share,
)

from dataclasses import dataclass


@dataclass(frozen=True)
class BreadcrumbParent:
    label: str
    url: str

    def __str__(self):
        return self.label

    def get_absolute_url(self):
        return self.url

#************ VIEW DE INBOX *********************

@login_required
def dailyplan_share(request, pk):

    dailyplan = get_object_or_404(
        DailyPlan,
        pk=pk,
        created_by=request.user
    )

    # Solo el dueño puede compartir
    if dailyplan.created_by != request.user:
        return HttpResponseForbidden()

    form = DailyPlanShareForm(request.POST or None, initial={"subject": dailyplan.name})

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["recipient_email"]
        share_subject = form.cleaned_data.get("subject", dailyplan.name)
        message = form.cleaned_data.get("message", "")

        result = create_dailyplan_share(
            sender=request.user,
            recipient_email=email,
            dailyplan=dailyplan,
            subject=share_subject,
            message=message,
        )

        share = result.share

        subject, message = build_share_invitation_email(
            request=request,
            share=share,
            kind="dailyplan",
            item_name=dailyplan.name,
            custom_subject=share_subject,
            custom_message=message,
        )

        email_sent = False
        try:
            email_sent = bool(send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            ))
        except Exception:
            email_sent = False

        if share.accepted_by_id:
            messages.success(
                request,
                "Compartiste este plan diario. Como el correo pertenece a una cuenta existente, ya está disponible en su Inbox.",
            )
        elif email_sent:
            messages.success(
                request,
                "Compartiste este plan diario. Enviamos el correo de invitación al destinatario.",
            )
        else:
            messages.warning(
                request,
                "Se creó la invitación, pero no se pudo enviar el correo. Revisa la configuración de email.",
            )

        return redirect("dailyplan_detail", pk=dailyplan.pk)

    if request.method == "POST":
        messages.error(request, "No se pudo compartir. Revisa el correo ingresado.")

    return render(
        request,
        "notas/dailyplans/share.html",
        {"dailyplan": dailyplan, "form": form},
    )


@login_required
def dailyplan_share_accept(request, token):
    share = get_object_or_404(
        DailyPlanShare,
        token=token,
    )

    accept_dailyplan_share(
        share=share,
        user=request.user,
    )

    return redirect("inbox_list")


@login_required
def dailyplan_share_dismiss(request, share_id):
    share = get_object_or_404(
        DailyPlanShare,
        id=share_id,
        accepted_by=request.user,
    )

    if request.method == "POST":
        dismiss_dailyplan_share(
            share=share,
        )

    return redirect("dailyplan_shared_list")


@login_required
@require_POST
def dailyplan_unshare(request, share_id):
    share = get_object_or_404(
        DailyPlanShare,
        id=share_id,
        accepted_by=request.user,
    )

    remove_dailyplan_share(
        share=share,
    )

    return redirect("dailyplan_shared_list")




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


@login_required
@require_POST
def dailyplan_list_reorder(request):
    ordered_ids = request.POST.getlist("order[]")

    if not ordered_ids:
        return HttpResponseBadRequest("No order received.")

    dailyplans = {
        dailyplan.id: dailyplan
        for dailyplan in DailyPlan.objects.filter(
            created_by=request.user,
            is_draft=False,
            id__in=ordered_ids,
        )
    }

    for index, raw_id in enumerate(ordered_ids):
        try:
            dailyplan_id = int(raw_id)
        except (TypeError, ValueError):
            continue

        dailyplan = dailyplans.get(dailyplan_id)
        if not dailyplan:
            continue

        if dailyplan.list_order != index:
            dailyplan.list_order = index
            dailyplan.save(update_fields=["list_order"])

    return HttpResponse(status=204)


@login_required
@require_POST
def dailyplan_list_bulk_delete(request):
    selected_ids = request.POST.getlist("selected_ids[]")

    if not selected_ids:
        messages.info(request, "No seleccionaste planes para eliminar.")
        return redirect(_safe_return_to(request, "dailyplan_list", mode="delete"))

    dailyplans = DailyPlan.objects.filter(
        created_by=request.user,
        is_draft=False,
        id__in=selected_ids,
    )

    deleted_count = 0

    for dailyplan in dailyplans:
        try:
            delete_dailyplan(dailyplan=dailyplan)
            deleted_count += 1
        except ValueError:
            continue

    if deleted_count:
        messages.success(request, f"{deleted_count} plan(es) eliminado(s).")
    else:
        messages.info(request, "No se eliminaron planes.")

    return redirect(_safe_return_to(request, "dailyplan_list", mode="delete"))

#************ RENDER COMPLEJOS *********************

@login_required
def dailyplan_list(request):
    page = get_dailyplan_list_page_data(
        user=request.user,
        request_get=request.GET,
    )

    content_vm = build_dailyplan_list_vm(
        page.list_content_data,
        page_actions=page.page_actions,
        list_mode=page.list_mode,
    )

    ui_vm = build_ui_vm(page.viewmode)

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/dailyplans/list.html",
        base_vm.as_context(),
    )


@login_required
def dailyplan_explore_list(request):
    page = get_dailyplan_explore_list_page_data(
        user=request.user,
    )

    content_vm = build_dailyplan_list_vm(
        page.list_content_data,
        page_actions=page.page_actions,
    )

    ui_vm = build_ui_vm(page.viewmode)

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/dailyplans/list.html",
        base_vm.as_context(),
    )


@login_required
def dailyplan_shared_list(request):
    page = get_dailyplan_shared_list_page_data(
        user=request.user,
    )

    content_vm = build_dailyplan_list_vm(
        page.list_content_data,
        page_actions=page.page_actions,
    )

    ui_vm = build_ui_vm(page.viewmode)

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/dailyplans/list.html",
        base_vm.as_context(),
    )


@login_required
def dailyplan_draft_list(request):
    page = get_dailyplan_draft_list_page_data(
        user=request.user,
    )

    content_vm = build_dailyplan_list_vm(
        page.list_content_data,
        page_actions=page.page_actions,
    )

    ui_vm = build_ui_vm(page.viewmode)

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/dailyplans/list.html",
        base_vm.as_context(),
    )

# DETAIL VIEWS ···················

@login_required
def dailyplan_detail(request, pk):

    page = get_dailyplan_detail_page_data(
        user=request.user,
        dailyplan_id=pk,
        viewmode=DAILYPLAN_VIEWMODE_PERSONAL_DETAIL,
        request_get=request.GET,
    )

    content_vm = build_dailyplan_detail_vm(
        page.detail_content_data,
    )

    ui_vm = build_ui_vm(
        page.viewmode,
        instance=page.dailyplan,
    )

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    context = base_vm.as_context()
    context["meal_picker_data_json"] = page.meal_picker_data_json
    context["meal_picker_context"] = page.meal_picker_context_json
    context["selected_meal_id"] = page.selected_meal_id
    context["editing_dailyplanmeal_id"] = page.editing_dailyplanmeal_id

    return render(
        request,
        "notas/dailyplans/detail.html",
        context,
    )


@login_required
def dailyplan_explore_detail(request, pk):

    page = get_dailyplan_detail_page_data(
        user=request.user,
        dailyplan_id=pk,
        viewmode=DAILYPLAN_VIEWMODE_EXPLORE_DETAIL,
    )

    content_vm = build_dailyplan_detail_vm(
        page.detail_content_data,
    )

    ui_vm = build_ui_vm(
        page.viewmode,
        instance=page.dailyplan,
    )

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/dailyplans/detail.html",
        base_vm.as_context(),
    )

@login_required
def dailyplan_shared_detail(request, pk):

    page = get_dailyplan_detail_page_data(
        user=request.user,
        dailyplan_id=pk,
        viewmode=DAILYPLAN_VIEWMODE_SHARED_DETAIL,
    )

    content_vm = build_dailyplan_detail_vm(
        page.detail_content_data,
    )

    ui_vm = build_ui_vm(
        page.viewmode,
        instance=page.dailyplan,
    )

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/dailyplans/detail.html",
        base_vm.as_context(),
    )

@login_required
def dailyplan_draft_detail(request, pk):

    page = get_dailyplan_detail_page_data(
        user=request.user,
        dailyplan_id=pk,
        viewmode=DAILYPLAN_VIEWMODE_DRAFT_DETAIL,
    )

    content_vm = build_dailyplan_detail_vm(
        page.detail_content_data,
    )

    ui_vm = build_ui_vm(
        page.viewmode,
        instance=page.dailyplan,
    )

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/dailyplans/detail.html",
        base_vm.as_context(),
    )


#************ RENDER DE EDICION *********************
# ---------- EDIT - BUILDER ----------


@login_required
def dailyplan_draft_edit(request, pk):

    page = get_dailyplan_detail_page_data(
        user=request.user,
        dailyplan_id=pk,
        request_get=request.GET,
        is_draft=True,
    )

    content_vm = build_dailyplan_detail_vm(
        page.detail_content_data,
    )

    ui_vm = build_ui_vm(
        page.viewmode,
        instance=page.dailyplan,
    )

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    context = base_vm.as_context()
    context["meal_picker_data_json"] = page.meal_picker_data_json
    context["meal_picker_context"] = page.meal_picker_context_json
    context["selected_meal_id"] = page.selected_meal_id
    context["editing_dailyplanmeal_id"] = page.editing_dailyplanmeal_id

    return render(
        request,
        "notas/dailyplans/edit.html",
        context,
    )



#************ RENDER BÁSICOS *********************
# ---------- CREATE - RENAME - CONFIGURE ----------

@login_required
def dailyplan_create(request):
    viewmode = DAILYPLAN_VIEWMODE_CREATE

    ui_vm = build_ui_vm(viewmode)

    base_vm = BaseVM(
        ui=ui_vm,
        content=None,
    )

    if request.method == "POST":
        name = request.POST.get("name")

        try:
            result = create_draft_dailyplan(
                user=request.user,
                name=name,
            )
        except ValueError:
            messages.error(request, "El nombre es obligatorio")
            return redirect("dailyplan_create")

        return redirect("dailyplan_detail", pk=result.dailyplan.pk)

    return render(
        request,
        "notas/dailyplans/create.html",
        base_vm.as_context(),
    )

@login_required
def dailyplan_rename(request, pk):
    dailyplan = get_object_or_404(
        DailyPlan,
        pk=pk,
        created_by=request.user,
    )

    if request.method == "POST":
        name = request.POST.get("name", "")

        try:
            rename_dailyplan(
                dailyplan=dailyplan,
                name=name,
            )
        except ValueError:
            messages.error(request, "El nombre no puede estar vacío.")
            return redirect("dailyplan_rename", pk=pk)

        messages.success(request, "Nombre actualizado.")
        return redirect("dailyplan_detail", pk=pk)

    return render(
        request,
        "notas/dailyplans/rename.html",
        {"dailyplan": dailyplan}
    )


@login_required
def dailyplan_configure(request, pk):

    dailyplan = get_object_or_404(
        DailyPlan,
        pk=pk,
        created_by=request.user,
    )

    user = request.user
    caps = get_capabilities(user)

    if not caps or not caps.can_access_distribution_settings():
        messages.error(request, "Your plan cannot configure daily plan distribution.")
        return redirect("dailyplan_detail", pk=pk)

    # =====================
    # POST
    # =====================
    if request.method == "POST":

        is_public = bool(request.POST.get("is_public"))
        is_forkable = bool(request.POST.get("is_forkable"))
        is_copiable = bool(request.POST.get("is_copiable"))

        if is_public and not caps.can_publish():
            messages.error(request, "You cannot publish this daily plan.")
            return redirect("dailyplan_configure", pk=pk)

        if is_copiable and not caps.can_copy():
            messages.error(request, "Your plan does not allow copies.")
            return redirect("dailyplan_configure", pk=pk)

        result = configure_dailyplan(
            dailyplan=dailyplan,
            is_public=is_public,
            is_forkable=is_forkable,
            is_copiable=is_copiable,
        )

        messages.success(request, "Configuración guardada")

        return redirect("dailyplan_detail", pk=result.dailyplan.pk)

    # =====================
    # VIEWMODEL
    # =====================

    viewmode = DAILYPLAN_VIEWMODE_CONFIGURE

    content_vm = build_dailyplan_configure_vm(
        dailyplan,
        user,
        viewmode,
    )

    ui_vm = build_ui_vm(
        viewmode,
        instance=dailyplan,
    )

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/dailyplans/configure.html",
        base_vm.as_context(),
    )


#************ ACCIONES (NO RENDERIZAN) **************
# ---------- FORK - COPY ----------

@login_required
@require_POST
def dailyplan_fork(request, dailyplan_id):

    original = get_dailyplan_for_user(request.user, dailyplan_id)

    if not original.is_forkable:
        return HttpResponseForbidden("No puedes forkear este daily plan")

    forked = fork_dailyplan(original, request.user)

    messages.success(request, "Daily plan guardado en tu biblioteca")
    return redirect("dailyplan_detail", pk=forked.pk)


@login_required
@require_POST
def dailyplan_save(request, dailyplan_id):

    original = get_dailyplan_for_user(request.user, dailyplan_id)

    if not original.is_forkable:
        return HttpResponseForbidden("No puedes guardar este daily plan")

    saved = save_dailyplan(original, request.user)

    messages.success(request, "Daily plan guardado en tu biblioteca")
    return redirect("dailyplan_list")



@login_required
@require_POST
def dailyplan_copy(request, pk):

    dailyplan = get_dailyplan_for_user(request.user, pk)

    if not dailyplan.is_copiable:
        return HttpResponseForbidden()

    copy = copy_dailyplan(dailyplan, request.user)

    messages.success(request, "Daily plan copied successfully")
    return redirect("dailyplan_detail", pk=copy.pk)


#CREATE MEAL DESDE EDIT DAILYPLAN
@login_required
def create_meal_for_dailyplan(request, dailyplan_id):

    dailyplan = get_object_or_404(
        DailyPlan,
        pk=dailyplan_id,
        created_by=request.user,
    )

    if request.method == "POST":
        name = request.POST.get("name")

        try:
            result = create_pending_meal_for_dailyplan(
                dailyplan=dailyplan,
                user=request.user,
                name=name,
            )
        except ValueError:
            messages.error(request, "Name is required")
            return redirect("create_meal_for_dailyplan", dailyplan_id=dailyplan.id)

        return redirect("meal_detail", pk=result.meal.id)

    return render(
        request,
        "notas/meals/create.html",
        {"dailyplan": dailyplan},
    )


#ADD MEAL FROM MEAL_LIST (SELECT DAILYPLAN AND SET HOUR-NOTA)
@login_required
def add_meal_from_list(request, meal_id):
    """
    Paso intermedio:
    - elegir dailyplan
    - definir hora
    - agregar nota
    """
    meal = get_object_or_404(Meal, pk=meal_id)

    # 🔹 solo MIS dailyplans (drafts por ahora)
    dailyplans = (
        DailyPlan.objects
        .filter(created_by=request.user)
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .order_by("-created_at")
    )

    return render(
        request,
        "notas/dailyplans/add_meal_from_list.html",
        {
            "meal": meal,
            "dailyplans": dailyplans,
        },
    )



#----

@login_required
@require_POST
def dailyplan_remove(request, pk):
    dailyplan = get_object_or_404(
        DailyPlan,
        pk=pk,
        created_by=request.user,
    )

    try:
        delete_dailyplan(
            dailyplan=dailyplan,
        )
    except ValueError:
        return HttpResponseForbidden(
            "No puedes eliminar un plan público."
        )

    messages.success(request, "Plan eliminado definitivamente.")

    return redirect(_safe_return_to(request, "dailyplan_list", mode="delete"))



