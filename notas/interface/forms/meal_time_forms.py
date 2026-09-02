from django import forms


class MealTimeChangeForm(forms.Form):
    hour = forms.TimeField(
        input_formats=["%H:%M"],
        widget=forms.TimeInput(
            format="%H:%M",
            attrs={
                "type": "time",
                "class": "input-create entity-form__input",
                "id": "meal-time",
                "step": "300",
            },
        ),
        error_messages={
            "required": "Selecciona una hora.",
            "invalid": "Selecciona una hora válida.",
        },
    )
