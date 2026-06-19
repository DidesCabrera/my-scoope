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