from __future__ import annotations

from allauth.account.forms import SignupForm
from django import forms
from django.utils import timezone

from accounts.turnstile import validate_signup_token
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


class ProtectedSignupForm(SignupForm):
    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        validation = validate_signup_token(
            self.data.get("cf-turnstile-response", "")
        )
        if not validation.success:
            raise forms.ValidationError(
                "No pudimos validar que el registro sea legítimo. "
                "Inténtalo nuevamente."
            )
        return cleaned_data


class AccountDeletionForm(forms.Form):
    confirmation = forms.CharField(
        label="Confirmación",
        help_text='Escribe "ELIMINAR" para confirmar.',
        widget=forms.TextInput(attrs={"autocomplete": "off", "placeholder": "ELIMINAR"}),
    )
    password = forms.CharField(
        label="Contraseña actual",
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if not user.has_usable_password():
            self.fields.pop("password")

    def clean_confirmation(self):
        confirmation = self.cleaned_data["confirmation"].strip()
        if confirmation != "ELIMINAR":
            raise forms.ValidationError('Escribe exactamente "ELIMINAR".')
        return confirmation

    def clean(self):
        cleaned_data = super().clean()
        if self.user.has_usable_password():
            password = cleaned_data.get("password", "")
            if not password:
                self.add_error("password", "Ingresa tu contraseña actual.")
            elif not self.user.check_password(password):
                self.add_error("password", "La contraseña no es correcta.")
        return cleaned_data
