from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django import forms


class CalendarizationActivationForm(forms.Form):
    program_id = forms.IntegerField(min_value=1)
    start_date = forms.DateField()
    notification_time = forms.TimeField()
    timezone_name = forms.CharField(max_length=64)
    daily_notifications_enabled = forms.BooleanField(required=False)
    meal_notifications_enabled = forms.BooleanField(required=False)
    confirm_incomplete = forms.BooleanField(required=False)
    replace_current = forms.BooleanField(required=False)

    def clean_timezone_name(self):
        name = self.cleaned_data["timezone_name"].strip()
        try:
            ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise forms.ValidationError("Selecciona una zona horaria válida.") from exc
        return name


class CalendarizationPreferencesForm(forms.Form):
    notification_time = forms.TimeField()
    timezone_name = forms.CharField(max_length=64)
    daily_notifications_enabled = forms.BooleanField(required=False)
    meal_notifications_enabled = forms.BooleanField(required=False)

    def clean_timezone_name(self):
        name = self.cleaned_data["timezone_name"].strip()
        try:
            ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise forms.ValidationError("Selecciona una zona horaria válida.") from exc
        return name
