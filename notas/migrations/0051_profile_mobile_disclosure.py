from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notas", "0050_notificationdelivery_channel_applepushsubscription_and_more")]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="mobile_disclosure_accepted_at",
            field=models.DateTimeField(
                blank=True,
                help_text="When the current mobile disclosure was explicitly acknowledged.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="mobile_disclosure_version",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Latest mobile safety and privacy disclosure acknowledged by the user.",
                max_length=32,
            ),
        ),
    ]
