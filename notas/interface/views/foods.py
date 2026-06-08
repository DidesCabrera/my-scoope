import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from openpyxl import Workbook
from django.contrib import messages
from notas.application.services.access.capabilities import get_capabilities
from notas.domain.models import Food
from notas.application.queries.food_picker_queries import (
    get_food_picker_item_by_id,
    list_food_picker_items,
)
from notas.presentation.config.viewmodel_config import (
    FOOD_VIEWMODE_PERSONAL_LIST, 
    FOOD_VIEWMODE_PERSONAL_DETAIL,
    FOOD_VIEWMODE_PERSONAL_EDIT,
    FOOD_VIEWMODE_CREATE,
    FOOD_VIEWMODE_IMPORT
)
from notas.interface.routing.food import food_url
from notas.presentation.composition.viewmodel.food.list_foods_builder import build_food_list_vm
from notas.presentation.composition.viewmodel.food.detail_food_builder import build_food_detail_vm
from notas.presentation.composition.viewmodel.food.edit_food_builder import build_edit_food_vm
from notas.interface.forms.forms import FoodEditForm

from notas.application.services.commands.food_commands import (
    bulk_create_foods,
    create_food,
    update_food,
)


from notas.presentation.viewmodels.base_vm import BaseVM
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm

from notas.application.use_cases.food_pages import get_food_list_page_data


#************ RENDER COMPLEJOS *********************
@login_required
def food_list(request):
    page = get_food_list_page_data(
        user=request.user,
    )

    ui_vm = build_ui_vm(page.viewmode)

    content_vm = build_food_list_vm(
        page.foods,
        request.user,
        page.viewmode,
        page_actions=page.page_actions,
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

def food_create(request):

    viewmode = FOOD_VIEWMODE_CREATE
    
    ui_vm = build_ui_vm(viewmode)

    base_vm = BaseVM(
        ui=ui_vm,
    )

    if request.method == "POST":

        name = request.POST.get("name")
        protein = float(request.POST.get("protein"))
        carbs = float(request.POST.get("carbs"))
        fat = float(request.POST.get("fat"))

        create_food(
            user=request.user,
            name=name,
            protein=protein,
            carbs=carbs,
            fat=fat,
        )

        return redirect("food_list")

    return render(
        request,
        "notas/foods/create.html",
        base_vm.as_context(),
    )


@login_required
def import_foods(request):

    viewmode = FOOD_VIEWMODE_IMPORT

    ui_vm = build_ui_vm(viewmode)

    base_vm = BaseVM(
        ui=ui_vm,
    )

    if request.method == "POST":
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




