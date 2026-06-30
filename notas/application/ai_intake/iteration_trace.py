"""Compatibility imports for proposal iteration trace helpers.

The canonical home for this metadata contract is now
``notas.application.dto.proposal_iteration_trace`` so read-models,
presentation and integration adapters can reuse it without depending on the
AI chat bounded context.
"""

from notas.application.dto.proposal_iteration_trace import (  # noqa: F401
    PlanIterationTrace,
    extract_plan_iteration_trace,
)
