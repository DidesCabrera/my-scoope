from django.conf import settings
from django.db import migrations

NOTAS_INSTALLED = any(app == "notas" or app.startswith("notas.apps.") for app in settings.INSTALLED_APPS)


class Migration(migrations.Migration):
    dependencies = [("food_catalog", "0023_alter_catalogfoodportion_household_measure")]

    # The operational table remains in place; notas takes ownership of its
    # existing rows through a matching db_table in its own migration.
    operations = (
        [
            migrations.SeparateDatabaseAndState(
                database_operations=[],
                state_operations=[migrations.DeleteModel(name="LegacyFoodVisualAsset")],
            )
        ]
        if NOTAS_INSTALLED else []
    )
