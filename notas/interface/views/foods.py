from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from email_delivery.services import deliver_share_invitation
from notas.application.queries.food_picker_queries import (
    get_food_picker_item_by_id,
    list_food_picker_items,
)
from notas.application.services.access.capabilities import get_capabilities
from notas.application.services.commands.food_commands import (
    bulk_create_foods,
    create_food,
    delete_food,
    update_food,
)
from notas.application.services.commands.share_commands import (
    accept_food_share,
    create_food_share,
)
from notas.application.services.notifications.share_emails import build_share_invitation_email
from notas.domain.models import Food, FoodShare
from notas.interface.forms.forms import FoodEditForm, FoodShareForm
from notas.interface.routing.food import food_url
from notas.presentation.composition.viewmodel.food.detail_food_builder import build_food_detail_vm
from notas.presentation.composition.viewmodel.food.edit_food_builder import build_edit_food_vm
from notas.presentation.composition.viewmodel.food.list_foods_builder import build_food_list_vm
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import (
    FOOD_VIEWMODE_CREATE,
    FOOD_VIEWMODE_IMPORT,
    FOOD_VIEWMODE_PERSONAL_DETAIL,
    FOOD_VIEWMODE_PERSONAL_EDIT,
    FOOD_VIEWMODE_PERSONAL_LIST,
    PROGRAM_VIEWMODE_PERSONAL_DETAIL,
)
from notas.presentation.navigation.program_context import (
    compact_program_breadcrumbs,
    dailyplan_context_url,
    day_plan_parent,
    dpm_context_url,
    dpm_parent,
    get_context_dailyplan_meal,
    get_context_meal_food,
    get_program_day_for_user,
    program_parent,
    week_parent,
)
from notas.presentation.pages.food_pages import get_food_list_page_data
from notas.presentation.viewmodels.base_vm import BaseVM


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


def _safe_requested_return_to(request):
    return_to = request.POST.get("return_to") or request.GET.get("return_to") or ""
    if return_to and url_has_allowed_host_and_scheme(
        url=return_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return return_to
    return ""


def _with_query_parameter(url, key, value):
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query[key] = str(value)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


@login_required
@require_POST
def food_list_reorder(request):
    ordered_ids = request.POST.getlist("order[]")

    if not ordered_ids:
        return HttpResponseBadRequest("No order received.")

    foods = {
        food.id: food
        for food in Food.objects.filter(
            created_by=request.user,
            is_active=True,
            id__in=ordered_ids,
        )
    }

    for index, raw_id in enumerate(ordered_ids):
        try:
            food_id = int(raw_id)
        except (TypeError, ValueError):
            continue

        food = foods.get(food_id)
        if not food:
            continue

        if food.list_order != index:
            food.list_order = index
            food.save(update_fields=["list_order"])

    return HttpResponse(status=204)


@login_required
@require_POST
def food_list_bulk_delete(request):
    selected_ids = request.POST.getlist("selected_ids[]")

    if not selected_ids:
        messages.info(request, "No seleccionaste alimentos para eliminar.")
        return redirect(_safe_return_to(request, "food_list", mode="delete"))

    foods = Food.objects.filter(
        created_by=request.user,
        is_active=True,
        id__in=selected_ids,
    )

    deleted_count = 0

    for food in foods:
        delete_food(food=food)
        deleted_count += 1

    if deleted_count:
        messages.success(request, f"{deleted_count} alimento(s) eliminados.")
    else:
        messages.info(request, "No se eliminaron alimentos.")

    return redirect(_safe_return_to(request, "food_list", mode="delete"))


@login_required
@require_POST
def food_delete(request, pk):
    food = get_object_or_404(
        Food,
        pk=pk,
        created_by=request.user,
        is_active=True,
    )

    delete_food(food=food)
    messages.success(request, "Alimento eliminado.")

    return redirect(_safe_return_to(request, "food_list", mode="delete"))

#************ RENDER COMPLEJOS *********************
@login_required
def food_list(request):
    page = get_food_list_page_data(
        user=request.user,
        request_get=request.GET,
    )

    ui_vm = build_ui_vm(page.viewmode)

    content_vm = build_food_list_vm(
        page.foods,
        request.user,
        page.viewmode,
        page_actions=page.page_actions,
        list_mode=page.list_mode,
    )

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/foods/list.html",
        base_vm.as_context(),
    )


def food_detail(request, pk):

    food = get_object_or_404(Food, pk=pk)

    viewmode = FOOD_VIEWMODE_PERSONAL_DETAIL


    content_vm = build_food_detail_vm(
        food,
        request.user,
        viewmode,
    )

    program_day = get_program_day_for_user(
        request.user,
        request.GET.get("program_day"),
    )
    dpm = get_context_dailyplan_meal(program_day, request.GET.get("dpm"))
    mealfood = get_context_meal_food(dpm, request.GET.get("mealfood"))

    if mealfood and mealfood.food_id == food.id:
        ui_vm = build_ui_vm(
            PROGRAM_VIEWMODE_PERSONAL_DETAIL,
            parents=[
                program_parent(program_day),
                week_parent(program_day),
                day_plan_parent(
                    program_day,
                    url=dailyplan_context_url(program_day),
                ),
                dpm_parent(
                    program_day,
                    dpm,
                    url=dpm_context_url(program_day, dpm),
                ),
            ],
            instance=food,
            back_config={
                "type": "url",
                "value": dpm_context_url(program_day, dpm),
            },
        )
        compact_program_breadcrumbs(ui_vm)
    else:
        ui_vm = build_ui_vm(viewmode, instance=food)

    base_vm = BaseVM(
        ui=ui_vm,
        content=content_vm,
    )

    return render(
        request,
        "notas/foods/detail.html",
        base_vm.as_context(),
    )


@login_required
def food_edit(request, pk):

    food = get_object_or_404(
        Food,
        pk=pk,
        created_by=request.user,
    )

    if request.method == "POST":
        form = FoodEditForm(request.POST, instance=food)

        if form.is_valid():
            result = update_food(
                food=food,
                name=form.cleaned_data["name"],
                protein=form.cleaned_data["protein"],
                carbs=form.cleaned_data["carbs"],
                fat=form.cleaned_data["fat"],
            )

            return redirect("food_detail", pk=result.food.pk)

    else:
        form = FoodEditForm(instance=food)

    ui_vm = build_ui_vm(FOOD_VIEWMODE_PERSONAL_DETAIL, instance=food)

    content_vm = build_edit_food_vm(food=food)

    base_vm = BaseVM(ui=ui_vm, content=content_vm)

    return render(
        request,
        "notas/foods/edit.html",
        {
            **base_vm.as_context(),
            "form": form,
        }
    )   


#************ RENDER BÁSICOS *********************
# ---------- CREATE - *FALTA_RENAME - CONFIGURE ----------

@login_required
def food_create(request):

    viewmode = FOOD_VIEWMODE_CREATE
    
    ui_vm = build_ui_vm(viewmode)

    base_vm = BaseVM(
        ui=ui_vm,
    )
    return_to = _safe_requested_return_to(request)

    if request.method == "POST":
        form = FoodEditForm(request.POST)

        if form.is_valid():
            result = create_food(
                user=request.user,
                name=form.cleaned_data["name"],
                protein=form.cleaned_data["protein"],
                carbs=form.cleaned_data["carbs"],
                fat=form.cleaned_data["fat"],
            )

            if return_to:
                return redirect(
                    _with_query_parameter(
                        return_to,
                        "select_food",
                        result.food.pk,
                    )
                )

            return redirect("food_list")
    else:
        form = FoodEditForm()

    return render(
        request,
        "notas/foods/create.html",
        {
            **base_vm.as_context(),
            "form": form,
            "return_to": return_to,
        },
    )


@login_required
def import_foods(request):

    viewmode = FOOD_VIEWMODE_IMPORT

    ui_vm = build_ui_vm(viewmode)

    base_vm = BaseVM(
        ui=ui_vm,
    )

    if request.method == "POST":
        import pandas as pd

        file = request.FILES.get("file")

        if not file:
            messages.error(request, "Please upload a file.")
            return redirect("import_foods")

        try:
            df = pd.read_excel(file)

            required_columns = {"name", "protein", "carbs", "fat"}

            if not required_columns.issubset(df.columns):
                messages.error(
                    request,
                    f"Missing columns. Required: {', '.join(required_columns)}"
                )
                return redirect("import_foods")

            rows_to_create = []

            for _, row in df.iterrows():
                rows_to_create.append(
                    {
                        "name": row["name"],
                        "protein": row["protein"],
                        "carbs": row["carbs"],
                        "fat": row["fat"],
                    }
                )

            result = bulk_create_foods(
                user=request.user,
                rows=rows_to_create,
            )

            messages.success(
                request,
                f"{result.created_count} foods imported successfully."
            )

        except Exception as e:
            messages.error(request, f"Import failed: {e}")

        return redirect("food_list")

    return render(
        request,
        "notas/foods/import.html",
        base_vm.as_context(),
    )



@login_required
def download_food_template(request):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Foods"

    # Headers
    ws.append([
        "name",
        "protein",
        "carbs",
        "fat",
    ])

    # Optional example row (muy útil)
    ws.append([
        "Chicken breast",
        31,
        0,
        3.6,
    ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="food_import_template.xlsx"'

    wb.save(response)
    return response



@login_required
def foods_json(request):
    search = request.GET.get("search")
    raw_limit = request.GET.get("limit")
    raw_food_id = request.GET.get("food_id")

    try:
        limit = int(raw_limit) if raw_limit else 80
    except (TypeError, ValueError):
        limit = 80

    if raw_food_id:
        try:
            food_id = int(raw_food_id)
        except (TypeError, ValueError):
            return JsonResponse([], safe=False)

        item = get_food_picker_item_by_id(
            user=request.user,
            food_id=food_id,
        )

        if item is None:
            return JsonResponse([], safe=False)

        picker_foods = [item]
    else:
        picker_items = list_food_picker_items(
            user=request.user,
            search=search,
            limit=limit,
        )
        picker_foods = picker_items.foods

    foods = []

    for item in picker_foods:
        foods.append({
            "id": item.id,
            "name": item.name,
            "display_name": item.display_name,
            "protein": item.protein,
            "carbs": item.carbs,
            "fat": item.fat,
            "total_kcal": item.total_kcal,
            "alloc": item.alloc,
            "picker_source": item.picker_source,
            "picker_label": item.picker_label,
            "is_user_food": item.is_user_food,
            "is_global_food": item.is_global_food,
            "is_verified": item.is_verified,
            "visibility": item.visibility,
            "data_quality_score": item.data_quality_score,
            "source": item.source,
            "search_text": item.search_text,
        })

    return JsonResponse(foods, safe=False)






@login_required
def food_share(request, pk):
    food = get_object_or_404(Food, pk=pk, created_by=request.user, is_active=True)

    if food.created_by != request.user:
        return HttpResponseForbidden()

    form = FoodShareForm(request.POST or None, initial={"subject": food.name})

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["recipient_email"]
        share_subject = form.cleaned_data.get("subject", food.name)
        message = form.cleaned_data.get("message", "")

        result = create_food_share(
            sender=request.user,
            recipient_email=email,
            food=food,
            subject=share_subject,
            message=message,
        )
        share = result.share

        email_subject, email_message = build_share_invitation_email(
            request=request,
            share=share,
            kind="food",
            item_name=food.name,
            custom_subject=share_subject,
            custom_message=message,
        )

        delivery = deliver_share_invitation(
            share=share,
            subject=email_subject,
            message=email_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
        )

        if share.accepted_by_id:
            messages.success(request, "Compartiste este alimento. Como el correo pertenece a una cuenta existente, ya está disponible en su Inbox.")
        elif delivery.sent:
            messages.success(request, "Compartiste este alimento. Enviamos el correo de invitación al destinatario.")
        elif delivery.reason == "duplicate_share":
            messages.success(request, "Este alimento ya estaba compartido. No reenviamos el correo para evitar duplicados.")
        else:
            messages.warning(request, "Se creó la invitación, pero la política de correo no permitió enviarla.")

        return redirect("food_detail", pk=food.pk)

    if request.method == "POST":
        messages.error(request, "No se pudo compartir. Revisa el correo ingresado.")

    return render(request, "notas/foods/share.html", {"food": food, "form": form})


@login_required
def food_share_accept(request, token):
    share = get_object_or_404(FoodShare, token=token)
    accept_food_share(share=share, user=request.user)
    return redirect("inbox_list")
