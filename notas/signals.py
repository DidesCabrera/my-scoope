from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from django.contrib.auth.models import User
from notas.domain.models import Profile, Plan, MealFood
from notas.application.services.nutrition.meal_nutrition import rebuild_meal_cached_state
from notas.application.services.cache.dailyplan_summary import refresh_dailyplans_for_meal
from accounts.models import AccountSubscription
from accounts.services.subscriptions import ensure_account_subscription_for_user


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    if not created:
        return

    # Plan default: primer plan Member
    default_plan = Plan.objects.filter(role="member").first()

    Profile.objects.create(
        user=instance,
        role="member",
        plan=default_plan,
        is_verified=False,
    )
    ensure_account_subscription_for_user(instance, source=AccountSubscription.Source.SEED)


@receiver(post_save, sender=MealFood)
def recompute_meal_on_food_save(sender, instance, **kwargs):
    rebuild_meal_cached_state(instance.meal)
    refresh_dailyplans_for_meal(instance.meal)


@receiver(post_delete, sender=MealFood)
def recompute_meal_on_food_delete(sender, instance, **kwargs):
    rebuild_meal_cached_state(instance.meal)