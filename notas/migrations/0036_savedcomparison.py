import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("notas", "0035_dailyplan_summary_cache"),
    ]

    operations = [
        migrations.CreateModel(
            name="SavedComparison",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("foods", "Alimentos"), ("meals", "Comidas"), ("dailyplans", "Planes diarios")], max_length=20)),
                ("name", models.CharField(max_length=160)),
                ("payload", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_comparisons", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-updated_at", "-id"],
                "indexes": [models.Index(fields=["owner", "kind", "-updated_at"], name="savedcomp_owner_kind_idx")],
            },
        ),
    ]
