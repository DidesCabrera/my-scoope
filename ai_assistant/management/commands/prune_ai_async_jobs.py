from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from ai_assistant.models import AIAsyncJob


class Command(BaseCommand):
    help = "Delete terminal AI async jobs after their configured retention window."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        days = max(1, int(options["days"] or 30))
        cutoff = timezone.now() - timedelta(days=days)
        jobs = AIAsyncJob.objects.filter(
            status__in=(
                AIAsyncJob.Status.SUCCEEDED,
                AIAsyncJob.Status.FAILED,
                AIAsyncJob.Status.CANCELLED,
            ),
            completed_at__lt=cutoff,
        )
        count = jobs.count()
        if not options["dry_run"]:
            jobs.delete()
        self.stdout.write(f"eligible={count} deleted={0 if options['dry_run'] else count}")
