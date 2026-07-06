# Generated manually for ACC02.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CreditWallet",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("balance", models.PositiveIntegerField(default=0)),
                ("reserved_balance", models.PositiveIntegerField(default=0, help_text="Credits temporarily reserved for in-flight operations.")),
                ("period", models.CharField(blank=True, db_index=True, help_text="Current wallet accounting period in YYYY-MM format when applicable.", max_length=7)),
                ("plan_snapshot_code", models.CharField(blank=True, help_text="Plan slug/code that granted or last refreshed this wallet balance.", max_length=60)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="credit_wallet", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["user_id"],
            },
        ),
        migrations.CreateModel(
            name="CreditLedger",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("grant", "Grant"), ("reserve", "Reserve"), ("consume", "Consume"), ("release", "Release"), ("refund", "Refund"), ("adjustment", "Adjustment"), ("expire", "Expire")], db_index=True, max_length=20)),
                ("credits_delta", models.IntegerField(help_text="Signed credit movement. Grants/refunds are positive; consumes/expirations are negative.")),
                ("reserved_delta", models.IntegerField(default=0, help_text="Signed reserved-credit movement for reservation lifecycle auditing.")),
                ("balance_after", models.IntegerField(help_text="Wallet balance after this movement was applied.")),
                ("reserved_balance_after", models.IntegerField(default=0, help_text="Wallet reserved balance after this movement was applied.")),
                ("period", models.CharField(blank=True, db_index=True, max_length=7)),
                ("plan_snapshot_code", models.CharField(blank=True, max_length=60)),
                ("reference_type", models.CharField(blank=True, help_text="Optional external reference type, for example ai_usage_event.", max_length=120)),
                ("reference_id", models.CharField(blank=True, max_length=120)),
                ("reason", models.CharField(blank=True, max_length=160)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="credit_ledger_entries", to=settings.AUTH_USER_MODEL)),
                ("wallet", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ledger_entries", to="accounts.creditwallet")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="creditwallet",
            index=models.Index(fields=["period", "plan_snapshot_code"], name="acct_wallet_period_plan_idx"),
        ),
        migrations.AddIndex(
            model_name="creditledger",
            index=models.Index(fields=["user", "period"], name="acct_ledger_user_period_idx"),
        ),
        migrations.AddIndex(
            model_name="creditledger",
            index=models.Index(fields=["kind", "created_at"], name="acct_ledger_kind_created_idx"),
        ),
        migrations.AddIndex(
            model_name="creditledger",
            index=models.Index(fields=["reference_type", "reference_id"], name="acct_ledger_reference_idx"),
        ),
    ]
