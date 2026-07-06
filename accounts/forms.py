from __future__ import annotations

from django import forms
from django.utils import timezone

from notas.domain.models import Profile


class NutritionOnboardingForm(forms.Form):
    birth_date = forms.DateField(
        label="Fecha de nacimiento",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "autocomplete": "bday",
            }
        ),
    )
    sex = forms.ChoiceField(
        label="Sexo para cálculo nutricional",
        choices=(('', 'Selecciona una opción'),) + Profile.SEX_CHOICES,
    )
    height_cm = forms.IntegerField(
        label="Altura",
        min_value=80,
        max_value=250,
        widget=forms.NumberInput(
            attrs={
                "inputmode": "numeric",
                "placeholder": "Ej: 188",
            }
        ),
    )
    weight_kg = forms.FloatField(
        label="Peso actual",
        min_value=25,
        max_value=350,
        widget=forms.NumberInput(
            attrs={
                "inputmode": "decimal",
                "step": "0.1",
                "placeholder": "Ej: 88.5",
            }
        ),
    )

    def clean_birth_date(self):
        birth_date = self.cleaned_data["birth_date"]
        today = timezone.localdate()

        if birth_date >= today:
            raise forms.ValidationError("Ingresa una fecha de nacimiento anterior a hoy.")

        age = today.year - birth_date.year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1

        if age < 13:
            raise forms.ValidationError("Debes tener al menos 13 años para completar este flujo.")
        if age > 100:
            raise forms.ValidationError("Revisa la fecha de nacimiento ingresada.")

        return birth_date
