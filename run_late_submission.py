"""Send one late course-delivery failure through the local service."""

from fastapi.testclient import TestClient

from educator_service import service


def main() -> None:
    response = TestClient(service).post(
        "/delivery-errors",
        json={
            "event_id": "delivery-catalog-2048",
            "course_id": "python-checkout-101",
            "learner_id": "learner-42",
            "delivery_step": "assignment-publish",
            "deadline": "2025-01-15T16:00:00Z",
            "backend_message": "assignment catalog response was incomplete",
        },
    )
    response.raise_for_status()
    print(response.json())


if __name__ == "__main__":
    main()
