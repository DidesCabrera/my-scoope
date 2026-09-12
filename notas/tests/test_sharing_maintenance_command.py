import json
from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from notas.domain.models import ShareResource


class SharingMaintenanceCommandTests(TestCase):
    def test_dry_run_reports_due_resource_without_changing_it(self):
        sender = User.objects.create_user("maintenance-sender")
        resource = ShareResource.objects.create(
            sender=sender,
            subject_type=ShareResource.SubjectType.DAILY_PLAN,
            snapshot={},
            snapshot_schema_version="sharing.snapshot.v1",
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        output = StringIO()

        call_command(
            "maintain_sharing_resources",
            "--retention-days",
            "30",
            "--dry-run",
            stdout=output,
        )

        payload = json.loads(output.getvalue())
        resource.refresh_from_db()
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["resources_expired"], 1)
        self.assertEqual(resource.status, ShareResource.Status.ACTIVE)
