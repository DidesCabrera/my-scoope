from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notas", "0091_shareinvitation_read_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="onboarding_plan_proposal_ids",
            field=models.JSONField(blank=True, default=list, help_text="Owned proposal identifiers used to resume the two onboarding minutas."),
        ),
    ]
