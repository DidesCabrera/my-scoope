"""Track only review artifacts created by this execution context."""

from contextlib import contextmanager
from contextvars import ContextVar

from django.db.models.signals import post_save

from ai_assistant.models import AIPreparedAction
from notas.domain.models import NutritionProposal

_active_capture = ContextVar("evaluation_artifact_capture", default=None)


@contextmanager
def capture_review_artifacts(user):
    artifacts = {"nutrition_proposals": set(), "prepared_actions": set()}
    capture = object()
    token = _active_capture.set(capture)

    def record(sender, instance, created, **kwargs):
        if not created or _active_capture.get() is not capture:
            return
        owner = instance.created_by_id if sender is NutritionProposal else instance.user_id
        if owner == user.pk:
            artifacts["nutrition_proposals" if sender is NutritionProposal else "prepared_actions"].add(instance.pk)

    for model in (NutritionProposal, AIPreparedAction):
        post_save.connect(record, sender=model, weak=False)
    try:
        yield artifacts
    finally:
        for model in (NutritionProposal, AIPreparedAction):
            post_save.disconnect(record, sender=model)
        _active_capture.reset(token)
