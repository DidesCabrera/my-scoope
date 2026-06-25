from django.urls import reverse


def dailyplan_url(dailyplan):
    return reverse("dailyplan_detail", args=[dailyplan.id])


def dailyplan_configure_url(dailyplan):
    return reverse("dailyplan_configure", args=[dailyplan.id])
