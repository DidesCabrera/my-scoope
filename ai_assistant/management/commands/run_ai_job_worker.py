from __future__ import annotations

import time

from django.core.management.base import BaseCommand

from ai_assistant.application.async_jobs import run_one_async_job
from ai_assistant.infrastructure.job_signal import wait_for_job_signal


class Command(BaseCommand):
    help = "Run the durable AI job worker. PostgreSQL is authoritative; Redis only wakes the worker."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--max-jobs", type=int, default=0)
        parser.add_argument("--poll-interval", type=int, default=5)

    def handle(self, *args, **options):
        once = bool(options["once"])
        max_jobs = max(0, int(options["max_jobs"] or 0))
        poll_interval = max(1, min(int(options["poll_interval"] or 5), 30))
        processed = 0
        while True:
            job = run_one_async_job()
            if job is not None:
                processed += 1
                self.stdout.write(f"job={job.public_id} kind={job.kind} status={job.status}")
                if once or (max_jobs and processed >= max_jobs):
                    return
                continue
            if once or (max_jobs and processed >= max_jobs):
                return
            signal_received = wait_for_job_signal(timeout_seconds=poll_interval)
            if signal_received is None:
                time.sleep(poll_interval)
