from django.db import migrations


def add_mcp_entitlement(apps, schema_editor):
    AccountPlan = apps.get_model("accounts", "AccountPlan")
    for plan in AccountPlan.objects.filter(slug__in=("free", "basic", "pro")):
        entitlements = dict(plan.entitlements or {})
        integrations = dict(entitlements.get("integrations") or {})
        mcp = dict(integrations.get("mcp") or {})
        mcp["enabled"] = plan.slug == "pro"
        integrations["mcp"] = mcp
        entitlements["integrations"] = integrations
        plan.entitlements = entitlements
        plan.save(update_fields=["entitlements"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0006_purchased_credit_wallet")]
    operations = [migrations.RunPython(add_mcp_entitlement, migrations.RunPython.noop)]
