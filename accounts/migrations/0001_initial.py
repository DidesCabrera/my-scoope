# Generated manually for ACC01.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AccountPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(help_text="Stable commercial identifier. Do not depend on the display name.", max_length=60, unique=True)),
                ("name", models.CharField(max_length=80)),
                ("description", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("archived", "Archived")], db_index=True, default="draft", max_length=20)),
                ("display_order", models.PositiveSmallIntegerField(default=100)),
                ("included_monthly_credits", models.PositiveIntegerField(default=0, help_text="Credits granted by this plan in a monthly period. Zero means no included credits.")),
                ("daily_credit_limit", models.PositiveIntegerField(blank=True, help_text="Optional daily credit cap. Empty means no explicit daily cap.", null=True)),
                ("monthly_credit_limit", models.PositiveIntegerField(blank=True, help_text="Optional monthly credit cap. Empty means no explicit monthly cap.", null=True)),
                ("entitlements", models.JSONField(blank=True, default=dict, help_text="Commercial feature flags and limits resolved by accounts services.")),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["display_order", "name"],
            },
        ),
        migrations.CreateModel(
            name="AccountSubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("trialing", "Trialing"), ("active", "Active"), ("past_due", "Past due"), ("canceled", "Canceled"), ("expired", "Expired")], db_index=True, default="active", max_length=20)),
                ("source", models.CharField(choices=[("manual", "Manual"), ("seed", "Seed"), ("migration", "Migration"), ("billing", "Billing"), ("internal", "Internal")], default="manual", max_length=20)),
                ("current_period_start", models.DateTimeField(blank=True, null=True)),
                ("current_period_end", models.DateTimeField(blank=True, null=True)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="subscriptions", to="accounts.accountplan")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="account_subscription", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at", "user_id"],
            },
        ),
        migrations.AddIndex(
            model_name="accountplan",
            index=models.Index(fields=["status", "display_order"], name="acct_plan_status_order_idx"),
        ),
        migrations.AddIndex(
            model_name="accountsubscription",
            index=models.Index(fields=["status", "current_period_end"], name="acct_sub_status_period_idx"),
        ),
        migrations.AddIndex(
            model_name="accountsubscription",
            index=models.Index(fields=["source", "created_at"], name="acct_sub_source_created_idx"),
        ),
    ]
