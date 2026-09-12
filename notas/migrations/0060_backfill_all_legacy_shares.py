from django.db import migrations

SNAPSHOT_VERSION = "sharing.snapshot.v1"


def _number(value):
    return round(float(value or 0), 2)


def _nutrition(protein, carbs, fat):
    protein = _number(protein)
    carbs = _number(carbs)
    fat = _number(fat)
    return {
        "calories": _number(protein * 4 + carbs * 4 + fat * 9),
        "protein_grams": protein,
        "carbs_grams": carbs,
        "fat_grams": fat,
    }


def _meal_snapshot(MealFood, meal, *, variant="", time=None):
    foods = []
    protein = carbs = fat = 0.0
    for row in MealFood.objects.filter(meal_id=meal.id).select_related("food").order_by("order", "id"):
        factor = float(row.quantity or 0) / 100
        item_nutrition = _nutrition(
            float(row.food.protein or 0) * factor,
            float(row.food.carbs or 0) * factor,
            float(row.food.fat or 0) * factor,
        )
        foods.append(
            {
                "name": row.food.name,
                "quantity_grams": _number(row.quantity),
                "nutrition": item_nutrition,
            }
        )
        protein += item_nutrition["protein_grams"]
        carbs += item_nutrition["carbs_grams"]
        fat += item_nutrition["fat_grams"]
    subject = {"type": "meal", "title": meal.name}
    if variant:
        subject["variant"] = variant
    snapshot = {
        "schema_version": SNAPSHOT_VERSION,
        "subject": subject,
        "summary": {"food_count": len(foods)},
        "nutrition": _nutrition(protein, carbs, fat),
        "foods": foods,
    }
    if time:
        snapshot["time"] = time.isoformat(timespec="minutes")
    return snapshot


def _dailyplan_snapshot(DailyPlanMeal, MealFood, dailyplan):
    meals = []
    protein = carbs = fat = 0.0
    food_count = 0
    rows = DailyPlanMeal.objects.filter(dailyplan_id=dailyplan.id).select_related("meal").order_by("order", "id")
    for row in rows:
        meal = _meal_snapshot(MealFood, row.meal, time=row.hour)
        meal["name"] = meal.pop("subject")["title"]
        meals.append(meal)
        nutrition = meal["nutrition"]
        protein += nutrition["protein_grams"]
        carbs += nutrition["carbs_grams"]
        fat += nutrition["fat_grams"]
        food_count += meal["summary"]["food_count"]
        meal.pop("schema_version", None)
        meal.pop("summary", None)
        if "time" not in meal:
            meal["time"] = None
    return {
        "schema_version": SNAPSHOT_VERSION,
        "subject": {"type": "daily_plan", "title": dailyplan.name},
        "summary": {"meal_count": len(meals), "food_count": food_count},
        "nutrition": _nutrition(protein, carbs, fat),
        "meals": meals,
    }


def _program_snapshot(ProgramDay, DailyPlanMeal, MealFood, program):
    days = []
    protein = carbs = fat = 0.0
    meal_count = food_count = 0
    for row in ProgramDay.objects.filter(program_id=program.id).select_related("dailyplan").order_by(
        "week_number", "day_number", "id"
    ):
        plan = _dailyplan_snapshot(DailyPlanMeal, MealFood, row.dailyplan)
        days.append({"week_number": row.week_number, "day_number": row.day_number, "plan": plan})
        protein += plan["nutrition"]["protein_grams"]
        carbs += plan["nutrition"]["carbs_grams"]
        fat += plan["nutrition"]["fat_grams"]
        meal_count += plan["summary"]["meal_count"]
        food_count += plan["summary"]["food_count"]
    duration_weeks = max(int(program.duration_weeks or 1), 1)
    return {
        "schema_version": SNAPSHOT_VERSION,
        "subject": {"type": "program", "title": program.name},
        "summary": {
            "duration_weeks": duration_weeks,
            "filled_days": len(days),
            "meal_count": meal_count,
            "food_count": food_count,
        },
        "nutrition": _nutrition(protein, carbs, fat),
        "days": days,
    }


def _migrate_share(*, legacy, reference, subject_type, source_id, snapshot, models):
    ShareResource, ShareInvitation, ShareClaim, InboxItem = models
    resource, _ = ShareResource.objects.update_or_create(
        legacy_reference=reference,
        defaults={
            "sender_id": legacy.sender_id,
            "subject_type": subject_type,
            "source_object_id": source_id,
            "snapshot": snapshot,
            "snapshot_schema_version": SNAPSHOT_VERSION,
            "claim_policy": "single",
            "status": "active",
            "expires_at": None,
            "revoked_at": None,
        },
    )
    ShareResource.objects.filter(pk=resource.pk).update(
        created_at=legacy.created_at,
        updated_at=legacy.created_at,
    )
    invitation, _ = ShareInvitation.objects.get_or_create(
        resource_id=resource.id,
        recipient_email=legacy.recipient_email.strip().lower(),
    )
    invitation.public_id = legacy.token
    invitation.recipient_user_id = legacy.accepted_by_id
    invitation.subject = legacy.subject or snapshot["subject"]["title"]
    invitation.message = legacy.message or ""
    invitation.status = "claimed" if legacy.accepted_by_id else "delivered"
    invitation.delivered_at = legacy.created_at
    invitation.claimed_at = legacy.created_at if legacy.accepted_by_id else None
    invitation.save()
    ShareInvitation.objects.filter(pk=invitation.pk).update(
        created_at=legacy.created_at,
        updated_at=legacy.created_at,
    )
    if not legacy.accepted_by_id:
        return
    claim, _ = ShareClaim.objects.get_or_create(
        resource_id=resource.id,
        user_id=legacy.accepted_by_id,
        defaults={"invitation_id": invitation.id, "source": "email"},
    )
    ShareClaim.objects.filter(pk=claim.pk).update(
        invitation_id=invitation.id,
        source="email",
        created_at=legacy.created_at,
    )
    item, _ = InboxItem.objects.get_or_create(
        owner_id=legacy.accepted_by_id,
        resource_id=resource.id,
        defaults={"claim_id": claim.id},
    )
    item.claim_id = claim.id
    item.read_at = legacy.created_at if legacy.is_read else None
    item.dismissed_at = legacy.created_at if legacy.dismissed or legacy.removed else None
    item.is_favorite = legacy.is_favorite
    item.save()
    InboxItem.objects.filter(pk=item.pk).update(
        created_at=legacy.created_at,
        updated_at=legacy.created_at,
    )


def backfill_all_legacy_shares(apps, schema_editor):
    DailyPlanShare = apps.get_model("notas", "DailyPlanShare")
    FoodShare = apps.get_model("notas", "FoodShare")
    MealShare = apps.get_model("notas", "MealShare")
    DailyPlanMealShare = apps.get_model("notas", "DailyPlanMealShare")
    ProgramShare = apps.get_model("notas", "ProgramShare")
    DailyPlanMeal = apps.get_model("notas", "DailyPlanMeal")
    MealFood = apps.get_model("notas", "MealFood")
    ProgramDay = apps.get_model("notas", "ProgramDay")
    models = (
        apps.get_model("notas", "ShareResource"),
        apps.get_model("notas", "ShareInvitation"),
        apps.get_model("notas", "ShareClaim"),
        apps.get_model("notas", "InboxItem"),
    )

    for legacy in DailyPlanShare.objects.select_related("dailyplan").iterator():
        _migrate_share(
            legacy=legacy,
            reference=f"dailyplan:{legacy.id}",
            subject_type="daily_plan",
            source_id=legacy.dailyplan_id,
            snapshot=_dailyplan_snapshot(DailyPlanMeal, MealFood, legacy.dailyplan),
            models=models,
        )
    for legacy in FoodShare.objects.select_related("food").iterator():
        food = legacy.food
        _migrate_share(
            legacy=legacy,
            reference=f"food:{legacy.id}",
            subject_type="food",
            source_id=legacy.food_id,
            snapshot={
                "schema_version": SNAPSHOT_VERSION,
                "subject": {"type": "food", "title": food.name},
                "summary": {"basis_grams": 100},
                "nutrition": _nutrition(food.protein, food.carbs, food.fat),
            },
            models=models,
        )
    for legacy in MealShare.objects.select_related("meal").iterator():
        _migrate_share(
            legacy=legacy,
            reference=f"meal:{legacy.id}",
            subject_type="meal",
            source_id=legacy.meal_id,
            snapshot=_meal_snapshot(MealFood, legacy.meal),
            models=models,
        )
    for legacy in DailyPlanMealShare.objects.select_related("dailyplan_meal__meal").iterator():
        _migrate_share(
            legacy=legacy,
            reference=f"dpm:{legacy.id}",
            subject_type="meal",
            source_id=legacy.dailyplan_meal_id,
            snapshot=_meal_snapshot(
                MealFood,
                legacy.dailyplan_meal.meal,
                variant="daily_plan_meal",
                time=legacy.dailyplan_meal.hour,
            ),
            models=models,
        )
    for legacy in ProgramShare.objects.select_related("program").iterator():
        _migrate_share(
            legacy=legacy,
            reference=f"program:{legacy.id}",
            subject_type="program",
            source_id=legacy.program_id,
            snapshot=_program_snapshot(ProgramDay, DailyPlanMeal, MealFood, legacy.program),
            models=models,
        )


def reverse_backfill(apps, schema_editor):
    ShareResource = apps.get_model("notas", "ShareResource")
    for prefix in ("dailyplan:", "food:", "meal:", "dpm:", "program:"):
        ShareResource.objects.filter(legacy_reference__startswith=prefix).delete()


class Migration(migrations.Migration):
    dependencies = [("notas", "0059_shareresource_preview_evidence")]
    operations = [migrations.RunPython(backfill_all_legacy_shares, reverse_backfill)]
