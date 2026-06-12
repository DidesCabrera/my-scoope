from django import forms

class DailyPlanShareForm(forms.Form):
    recipient_email = forms.EmailField(label="Email del destinatario")

class MealShareForm(forms.Form):
    recipient_email = forms.EmailField(label="Email del destinatario")


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