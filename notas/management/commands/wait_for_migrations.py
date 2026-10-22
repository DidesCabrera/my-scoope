import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = "Wait until the database schema includes every migration known by this release."

    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=int, default=600)
        parser.add_argument("--interval", type=float, default=5)

    def handle(self, *args, **options):
        timeout = max(0, options["timeout"])
        interval = max(0.1, options["interval"])
        deadline = time.monotonic() + timeout

        while True:
            executor = MigrationExecutor(connection)
            targets = executor.loader.graph.leaf_nodes()
            pending = executor.migration_plan(targets)
            if not pending:
                self.stdout.write(self.style.SUCCESS("Database migrations are current."))
                return
            if time.monotonic() >= deadline:
                names = ", ".join(f"{migration.app_label}.{migration.name}" for migration, _backwards in pending[:5])
                raise CommandError(f"Database migrations did not become current before timeout: {names}")
            time.sleep(interval)
