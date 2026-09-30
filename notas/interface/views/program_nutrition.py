"""Manual planning assumptions. Saving targets never mutates measured weight or meals."""

from django import forms
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import formset_factory
from django.shortcuts import get_object_or_404, redirect, render

from notas.domain.models import Program
from nutrition_solver.application.program_specification import parse_program_specification


class NutritionPolicyForm(forms.Form):
    weight_basis = forms.ChoiceField(label="Peso utilizado para calcular proteína", choices=[
        ("measured", "Peso actual medido (constante hasta nueva revisión)"),
        ("projected", "Peso proyectado de cada semana (supuesto, no medición)")])
    measured_weight_kg = forms.FloatField(label="Peso actual medido (kg)", min_value=20, max_value=400)
    meals_per_day = forms.IntegerField(label="Comidas diarias", min_value=1, max_value=6, initial=4)
    protein_min_ppk = forms.FloatField(label="Proteína mínima (g/kg)", min_value=.1, max_value=3.5)
    protein_max_ppk = forms.FloatField(label="Proteína máxima (g/kg)", min_value=.1, max_value=3.5)
    fat_max_percent = forms.FloatField(label="Máximo de energía procedente de grasa (%)", min_value=1, max_value=100)
    calorie_tolerance_percent = forms.FloatField(label="Tolerancia de calorías (%)", min_value=0, max_value=10, initial=3)
    fruit_min_g = forms.FloatField(label="Fruta mínima diaria (g)", min_value=0, max_value=2000)
    vegetable_min_g = forms.FloatField(label="Verduras mínimas diarias (g)", min_value=0, max_value=3000)
    weekly_fruit_species = forms.IntegerField(label="Frutas distintas por semana", min_value=0, max_value=7)
    weekly_vegetable_species = forms.IntegerField(label="Verduras distintas por semana", min_value=0, max_value=14)
    max_family_per_week_per_slot = forms.IntegerField(label="Máximo de repeticiones de una familia por horario y semana", min_value=1, max_value=7)


class WeekTargetForm(forms.Form):
    kcal = forms.FloatField(label="Calorías diarias objetivo", min_value=800, max_value=8000)
    projected_weight_kg = forms.FloatField(label="Peso proyectado (kg; opcional si se usa el medido)", required=False, min_value=20, max_value=400)


@login_required
def program_nutrition_settings(request, pk):
    program = get_object_or_404(Program, pk=pk, created_by=request.user)
    duration = program.normalized_duration_weeks
    if duration > 8:
        return render(request, "notas/programs/nutrition_settings.html", {"program": program,
                      "error": "La configuración nutricional admite programas de una a ocho semanas."}, status=400)
    current = program.nutrition_specification or {}
    WeekForms = formset_factory(WeekTargetForm, extra=0, min_num=duration, max_num=duration,
                               validate_min=True, validate_max=True, absolute_max=8)
    data = request.POST if request.method == "POST" else None
    policy = NutritionPolicyForm(data, initial=current)
    rows = WeekForms(data, prefix="weeks", initial=current.get("weeks") or [{} for _ in range(duration)])
    preview, error = None, None
    if request.method == "POST" and policy.is_valid() and rows.is_valid():
        try:
            spec = parse_program_specification({"version": 1, "duration_weeks": duration, "energy_source": "manual",
                **policy.cleaned_data, "weeks": [{"week": index + 1, **row.cleaned_data} for index, row in enumerate(rows)]})
            preview = spec.as_dict()
            if request.POST.get("action") == "save":
                with transaction.atomic():
                    stored = Program.objects.select_for_update().get(pk=program.pk, created_by=request.user)
                    if stored.duration_weeks != duration:
                        raise ValueError("La duración cambió. Recarga la configuración.")
                    stored.nutrition_specification = preview
                    stored.culinary_provenance = {**stored.culinary_provenance, "needs_revalidation": True}
                    stored.save(update_fields=["nutrition_specification", "culinary_provenance"])
                return redirect("program_nutrition_settings", pk=program.pk)
        except ValueError as exc:
            error = str(exc)
    return render(request, "notas/programs/nutrition_settings.html", {"program": program, "policy": policy,
        "week_forms": rows, "preview": preview or current, "error": error})
