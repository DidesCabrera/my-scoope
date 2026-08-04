from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from ai_assistant.application.async_jobs import (
    AsyncJobContractError,
    claim_next_async_job,
    enqueue_async_job,
    run_one_async_job,
)
from ai_assistant.models import AIAsyncJob

HANDLERS = {
    "echo": "ai_assistant.tests.async_job_handlers.echo_job",
    "fail": "ai_assistant.tests.async_job_handlers.failing_job",
}


@override_settings(AI_ASYNC_JOB_HANDLERS=HANDLERS, CACHE_URL="")
class AIAsyncJobTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="async-job-user")

    def test_enqueue_is_idempotent_for_user_kind_and_key(self):
        first, first_created = enqueue_async_job(
            user=self.user,
            kind="echo",
            idempotency_key="mobile-request-1",
            request_payload={"value": 1},
            lane_key="chat:1",
        )
        second, second_created = enqueue_async_job(
            user=self.user,
            kind="echo",
            idempotency_key="mobile-request-1",
            request_payload={"value": 1},
            lane_key="chat:1",
        )

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.request_payload, {"value": 1})

        with self.assertRaises(AsyncJobContractError):
            enqueue_async_job(
                user=self.user,
                kind="echo",
                idempotency_key="mobile-request-1",
                request_payload={"value": 2},
                lane_key="chat:1",
            )

    def test_worker_persists_success_result(self):
        job, _ = enqueue_async_job(
            user=self.user,
            kind="echo",
            idempotency_key="success-1",
            request_payload={"value": "ok"},
        )

        processed = run_one_async_job()

        self.assertEqual(processed.pk, job.pk)
        self.assertEqual(processed.status, AIAsyncJob.Status.SUCCEEDED)
        self.assertEqual(processed.attempts, 1)
        self.assertEqual(processed.result_payload, {"echo": "ok", "attempts": 1})
        self.assertIsNotNone(processed.completed_at)

    def test_worker_retries_then_marks_terminal_failure(self):
        job, _ = enqueue_async_job(
            user=self.user,
            kind="fail",
            idempotency_key="failure-1",
            request_payload={},
            max_attempts=2,
        )

        first = run_one_async_job()

        self.assertEqual(first.status, AIAsyncJob.Status.RETRYING)
        self.assertEqual(first.attempts, 1)
        AIAsyncJob.objects.filter(pk=job.pk).update(available_at=timezone.now())
        second = run_one_async_job()
        self.assertEqual(second.status, AIAsyncJob.Status.FAILED)
        self.assertEqual(second.attempts, 2)
        self.assertEqual(second.error_code, "RuntimeError")
        self.assertIsNotNone(second.completed_at)

    def test_expired_lease_is_reclaimed(self):
        job = AIAsyncJob.objects.create(
            user=self.user,
            kind="echo",
            idempotency_key="expired-lease",
            request_payload={"value": 1},
            status=AIAsyncJob.Status.RUNNING,
            attempts=1,
            leased_at=timezone.now() - timedelta(minutes=5),
            lease_expires_at=timezone.now() - timedelta(seconds=1),
        )

        claimed = claim_next_async_job(lease_seconds=60)

        self.assertEqual(claimed.pk, job.pk)
        self.assertEqual(claimed.attempts, 2)
        self.assertGreater(claimed.lease_expires_at, timezone.now())

    def test_active_lane_prevents_parallel_turn_claim(self):
        future = timezone.now() + timedelta(minutes=2)
        AIAsyncJob.objects.create(
            user=self.user,
            kind="echo",
            idempotency_key="running",
            lane_key="chat:serial",
            request_payload={},
            status=AIAsyncJob.Status.RUNNING,
            attempts=1,
            lease_expires_at=future,
        )
        AIAsyncJob.objects.create(
            user=self.user,
            kind="echo",
            idempotency_key="queued",
            lane_key="chat:serial",
            request_payload={},
        )

        self.assertIsNone(claim_next_async_job())
