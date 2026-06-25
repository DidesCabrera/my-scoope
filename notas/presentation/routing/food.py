from django.urls import reverse


def food_url(food):
    return reverse("food_detail", args=[food.id])


def food_list_url():
    return reverse("food_list")
