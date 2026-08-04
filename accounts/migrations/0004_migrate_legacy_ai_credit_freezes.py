from django.db import migrations


def migrate_latest_legacy_freezes(apps, schema_editor):
    """Carry the latest per-user operational block into the account wallet.

    Legacy quotas are period snapshots, so an older blocked period must not
    freeze a user whose latest quota is unblocked.
    """

    LegacyQuota = apps.get_model("ai_assistant", "AIUserCreditQuota")
    CreditWallet = apps.get_model("accounts", "CreditWallet")

    seen_user_ids = set()
    latest_quotas = LegacyQuota.objects.order_by("user_id", "-period", "-updated_at", "-pk")
    for quota in latest_quotas.iterator():
        if quota.user_id in seen_user_ids:
            continue
        seen_user_ids.add(quota.user_id)
        if not quota.hard_blocked:
            continue

        wallet, _ = CreditWallet.objects.get_or_create(
            user_id=quota.user_id,
            defaults={
                "balance": 0,
                "reserved_balance": 0,
                "period": quota.period,
                "plan_snapshot_code": quota.plan_code,
            },
        )
        wallet.is_frozen = True
        wallet.frozen_reason = "Migrated from latest legacy AI credit quota"
        wallet.frozen_at = quota.updated_at
        wallet.save(update_fields=["is_frozen", "frozen_reason", "frozen_at", "updated_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_creditwallet_operational_freeze"),
        ("ai_assistant", "0003_ai_credits"),
    ]

    operations = [
        migrations.RunPython(migrate_latest_legacy_freezes, migrations.RunPython.noop),
    ]
