from django.urls import reverse


def meal_url(meal):
    return reverse("meal_detail", args=[meal.id])


def meal_configure_url(meal):
    return reverse("meal_configure", args=[meal.id])


def meal_list_url():
    return reverse("meal_list")
