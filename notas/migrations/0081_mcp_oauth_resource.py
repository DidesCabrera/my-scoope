from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notas", "0080_unique_active_global_food_names")]

    operations = [
        migrations.AddField(
            model_name="mcpusertoken",
            name="resource",
            field=models.URLField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="oauthauthorizationcode",
            name="resource",
            field=models.URLField(blank=True, default="", max_length=500),
        ),
    ]
