from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.contrib import messages
from notas.application.services.access.capabilities import get_capabilities
from notas.domain.models import Meal, MealFood, Food, MealShare
from notas.presentation.config.viewmodel_config import *

import json
from django.core.serializers.json import DjangoJSONEncoder
from notas.application.services.nutrition.nutrition_kpis import build_nutrition_kpis_from_meal
from notas.presentation.viewmodels.meals import (
    build_meal_configure_vm,
    build_meal_detail_vm,
    build_meal_list_vm,
)
from notas.presentation.composition.js.food_picker_builder import build_food_picker_foods_payload, build_food_picker_context_payload
from notas.application.queries.performance.meal_queries import meals_with_kcal

from notas.interface.forms.forms import MealShareForm
from django.conf import settings
from email_delivery.services import deliver_share_invitation
from django.urls import reverse
from notas.application.services.notifications.share_emails import build_share_invitation_email

from notas.presentation.viewmodels.base_vm import BaseVM
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.pages.meal_pages import get_meal_detail_page_data

from notas.presentation.pages.meal_pages import (
    get_meal_detail_page_data,
    get_meal_list_page_data,
    get_meal_explore_list_page_data,
    get_meal_shared_list_page_data,
    get_meal_draft_list_page_data,
)

from notas.application.services.commands.meal_commands import (
    configure_meal,
    copy_meal,
    create_draft_meal,
    delete_draft_meal,
    delete_meal,
    finish_meal_for_pending_dailyplan,
    fork_meal_for_library,
    rename_meal,
    save_food_in_meal,
    save_meal,
)

from notas.application.services.commands.share_commands import (
    accept_meal_share,
    create_meal_share,
    dismiss_meal_share,
    remove_meal_share,
)

from notas.application.services.access.access import get_meal_for_user

from django.utils.http import url_has_allowed_host_and_scheme

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
def meal_share(request, pk):

    meal = get_object_or_404(
        Meal,
        pk=pk,
        created_by=request.user
    )

    # Solo el dueño puede compartir
    if meal.created_by != request.user:
        return HttpResponseForbidden()

    form = MealShareForm(request.POST or None, initial={"subject": meal.name})

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["recipient_email"]
        share_subject = form.cleaned_data.get("subject", meal.name)
        message = form.cleaned_data.get("message", "")

        result = create_meal_share(
            sender=request.user,
            recipient_email=email,
            meal=meal,
            subject=share_subject,
            message=message,
        )

        share = result.share

        subject, message = build_share_invitation_email(
            request=request,
            share=share,
            kind="meal",
            item_name=meal.name,
            custom_subject=share_subject,
            custom_message=message,
        )

        delivery = deliver_share_invitation(
            share=share,
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
        )

        if share.accepted_by_id:
            messages.success(
                request,
                "Compartiste esta comida. Como el correo pertenece a una cuenta existente, ya está disponible en su Inbox.",
            )
        elif delivery.sent:
            messages.success(
                request,
                "Compartiste esta comida. Enviamos el correo de invitación al destinatario.",
            )
        elif delivery.reason == "duplicate_share":
            messages.success(
                request,
                "Esta comida ya estaba compartida. No reenviamos el correo para evitar duplicados.",
            )
        else:
            messages.warning(
                request,
                "Se creó la invitación, pero la política de correo no permitió enviarla.",
            )

        return redirect("meal_detail", pk=meal.pk)

    if request.method == "POST":
        messages.error(request, "No se pudo compartir. Revisa el correo ingresado.")

    return render(
        request,
        "notas/meals/share.html",
        {"meal": meal, "form": form},
    )


@login_required
def meal_share_accept(request, token):
    share = get_object_or_404(
        MealShare,
        token=token,
    )

    accept_meal_share(
        share=share,
        user=request.user,
    )

    return redirect("inbox_list")


@login_required
def meal_share_dismiss(request, share_id):
    share = get_object_or_404(
        MealShare,
        id=share_id,
        accepted_by=request.user,
    )

    if request.method == "POST":
        dismiss_meal_share(
            share=share,
        )

    return redirect("meal_shared_list")


@login_required
@require_POST
def meal_unshare(request, share_id):

    share = get_object_or_404(
        MealShare,
        id=share_id,
        accepted_by=request.user,
    )

    remove_meal_share(
        share=share,
    )

    messages.success(request, "Meal removida de Shared with me.")
    return redirect("meal_shared_list")



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
def meal_list_reorder(request):
    ordered_ids = request.POST.getlist("order[]")

    if not ordered_ids:
        return HttpResponseBadRequest("No order received.")

    meals = {
        meal.id: meal
        for meal in Meal.objects.filter(
            created_by=request.user,
            is_draft=False,
            dailyplanmeal__isnull=True,
            id__in=ordered_ids,
        ).distinct()
    }

    for index, raw_id in enumerate(ordered_ids):
        try:
            meal_id = int(raw_id)
        except (TypeError, ValueError):
            continue

        meal = meals.get(meal_id)
        if not meal:
            continue

        if meal.list_order != index:
            meal.list_order = index
            meal.save(update_fields=["list_order"])

    return HttpResponse(status=204)


@login_required
@require_POST
def meal_list_bulk_delete(request):
    selected_ids = request.POST.getlist("selected_ids[]")

    if not selected_ids:
        messages.info(request, "No seleccionaste comidas para eliminar.")
        return redirect(_safe_return_to(request, "meal_list", mode="delete"))

    meals = Meal.objects.filter(
        created_by=request.user,
        is_draft=False,
        dailyplanmeal__isnull=True,
        id__in=selected_ids,
    ).distinct()

    deleted_count = 0

    for meal in meals:
        delete_meal(meal=meal)
        deleted_count += 1

    if deleted_count:
        messages.success(request, f"{deleted_count} comida(s) eliminada(s).")
    else:
        messages.info(request, "No se eliminaron comidas.")

    return redirect(_safe_return_to(request, "meal_list", mode="delete"))

#************ RENDER COMPLEJOS *********************

# LIST VIEWS ···················

@login_required
def meal_list(request):
    page = get_meal_list_page_data(
        user=request.user,
        request_get=request.GET,
    )

    content_vm = build_meal_list_vm(
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
        "notas/meals/list.html",
        base_vm.as_context(),
    )


@login_required
def meal_explore_list(request):
    page = get_meal_explore_list_page_data(
        user=request.user,
    )

    content_vm = build_meal_list_vm(
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
        "notas/meals/list.html",
        base_vm.as_context(),
    )


@login_required
def meal_shared_list(request):
    page = get_meal_shared_list_page_data(
        user=request.user,
    )

    content_vm = build_meal_list_vm(
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
        "notas/meals/list.html",
        base_vm.as_context(),
    )


@login_required
def meal_draft_list(request):
    page = get_meal_draft_list_page_data(
        user=request.user,
    )

    content_vm = build_meal_list_vm(
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
        "notas/meals/list.html",
        base_vm.as_context(),
    )





# DETAIL VIEWS ···················

@login_required
def meal_detail(request, pk):

    page = get_meal_detail_page_data(
        user=request.user,
        meal_id=pk,
        viewmode=MEAL_VIEWMODE_PERSONAL_DETAIL,
        request_get=request.GET,
    )

    meal = page.meal

    if request.method == "POST":

        if "finish_for_dailyplan" in request.POST:
            result = finish_meal_for_pending_dailyplan(
                meal=meal,
            )

            if result.completed:
                return redirect(
                    reverse("dailyplan_detail", args=[result.dailyplan_id]) +
                    f"?select_meal={result.meal.id}"
                )

        elif "save_food" in request.POST:
            mealfood_id = request.POST.get("mealfood_id")
            quantity = request.POST.get("quantity")
            food_id = request.POST.get("food_id")

            try:
                result = save_food_in_meal(
                    meal=meal,
                    mealfood_id=mealfood_id,
                    food_id=food_id,
                    quantity=quantity,
                )
            except MealFood.DoesNotExist:
                raise Http404("MealFood not found")

            return redirect("meal_detail", pk=result.meal.id)


    content_vm = build_meal_detail_vm(
        page.detail_content_data,
    )

    ui_vm = build_ui_vm(
        page.viewmode,
        instance=page.meal,
    )

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    context = base_vm.as_context()

    context["show_return_to_dailyplan"] = page.show_return_to_dailyplan
    context["foods_json"] = page.foods_json
    context["food_picker_context"] = page.food_picker_context_json
    context["can_edit_foods"] = page.can_edit_foods
    context["editing_mealfood_id"] = page.editing_mealfood_id
    context["selected_food_id"] = page.selected_food_id

    return render(
        request,
        "notas/meals/detail.html",
        context,
    )



@login_required
def meal_explore_detail(request, pk, dailyplan_id=None):

    page = get_meal_detail_page_data(
        user=request.user,
        meal_id=pk,
        viewmode=MEAL_VIEWMODE_EXPLORE_DETAIL,
    )

    content_vm = build_meal_detail_vm(
        page.detail_content_data,
    )

    ui_vm = build_ui_vm(
        page.viewmode,
        instance=page.meal,
    )

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/meals/detail.html",
        base_vm.as_context(),
    )


@login_required
def meal_share_detail(request, pk, dailyplan_id=None):

    page = get_meal_detail_page_data(
        user=request.user,
        meal_id=pk,
        viewmode=MEAL_VIEWMODE_SHARED_DETAIL,
    )

    content_vm = build_meal_detail_vm(
        page.detail_content_data,
    )

    ui_vm = build_ui_vm(
        page.viewmode,
        instance=page.meal,
    )

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/meals/detail.html",
        base_vm.as_context(),
    )


#************ RENDER BÁSICOS *********************
# ---------- CREATE - RENAME - CONFIGURE ----------

@login_required
def meal_create(request):
    from_dailyplan = request.GET.get("from_dailyplan")

    if request.method == "POST":
        name = request.POST.get("name")

        try:
            result = create_draft_meal(
                user=request.user,
                name=name,
                pending_dailyplan_id=from_dailyplan,
            )
        except ValueError:
            messages.error(request, "El nombre es obligatorio")
            return redirect("meal_create")

        return redirect("meal_detail", pk=result.meal.id)

    viewmode = MEAL_VIEWMODE_CREATE

    ui_vm = build_ui_vm(viewmode)

    base_vm = BaseVM(
        ui=ui_vm,
        content=None,
    )

    return render(
        request,
        "notas/meals/create.html",
        base_vm.as_context(),
    )


@login_required
def meal_rename(request, pk):
    meal = get_object_or_404(
        Meal,
        pk=pk,
        created_by=request.user,
    )

    return_to = (
        request.POST.get("return_to")
        or request.GET.get("return_to")
        or ""
    )

    fallback_url = reverse("meal_detail", kwargs={"pk": meal.pk})

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
            rename_meal(
                meal=meal,
                name=name,
            )
        except ValueError:
            messages.error(request, "El nombre no puede estar vacío.")
            return redirect(
                f"{reverse('meal_rename', kwargs={'pk': meal.pk})}?return_to={return_to}"
            )

        messages.success(request, "Nombre actualizado correctamente.")
        return redirect(redirect_url)

    header = {"title": "Edit meal name"}

    return render(request, "notas/meals/rename.html", {
        "meal": meal,
        "header": header,
        "return_to": return_to,
    })

@login_required
def meal_configure(request, pk):

    meal = get_object_or_404(
        Meal,
        pk=pk,
        created_by=request.user,
    )

    user = request.user
    caps = get_capabilities(user)

    if not caps or not caps.can_access_distribution_settings():
        messages.error(request, "Your plan cannot configure meal distribution.")
        return redirect("meal_detail", pk=pk)

    # =====================
    # POST
    # =====================
    if request.method == "POST":

        is_public = bool(request.POST.get("is_public"))
        is_forkable = bool(request.POST.get("is_forkable"))
        is_copiable = bool(request.POST.get("is_copiable"))

        if is_public and not caps.can_publish():
            messages.error(request, "You cannot publish this meal.")
            return redirect("meal_configure", pk=pk)

        if is_copiable and not caps.can_copy():
            messages.error(request, "Your plan does not allow copies.")
            return redirect("meal_configure", pk=pk)

        result = configure_meal(
            meal=meal,
            is_public=is_public,
            is_forkable=is_forkable,
            is_copiable=is_copiable,
        )

        if result.completed_from_pending_dailyplan:
            messages.success(
                request,
                "Meal saved and added to your DailyPlan."
            )

            return redirect(
                "dailyplan_detail",
                pk=result.origin_dailyplan_id,
            )

        messages.success(request, "Configuration saved")
        return redirect("meal_detail", pk=result.meal.pk)
        
    # =====================
    # VIEWMODEL
    # =====================

    viewmode = MEAL_VIEWMODE_CONFIGURE

    content_vm = build_meal_configure_vm(
        meal,
        user,
        viewmode
    )

    ui_vm = build_ui_vm(
        viewmode,
        instance=meal
    )

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm
    )

    context = base_vm.as_context()

    return render(
        request,
        "notas/meals/configure.html",
        context
    )

#************ ACCIONES (NO RENDERIZAN) **************
# ---------- FORK - COPY ----------


@login_required
@require_POST
def meal_fork(request, meal_id):

    original = get_object_or_404(Meal, id=meal_id)

    if not original.is_forkable:
        return HttpResponseForbidden("No puedes forkear esta meal")

    forked = fork_meal_for_library(original, request.user)

    messages.success(request, "Meal guardada en tu biblioteca")
    return redirect("meal_detail", pk=forked.pk)


@login_required
@require_POST
def meal_save(request, meal_id):

    original = get_meal_for_user(request.user, meal_id)

    if not original.is_forkable:
        return HttpResponseForbidden("No puedes guardar esta meal")

    saved = save_meal(original, request.user)

    messages.success(request, "Meal guardada en tu biblioteca")
    return redirect("meal_detail", pk=saved.pk)



@login_required
@require_POST
def meal_copy(request, pk):

    original = get_object_or_404(Meal, pk=pk)

    if not original.is_copiable:
        return HttpResponseForbidden("No tienes permiso para copiar esta meal")

    copy = copy_meal(original, request.user)

    messages.success(request, "Meal copiada correctamente")
    return redirect("meal_detail", pk=copy.pk)


@login_required
@require_POST
def meal_remove(request, pk):
    meal = get_object_or_404(
        Meal,
        pk=pk,
        created_by=request.user,
    )

    delete_meal(meal=meal)

    messages.success(request, "Meal removida de tu lista.")
    return redirect(_safe_return_to(request, "meal_list", mode="delete"))


@login_required
@require_POST
def meal_draft_delete(request, pk):
    meal = get_object_or_404(
        Meal,
        pk=pk,
        created_by=request.user,
        is_draft=True,
    )

    delete_draft_meal(meal=meal)

    messages.success(request, "Draft eliminado definitivamente.")
    return redirect("meal_draft_list")
