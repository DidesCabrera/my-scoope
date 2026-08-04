from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from notas.application.services.commands.meal_commands import (
    create_meal_food,
    delete_meal_food,
    reorder_meal_foods,
    update_meal_food,
)
from notas.domain.models import Food, Meal, MealFood

#************ RENDER COMPLEJOS *********************
# ---------- DETAIL (NO HAY LIST)  ----------

@login_required
@require_POST
def mealfood_update(request, meal_id, mealfood_id):

    meal = get_object_or_404(
        Meal,
        id=meal_id,
        created_by=request.user,
    )

    mealfood = get_object_or_404(
        MealFood.objects.select_related("meal"),
        id=mealfood_id,
        meal=meal,
    )

    return_to = (
        request.POST.get("return_to")
        or request.GET.get("return_to")
    )

    try:
        quantity = float(request.POST.get("quantity", 0))
    except ValueError:
        quantity = 0

    if quantity <= 0:
        messages.error(request, "La cantidad debe ser mayor a 0.")
        if return_to:
            return redirect(return_to)
        return redirect("meal_detail", meal.id)

    update_meal_food(
        meal_food=mealfood,
        quantity=quantity,
        food_id=request.POST.get("food_id"),
    )

    messages.success(request, "Alimento actualizado correctamente.")

    if return_to:
        return redirect(return_to)

    return redirect("meal_detail", pk=meal.pk)


@login_required
@require_POST
def mealfood_remove(request, pk):

    mf = get_object_or_404(
        MealFood.objects.select_related("meal", "meal__created_by"),
        pk=pk,
        meal__created_by=request.user,
    )

    meal = mf.meal

    # 🔑 NUEVO: destino explícito
    return_to = (
        request.POST.get("return_to")
        or request.GET.get("return_to")
    )

    delete_meal_food(
        meal_food=mf,
    )

    # 👉 prioridad absoluta: return_to
    if return_to:
        return redirect(return_to)

    return redirect("meal_detail", pk=meal.pk)


@require_POST
def add_food_to_meal(request, pk):
    meal = get_object_or_404(Meal, pk=pk)

    food_id = request.POST.get("food_id")
    quantity = request.POST.get("quantity")

    # 🔑 NUEVO: destino explícito (POST o GET)
    return_to = (
        request.POST.get("return_to")
        or request.GET.get("return_to")
    )

    if not food_id or not quantity:
        messages.error(request, "Food y cantidad son obligatorios")

        # 👉 prioridad absoluta: return_to
        if return_to:
            return redirect(return_to)

        return redirect("meal_detail", pk=meal.pk)

    food = get_object_or_404(Food, pk=food_id)

    create_meal_food(
        meal=meal,
        food=food,
        quantity=quantity,
    )

    messages.success(request, "Food agregado a la meal")

    # 👉 prioridad absoluta: return_to
    if return_to:
        return redirect(return_to)

    return redirect("meal_detail", pk=meal.pk)

@login_required
@require_POST
def mealfood_reorder(request, meal_id):
    meal = get_object_or_404(
        Meal,
        id=meal_id,
        created_by=request.user,
    )

    ordered_ids = request.POST.getlist("mealfood_order[]")

    if not ordered_ids:
        return JsonResponse(
            {"ok": False, "error": "Missing order payload"},
            status=400,
        )

    try:
        result = reorder_meal_foods(
            meal=meal,
            ordered_ids=ordered_ids,
        )
    except ValueError:
        return JsonResponse(
            {"ok": False, "error": "Invalid MealFood ids"},
            status=400,
        )

    return JsonResponse(
        {
            "ok": True,
            "updated_count": result.updated_count,
        }
    )