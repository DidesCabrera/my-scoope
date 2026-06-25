from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.contrib import messages
from notas.application.services.access.capabilities import get_capabilities
from notas.domain.models import Meal, MealFood, DailyPlan, DailyPlanMeal, Food, DailyPlanMealShare
from notas.presentation.config.viewmodel_config import (
    DAILYPLAN_MEAL_VIEWMODE_EDIT,
    DAILYPLAN_MEAL_VIEWMODE_DRAFT_DEEP_EDIT,
    DAILYPLAN_MEAL_VIEWMODE_DETAIL,
)
from notas.presentation.composition.viewmodel.dpm.detail_dpm_builder import build_dpm_detail_vm
from notas.presentation.composition.js.dpm_food_picker_builder import build_dpm_food_picker_context_payload
from notas.presentation.composition.js.food_picker_builder import build_food_picker_foods_payload
from notas.application.services.nutrition.nutrition_kpis import build_nutrition_kpis_from_meal, build_nutrition_kpis_from_dailyplan
import json
from django.core.serializers.json import DjangoJSONEncoder

from notas.presentation.viewmodels.base_vm import BaseVM
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.composition.viewmodel.components.builder_headers import build_page_header
from notas.application.services.commands.meal_commands import (
    fork_meal_for_dailyplan,
    save_dailyplan_meal_to_library,
    save_food_in_meal,
)

from django.urls import reverse
from notas.interface.forms.forms import DailyPlanMealShareForm
from notas.application.services.commands.share_commands import (
    accept_dailyplanmeal_share,
    create_dailyplanmeal_share,
)
from django.core.mail import send_mail
from django.conf import settings
from notas.application.services.notifications.share_emails import build_share_invitation_email

from notas.presentation.pages.dpm_pages import (
    get_dpm_detail_page_data,
    get_dpm_edit_page_data,
)

from django.http import HttpResponseForbidden, JsonResponse
from django.db import transaction

from notas.application.services.commands.dailyplan_commands import (
    add_existing_meal_to_dailyplan,
    create_empty_meal_for_dailyplan_meal,
    remove_dailyplan_meal,
    reorder_dailyplan_meals,
    update_dailyplan_meal,
)


@login_required
@require_POST
def dailyplanmeal_reorder(request, dailyplan_id):
    dailyplan = get_object_or_404(
        DailyPlan,
        pk=dailyplan_id,
        created_by=request.user,
    )

    ordered_ids = request.POST.getlist("order[]")

    result = reorder_dailyplan_meals(
        dailyplan=dailyplan,
        ordered_ids=ordered_ids,
    )

    return JsonResponse(
        {
            "ok": True,
            "updated_count": result.updated_count,
        }
    )
    
#************ RENDER COMPLEJOS *********************
# ---------- DETAIL (NO HAY LIST)  ----------

@login_required
def dailyplan_meal_detail(request, dailyplan_id, pk):

    page = get_dpm_detail_page_data(
        user=request.user,
        dailyplan_id=dailyplan_id,
        dpm_id=pk,
        viewmode=DAILYPLAN_MEAL_VIEWMODE_DETAIL,
        request_get=request.GET,
    )

    caps = get_capabilities(request.user)

    if request.method == "POST" and "save_food" in request.POST:
        if not caps or not caps.can_edit_own_content():
            return HttpResponseForbidden("You cannot edit this meal")

        try:
            save_food_in_meal(
                meal=page.meal,
                mealfood_id=request.POST.get("mealfood_id"),
                food_id=request.POST.get("food_id"),
                quantity=request.POST.get("quantity"),
            )
        except MealFood.DoesNotExist:
            raise Http404("MealFood not found")

        page = get_dpm_detail_page_data(
            user=request.user,
            dailyplan_id=dailyplan_id,
            dpm_id=pk,
            viewmode=DAILYPLAN_MEAL_VIEWMODE_DETAIL,
            request_get=request.GET,
        )

    content_vm = build_dpm_detail_vm(
        page.detail_content_data,
    )

    ui_vm = build_ui_vm(
        page.viewmode,
        parents=[page.dailyplan],
        instance=page.meal,
        back_config={
            "type": "url",
            "value": reverse(
                "dailyplan_detail",
                args=[page.dailyplan.id],
            ),
        },
    )

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    context = base_vm.as_context()
    context["foods_json"] = page.foods_json
    context["food_picker_json"] = page.food_picker_context_json
    context["can_edit_foods"] = page.can_edit_foods
    context["selected_food_id"] = page.selected_food_id
    context["editing_mealfood_id"] = page.editing_mealfood_id

    return render(
        request,
        "notas/dailyplan_meals/detail.html",
        context,
    )



# ---------- EDIT - DEEP EDIT ----------

@login_required
def dailyplan_meal_edit(request, dailyplan_id, dailyplanmeal_id):

    page = get_dpm_edit_page_data(
        user=request.user,
        dailyplan_id=dailyplan_id,
        dpm_id=dailyplanmeal_id,
        viewmode=DAILYPLAN_MEAL_VIEWMODE_EDIT,
    )

    if request.method == "POST":
        result = update_dailyplan_meal(
            dailyplan_meal=page.dpm,
            user=request.user,
            hour=request.POST.get("hour"),
            note=request.POST.get("note"),
        )

        return redirect(
            "dailyplan_meal_detail",
            dailyplan_id=result.dailyplan.id,
            pk=result.dailyplan_meal.id,
        )

    content_vm = build_dpm_detail_vm(
        page.detail_content_data,
    )

    ui_vm = build_ui_vm(
        page.viewmode,
        instance=page.dpm,
    )

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/dailyplan_meals/edit.html",
        base_vm.as_context(),
    )

@login_required
def dailyplanmeal_draft_deepedit(request, dailyplan_id, dailyplanmeal_id):

    page = get_dpm_detail_page_data(
        user=request.user,
        dailyplan_id=dailyplan_id,
        dpm_id=dailyplanmeal_id,
        request_get=request.GET,
        viewmode=DAILYPLAN_MEAL_VIEWMODE_DRAFT_DEEP_EDIT,
    )

    caps = get_capabilities(request.user)
    if not caps or not caps.can_edit_own_content():
        return HttpResponseForbidden("You cannot edit this meal")

    if request.method == "POST" and "save_food" in request.POST:
        try:
            save_food_in_meal(
                meal=page.meal,
                mealfood_id=request.POST.get("mealfood_id"),
                food_id=request.POST.get("food_id"),
                quantity=request.POST.get("quantity"),
            )
        except MealFood.DoesNotExist:
            raise Http404("MealFood not found")

        page = get_dpm_detail_page_data(
            user=request.user,
            dailyplan_id=dailyplan_id,
            dpm_id=dailyplanmeal_id,
            request_get=request.GET,
            viewmode=DAILYPLAN_MEAL_VIEWMODE_DRAFT_DEEP_EDIT,
        )

    content_vm = build_dpm_detail_vm(
        page.detail_content_data,
    )

    ui_vm = build_ui_vm(
        page.viewmode,
        parents=[page.dailyplan],
        instance=page.meal,
    )

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    context = base_vm.as_context()
    context["foods_json"] = page.foods_json
    context["food_picker_json"] = page.food_picker_context_json

    return render(
        request,
        "notas/dailyplan_meals/deep_edit.html",
        context,
    )
#************ AUXILIARES *********************

# ========== ACTIONS ====================

# ADD MEAL IN PICKER DAILYPLAN
@require_POST
@login_required
def dailyplan_add_meal(request, pk=None):
    dailyplan_id = request.POST.get("dailyplan_id") or pk

    dailyplan = get_object_or_404(
        DailyPlan,
        pk=dailyplan_id,
        created_by=request.user,
    )

    meal_id = request.POST.get("meal_id")

    if not meal_id:
        messages.error(request, "Debes seleccionar una meal.")
        return redirect("dailyplan_detail", dailyplan.pk)

    meal_original = get_object_or_404(
        Meal,
        pk=meal_id,
        created_by=request.user,
    )

    hour = request.POST.get("hour") or None
    note = request.POST.get("note")

    add_existing_meal_to_dailyplan(
        dailyplan=dailyplan,
        meal=meal_original,
        user=request.user,
        hour=hour,
        note=note,
    )

    messages.success(request, "Meal added to daily plan")

    return redirect("dailyplan_detail", dailyplan.pk)



@login_required
@require_POST
def dailyplanmeal_remove(request, dailyplan_id, dailyplanmeal_id):
    dpm = get_object_or_404(
        DailyPlanMeal.objects.select_related("dailyplan", "meal"),
        pk=dailyplanmeal_id,
        dailyplan_id=dailyplan_id,
        dailyplan__created_by=request.user,
    )

    return_to = (
        request.POST.get("return_to")
        or request.GET.get("return_to")
    )

    result = remove_dailyplan_meal(
        dailyplan_meal=dpm,
    )

    messages.success(request, "Meal eliminada del daily plan")

    if return_to:
        return redirect(return_to)

    return redirect("dailyplan_detail", result.dailyplan.pk)


@login_required
@require_POST
def dailyplanmeal_update(request, dailyplan_id, dailyplanmeal_id):
    dpm = get_object_or_404(
        DailyPlanMeal.objects.select_related("dailyplan", "meal"),
        pk=dailyplanmeal_id,
        dailyplan_id=dailyplan_id,
        dailyplan__created_by=request.user,
    )

    result = update_dailyplan_meal(
        dailyplan_meal=dpm,
        user=request.user,
        meal_id=request.POST.get("meal_id"),
        hour=request.POST.get("hour"),
        note=request.POST.get("note"),
    )

    messages.success(request, "Meal actualizada.")

    return redirect("dailyplan_detail", result.dailyplan.pk)



@login_required
@require_POST
def dailyplanmeal_save_to_library(request, dailyplan_id, dailyplanmeal_id):
    dpm = get_object_or_404(
        DailyPlanMeal.objects.select_related("dailyplan", "meal"),
        pk=dailyplanmeal_id,
        dailyplan_id=dailyplan_id,
        dailyplan__created_by=request.user,
    )

    saved_meal = save_dailyplan_meal_to_library(
        dailyplan_meal=dpm,
        user=request.user,
    )

    messages.success(request, "Comida guardada en Mi librería.")

    return redirect("meal_detail", pk=saved_meal.pk)


@login_required
@require_POST
def dailyplanmeal_create_meal(request, dailyplan_id, dailyplanmeal_id):
    dpm = get_object_or_404(
        DailyPlanMeal.objects.select_related("dailyplan", "meal"),
        pk=dailyplanmeal_id,
        dailyplan__id=dailyplan_id,
        dailyplan__created_by=request.user,
    )

    result = create_empty_meal_for_dailyplan_meal(
        dailyplan_meal=dpm,
        user=request.user,
        name="New Meal",
    )

    messages.success(request, "Nueva meal creada en este slot")

    return redirect(
        "dailyplan_meal_detail",
        dailyplan_id=result.dailyplan.id,
        pk=result.dailyplan_meal.id,
    )


@login_required
def dailyplanmeal_share(request, dailyplan_id, pk):
    dpm = get_object_or_404(
        DailyPlanMeal.objects.select_related("dailyplan", "meal"),
        pk=pk,
        dailyplan_id=dailyplan_id,
        dailyplan__created_by=request.user,
    )

    form = DailyPlanMealShareForm(request.POST or None, initial={"subject": dpm.meal.name})

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["recipient_email"]
        share_subject = form.cleaned_data.get("subject", dpm.meal.name)
        message = form.cleaned_data.get("message", "")

        result = create_dailyplanmeal_share(
            sender=request.user,
            recipient_email=email,
            dailyplan_meal=dpm,
            subject=share_subject,
            message=message,
        )
        share = result.share

        email_subject, email_message = build_share_invitation_email(
            request=request,
            share=share,
            kind="dpm",
            item_name=dpm.meal.name,
            custom_subject=share_subject,
            custom_message=message,
        )

        email_sent = False
        try:
            email_sent = bool(send_mail(
                subject=email_subject,
                message=email_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            ))
        except Exception:
            email_sent = False

        if share.accepted_by_id:
            messages.success(request, "Compartiste esta comida de plan. Como el correo pertenece a una cuenta existente, ya está disponible en su Inbox.")
        elif email_sent:
            messages.success(request, "Compartiste esta comida de plan. Enviamos el correo de invitación al destinatario.")
        else:
            messages.warning(request, "Se creó la invitación, pero no se pudo enviar el correo. Revisa la configuración de email.")

        return redirect("dailyplan_meal_detail", dailyplan_id=dpm.dailyplan_id, pk=dpm.pk)

    if request.method == "POST":
        messages.error(request, "No se pudo compartir. Revisa el correo ingresado.")

    return render(request, "notas/dailyplan_meals/share.html", {"dpm": dpm, "form": form})


@login_required
def dailyplanmeal_share_accept(request, token):
    share = get_object_or_404(DailyPlanMealShare, token=token)
    accept_dailyplanmeal_share(share=share, user=request.user)
    return redirect("inbox_list")


@login_required
def dailyplanmeal_share_detail(request, share_id):
    share = get_object_or_404(
        DailyPlanMealShare.objects.select_related("sender", "accepted_by", "dailyplan_meal", "dailyplan_meal__dailyplan", "dailyplan_meal__meal"),
        pk=share_id,
        removed=False,
    )

    if share.sender_id != request.user.id and share.accepted_by_id != request.user.id:
        return HttpResponseForbidden()

    dpm = share.dailyplan_meal
    page = get_dpm_detail_page_data(
        user=share.sender,
        dailyplan_id=dpm.dailyplan_id,
        dpm_id=dpm.id,
        viewmode=DAILYPLAN_MEAL_VIEWMODE_DETAIL,
        request_get=request.GET,
    )

    content_vm = build_dpm_detail_vm(page.detail_content_data)
    content_vm.header = build_page_header(actions=[])

    ui_vm = build_ui_vm(
        DAILYPLAN_MEAL_VIEWMODE_DETAIL,
        instance=page.meal,
        back_config={"type": "url", "value": reverse("inbox_list")},
    )
    ui_vm.nav_root = "meal"
    ui_vm.icon = "utensils"
    ui_vm.page_icon = "utensils"

    base_vm = BaseVM(ui=ui_vm, content=content_vm)
    context = base_vm.as_context()
    context["foods_json"] = "[]"
    context["food_picker_json"] = "{}"
    context["can_edit_foods"] = False
    context["selected_food_id"] = None
    context["editing_mealfood_id"] = None

    return render(request, "notas/dailyplan_meals/detail.html", context)
