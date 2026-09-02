from datetime import datetime, timezone

import pytest

import course_delivery
from course_delivery import DeliveryContext, deliver_course_step


def test_expired_delivery_is_urgent_and_groups_without_learner_id(monkeypatch) -> None:
    captured: dict = {}
    monkeypatch.setattr(course_delivery, "capture", lambda **body: captured.update(body))
    context = DeliveryContext(
        event_id="delivery-77",
        course_id="checkout-math",
        learner_id="learner-9",
        delivery_step="deadline-sync",
        deadline=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )

    with pytest.raises(RuntimeError, match="grade service rejected update"):
        deliver_course_step(
            context,
            lambda: (_ for _ in ()).throw(RuntimeError("grade service rejected update")),
            observed_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
        )

    assert captured["context"]["reporting_priority"] == "urgent"
    assert captured["fingerprint"] == ["checkout-math", "deadline-sync", "RuntimeError"]
    assert "learner-9" not in captured["fingerprint"]
