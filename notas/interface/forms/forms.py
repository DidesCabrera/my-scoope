from django import forms


class DailyPlanShareForm(forms.Form):
    recipient_email = forms.EmailField(
        label="Email del destinatario",
        widget=forms.EmailInput(attrs={
            "class": "input-create entity-form__input",
            "placeholder": "correo@ejemplo.com",
            "autocomplete": "email",
        }),
    )
    subject = forms.CharField(
        label="Asunto",
        max_length=160,
        widget=forms.TextInput(attrs={
            "class": "input-create entity-form__input",
            "placeholder": "Asunto del mensaje",
            "autocomplete": "off",
        }),
    )
    message = forms.CharField(
        label="Mensaje",
        required=False,
        widget=forms.Textarea(attrs={
            "class": "input-create entity-form__input entity-form__textarea",
            "placeholder": "Escribe un mensaje breve para acompañar el elemento compartido...",
            "rows": 4,
        }),
    )


class ProgramShareForm(forms.Form):
    recipient_email = forms.EmailField(
        label="Email del destinatario",
        widget=forms.EmailInput(attrs={
            "class": "input-create entity-form__input",
            "placeholder": "correo@ejemplo.com",
            "autocomplete": "email",
        }),
    )
    subject = forms.CharField(
        label="Asunto",
        max_length=160,
        widget=forms.TextInput(attrs={
            "class": "input-create entity-form__input",
            "placeholder": "Asunto del mensaje",
            "autocomplete": "off",
        }),
    )
    message = forms.CharField(
        label="Mensaje",
        required=False,
        widget=forms.Textarea(attrs={
            "class": "input-create entity-form__input entity-form__textarea",
            "placeholder": "Escribe un mensaje breve para acompañar el programa compartido...",
            "rows": 4,
        }),
    )


class MealShareForm(forms.Form):
    recipient_email = forms.EmailField(
        label="Email del destinatario",
        widget=forms.EmailInput(attrs={
            "class": "input-create entity-form__input",
            "placeholder": "correo@ejemplo.com",
            "autocomplete": "email",
        }),
    )
    subject = forms.CharField(
        label="Asunto",
        max_length=160,
        widget=forms.TextInput(attrs={
            "class": "input-create entity-form__input",
            "placeholder": "Asunto del mensaje",
            "autocomplete": "off",
        }),
    )
    message = forms.CharField(
        label="Mensaje",
        required=False,
        widget=forms.Textarea(attrs={
            "class": "input-create entity-form__input entity-form__textarea",
            "placeholder": "Escribe un mensaje breve para acompañar el elemento compartido...",
            "rows": 4,
        }),
    )


class FoodShareForm(forms.Form):
    recipient_email = forms.EmailField(
        label="Email del destinatario",
        widget=forms.EmailInput(attrs={
            "class": "input-create entity-form__input",
            "placeholder": "correo@ejemplo.com",
            "autocomplete": "email",
        }),
    )
    subject = forms.CharField(
        label="Asunto",
        max_length=160,
        widget=forms.TextInput(attrs={
            "class": "input-create entity-form__input",
            "placeholder": "Asunto del mensaje",
            "autocomplete": "off",
        }),
    )
    message = forms.CharField(
        label="Mensaje",
        required=False,
        widget=forms.Textarea(attrs={
            "class": "input-create entity-form__input entity-form__textarea",
            "placeholder": "Escribe un mensaje breve para acompañar el elemento compartido...",
            "rows": 4,
        }),
    )


class DailyPlanMealShareForm(forms.Form):
    recipient_email = forms.EmailField(
        label="Email del destinatario",
        widget=forms.EmailInput(attrs={
            "class": "input-create entity-form__input",
            "placeholder": "correo@ejemplo.com",
            "autocomplete": "email",
        }),
    )
    subject = forms.CharField(
        label="Asunto",
        max_length=160,
        widget=forms.TextInput(attrs={
            "class": "input-create entity-form__input",
            "placeholder": "Asunto del mensaje",
            "autocomplete": "off",
        }),
    )
    message = forms.CharField(
        label="Mensaje",
        required=False,
        widget=forms.Textarea(attrs={
            "class": "input-create entity-form__input entity-form__textarea",
            "placeholder": "Escribe un mensaje breve para acompañar el elemento compartido...",
            "rows": 4,
        }),
    )


class ProfileNutritionForm(forms.Form):
    birth_date = forms.DateField(
        label="Fecha de nacimiento",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "profile-form-input",
                "autocomplete": "bday",
            }
        ),
    )
    sex = forms.ChoiceField(
        label="Sexo para cálculo nutricional",
        choices=(("", "Selecciona una opción"),),
        widget=forms.Select(attrs={"class": "profile-form-input"}),
    )
    height_cm = forms.IntegerField(
        label="Altura",
        min_value=80,
        max_value=250,
        widget=forms.NumberInput(
            attrs={
                "class": "profile-form-input",
                "inputmode": "numeric",
                "placeholder": "Ej: 188",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from notas.domain.models import Profile

        self.fields["sex"].choices = (("", "Selecciona una opción"),) + Profile.SEX_CHOICES

    def clean_birth_date(self):
        from django.utils import timezone

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


from notas.domain.models import Food


class FoodEditForm(forms.ModelForm):

    class Meta:
        model = Food
        fields = [
            "name",
            "protein",
            "carbs",
            "fat"
        ]
        labels = {
            "name": "Nombre",
            "protein": "Protein",
            "carbs": "Carbs",
            "fat": "Fat",
        }
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "food-edit-form__input food-edit-form__input--name",
                "placeholder": "Nombre del alimento",
                "autocomplete": "off",
            }),
            "protein": forms.NumberInput(attrs={
                "class": "food-edit-form__macro-input",
                "step": "0.01",
                "min": "0",
                "inputmode": "decimal",
            }),
            "carbs": forms.NumberInput(attrs={
                "class": "food-edit-form__macro-input",
                "step": "0.01",
                "min": "0",
                "inputmode": "decimal",
            }),
            "fat": forms.NumberInput(attrs={
                "class": "food-edit-form__macro-input",
                "step": "0.01",
                "min": "0",
                "inputmode": "decimal",
            }),
        }