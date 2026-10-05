from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notas", "0065_culinary_library_and_program_requirements"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="food",
            index=models.Index(
                fields=["created_by", "is_active", "list_order", "name"],
                name="food_mobile_library_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="meal",
            index=models.Index(
                fields=["created_by", "is_draft", "list_order", "created_at"],
                name="meal_mobile_library_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="dailyplan",
            index=models.Index(
                fields=["created_by", "source", "is_draft", "list_order"],
                name="dayplan_mobile_library_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="program",
            index=models.Index(
                fields=["created_by", "list_order", "created_at"],
                name="program_mobile_library_idx",
            ),
        ),
    ]
