from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ai_assistant.models import AIUsageEvent


class Command(BaseCommand):
    help = (
        "Check recent post-tool follow-up health. Returns a non-zero exit code "
        "when degraded turns exceed the configured threshold."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes",
            type=int,
            default=60,
            help="Lookback window in minutes (default: 60).",
        )
        parser.add_argument(
            "--max-degraded",
            type=int,
            default=0,
            help="Maximum degraded tool turns allowed in the window (default: 0).",
        )

    def handle(self, *args, **options):
        minutes = max(1, int(options["minutes"]))
        max_degraded = max(0, int(options["max_degraded"]))
        since = timezone.now() - timedelta(minutes=minutes)

        tool_turns = AIUsageEvent.objects.filter(
            created_at__gte=since,
            tool_calls_count__gt=0,
        )
        total = tool_turns.count()
        degraded = tool_turns.filter(status=AIUsageEvent.Status.DEGRADED).count()
        healthy = tool_turns.filter(status=AIUsageEvent.Status.COMPLETED).count()
        errors = tool_turns.filter(status=AIUsageEvent.Status.ERROR).count()
        blocked = tool_turns.filter(status=AIUsageEvent.Status.BLOCKED).count()
        degraded_rate = (degraded / total * 100) if total else 0.0

        self.stdout.write(
            "Post-tool follow-up health "
            f"window={minutes}m total={total} healthy={healthy} degraded={degraded} "
            f"errors={errors} blocked={blocked} degraded_rate={degraded_rate:.2f}%"
        )

        if degraded > max_degraded:
            recent = list(
                tool_turns.filter(status=AIUsageEvent.Status.DEGRADED)
                .order_by("-created_at")
                .values_list("id", "error_type", "created_at")[:5]
            )
            detail = ", ".join(
                f"event={event_id} error={error_type or '-'} at={created_at.isoformat()}"
                for event_id, error_type, created_at in recent
            )
            raise CommandError(
                f"Post-tool follow-up degradation threshold exceeded: "
                f"{degraded}>{max_degraded}. Recent: {detail or 'none'}"
            )

        self.stdout.write(self.style.SUCCESS("Post-tool follow-up health: PASS"))
