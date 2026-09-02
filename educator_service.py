"""Typed HTTP boundary for course delivery failures."""

from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from course_delivery import DeliveryContext, deliver_course_step, reporting_priority
from infrai import InfraiError


class CourseDeliveryRequest(BaseModel):
    event_id: str
    course_id: str
    learner_id: str
    delivery_step: str
    deadline: datetime
    backend_message: str


class EducatorReport(BaseModel):
    captured: bool
    priority: str
    course_id: str
    learner_id: str


service = FastAPI(title="Course delivery error reporter")


@service.post("/delivery-errors", response_model=EducatorReport)
def capture_delivery_error(request: CourseDeliveryRequest) -> EducatorReport:
    observed_at = datetime.now(request.deadline.tzinfo)

    def failed_backend_call() -> None:
        raise RuntimeError(request.backend_message)

    context = DeliveryContext(
        event_id=request.event_id,
        course_id=request.course_id,
        learner_id=request.learner_id,
        delivery_step=request.delivery_step,
        deadline=request.deadline,
    )
    try:
        deliver_course_step(context, failed_backend_call, observed_at)
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=exc.detail) from exc
    except RuntimeError:
        pass

    return EducatorReport(
        captured=True,
        priority=reporting_priority(request.deadline, observed_at),
        course_id=request.course_id,
        learner_id=request.learner_id,
    )
