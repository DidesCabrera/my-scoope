from __future__ import annotations

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from notas.application.services.nutrition.body_metrics import record_weight
from notas.domain.models import Profile, WeightLog

from .forms import AccountDeletionForm, NutritionOnboardingForm
from .services.deletion import delete_user_account


@login_required
def nutrition_onboarding(request):
    profile = request.user.profile

    if request.method == "POST":
        form = NutritionOnboardingForm(request.POST)
        if form.is_valid():
            profile.birth_date = form.cleaned_data["birth_date"]
            profile.sex = form.cleaned_data["sex"]
            profile.height_cm = form.cleaned_data["height_cm"]
            profile.onboarding_completed_at = timezone.now()
            profile.onboarding_version = Profile.ONBOARDING_VERSION_NUTRITION_V1
            profile.save(
                update_fields=[
                    "birth_date",
                    "sex",
                    "height_cm",
                    "onboarding_completed_at",
                    "onboarding_version",
                ]
            )
            record_weight(
                request.user,
                form.cleaned_data["weight_kg"],
                source=WeightLog.SOURCE_ONBOARDING,
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
