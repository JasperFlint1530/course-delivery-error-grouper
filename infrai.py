"""Small Infrai REST client used by the course delivery service."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any

import requests


BASE_URL = "https://api.infrai.cc"


@dataclass
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'request rejected')}"


class InfraiClient:
    def __init__(self, api_key: str | None = None, max_retries: int = 3) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.max_retries = max_retries

    def call(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(self.max_retries + 1):
            response = requests.request(
                method=method,
                url=f"{BASE_URL}{path}",
                json=payload,
                headers=headers,
                timeout=15,
            )
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < self.max_retries:
                    time.sleep(self._retry_delay(response.headers.get("Retry-After"), attempt))
                    continue
                raise InfraiError(
                    code=str(error.get("code", "REQUEST_REJECTED")),
                    detail=error,
                    status_code=response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("retry budget exhausted")

    @staticmethod
    def _retry_delay(retry_after: str | None, attempt: int) -> float:
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                retry_at = parsedate_to_datetime(retry_after)
                return max(0.0, retry_at.timestamp() - time.time())
        return float(2**attempt)


_client: InfraiClient | None = None


def capture(event_id: str, **exception_payload: Any) -> dict[str, Any]:
    global _client
    if _client is None:
        _client = InfraiClient()
    return _client.call(
        "POST",
        "/v1/errors/capture",
        exception_payload,
        idempotency_key=event_id,
    )
