from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User

from notas.domain.models import Meal, DailyPlan, Program


def author_profile(request, username):
    user = get_object_or_404(User, username=username)
    profile = user.profile

    meals = (
        Meal.objects
        .filter(created_by=user, is_public=True, is_draft=False)
        .order_by("-created_at")
    )

    dailyplans = (
        DailyPlan.objects
        .filter(created_by=user, is_public=True, is_draft=False)
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .order_by("-created_at")
    )

    programs = (
        Program.objects
        .filter(created_by=user, is_public=True, is_draft=False)
        .order_by("-created_at")
    )


    return render(
        request,
        "notas/profile/author_detail.html",
        {
            "profile": profile,
            "meals": meals,
            "dailyplans": dailyplans,
            "programs": programs
        },
    )


def author_programs(request, username):
    user = get_object_or_404(User, username=username)

    programs = (
        Program.objects
        .filter(created_by=user, is_public=True, is_draft=False)
        .order_by("-created_at")
    )

    return render(
        request,
        "notas/profile/author_programs.html",
        {
            "author": user,
            "programs": programs,
        },
    )


def author_dailyplans(request, username):
    user = get_object_or_404(User, username=username)

    dailyplans = (
        DailyPlan.objects
        .filter(created_by=user, is_public=True, is_draft=False)
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .order_by("-created_at")
    )

    return render(
        request,
        "notas/profile/author_dailyplans.html",
        {
            "author": user,
            "dailyplans": dailyplans,
        },
    )


def author_meals(request, username):
    user = get_object_or_404(User, username=username)

    meals = (
        Meal.objects
        .filter(created_by=user, is_public=True, is_draft=False)
        .order_by("-created_at")
    )

    return render(
        request,
        "notas/profile/author_meals.html",
        {
            "author": user,
            "meals": meals,
        },
    )


