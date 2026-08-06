from __future__ import annotations

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from notas.domain.models import Profile

from .forms import AccountDeletionForm, NutritionOnboardingForm
from .services.deletion import delete_user_account
from .services.onboarding import complete_nutrition_onboarding


@login_required
def nutrition_onboarding(request):
    profile = request.user.profile

    if request.method == "POST":
        form = NutritionOnboardingForm(request.POST)
        if form.is_valid():
            complete_nutrition_onboarding(
                user=request.user,
                birth_date=form.cleaned_data["birth_date"],
                sex=form.cleaned_data["sex"],
                height_cm=form.cleaned_data["height_cm"],
                weight_kg=form.cleaned_data["weight_kg"],
            )
            return redirect("home_view")
    else:
        initial = {
            "birth_date": profile.birth_date,
            "sex": profile.sex,
            "height_cm": profile.height_cm,
        }
        form = NutritionOnboardingForm(initial=initial)

    return render(
        request,
        "accounts/onboarding.html",
        {
            "form": form,
            "onboarding_version": Profile.ONBOARDING_VERSION_NUTRITION_V1,
            "has_form_errors": bool(form.errors),
        },
    )


@login_required
def delete_account(request):
    if request.method == "POST":
        form = AccountDeletionForm(request.POST, user=request.user)
        if form.is_valid():
            result = delete_user_account(user=request.user, source="self_service_web")
            logout(request)
            return render(
                request,
                "accounts/account_deleted.html",
                {"receipt_id": result.receipt_id},
            )
    else:
        form = AccountDeletionForm(user=request.user)

    return render(request, "accounts/delete_account.html", {"form": form})
