from django.db import migrations


def enable_pro_personal_preparations(apps, schema_editor):
    AccountPlan = apps.get_model("accounts", "AccountPlan")
    for plan in AccountPlan.objects.filter(slug="pro"):
        entitlements = dict(plan.entitlements or {})
        workspace = dict(entitlements.get("nutrition_workspace") or {})
        workspace["can_use_personal_preparations"] = True
        entitlements["nutrition_workspace"] = workspace
        plan.entitlements = entitlements
        plan.save(update_fields=["entitlements"])


def disable_pro_personal_preparations(apps, schema_editor):
    AccountPlan = apps.get_model("accounts", "AccountPlan")
    for plan in AccountPlan.objects.filter(slug="pro"):
        entitlements = dict(plan.entitlements or {})
        workspace = dict(entitlements.get("nutrition_workspace") or {})
        workspace.pop("can_use_personal_preparations", None)
        entitlements["nutrition_workspace"] = workspace
        plan.entitlements = entitlements
        plan.save(update_fields=["entitlements"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0008_pro_supplements_entitlement")]
    operations = [migrations.RunPython(enable_pro_personal_preparations, disable_pro_personal_preparations)]
