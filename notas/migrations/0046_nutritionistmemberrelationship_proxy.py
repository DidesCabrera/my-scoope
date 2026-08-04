from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("notas", "0045_migrate_profile_plan_to_accounts"),
    ]

    operations = [
        migrations.CreateModel(
            name="NutritionistMemberRelationship",
            fields=[],
            options={
                "verbose_name": "nutritionist/member relationship",
                "verbose_name_plural": "nutritionist/member relationships",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("notas.subscription",),
        ),
    ]
