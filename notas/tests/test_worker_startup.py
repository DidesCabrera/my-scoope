from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase


class WaitForMigrationsCommandTests(SimpleTestCase):
    @patch("notas.management.commands.wait_for_migrations.MigrationExecutor")
    def test_returns_immediately_when_schema_is_current(self, executor_class):
        executor_class.return_value.loader.graph.leaf_nodes.return_value = [("notas", "0001_initial")]
        executor_class.return_value.migration_plan.return_value = []

        call_command("wait_for_migrations", timeout=0)

    @patch("notas.management.commands.wait_for_migrations.time.monotonic", side_effect=[10, 10])
    @patch("notas.management.commands.wait_for_migrations.MigrationExecutor")
    def test_fails_with_pending_migration_after_timeout(self, executor_class, _monotonic):
        migration = SimpleNamespace(app_label="notas", name="0077_calendar_commitment")
        executor_class.return_value.loader.graph.leaf_nodes.return_value = [("notas", migration.name)]
        executor_class.return_value.migration_plan.return_value = [(migration, False)]

        with self.assertRaisesRegex(CommandError, "notas.0077_calendar_commitment"):
            call_command("wait_for_migrations", timeout=0)
