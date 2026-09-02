"""Course-delivery decisions and error capture."""

from __future__ import annotations

import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, TypeVar

from infrai import capture


Result = TypeVar("Result")


@dataclass(frozen=True)
class DeliveryContext:
    event_id: str
    course_id: str
    learner_id: str
    delivery_step: str
    deadline: datetime


def reporting_priority(deadline: datetime, observed_at: datetime) -> str:
    """Expired learner work needs an educator's attention first."""
    return "urgent" if deadline <= observed_at else "monitor"


def deliver_course_step(
    context: DeliveryContext,
    operation: Callable[[], Result],
    observed_at: datetime | None = None,
) -> Result:
    """Run a delivery operation, capture its exception, then preserve its semantics."""
    now = observed_at or datetime.now(timezone.utc)
    try:
        return operation()
    except Exception as exc:
        exception_type = type(exc).__name__
        capture(
            event_id=context.event_id,
            title=f"Course delivery failed at {context.delivery_step}",
            message=f"{exception_type}: {exc}",
            level="error",
            fingerprint=[context.course_id, context.delivery_step, exception_type],
            exception=traceback.format_exc(),
            context={
                "course_id": context.course_id,
                "learner_id": context.learner_id,
                "delivery_step": context.delivery_step,
                "deadline": context.deadline.isoformat(),
                "reporting_priority": reporting_priority(context.deadline, now),
            },
        )
        raise
