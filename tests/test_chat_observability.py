from __future__ import annotations

import json
import asyncio
from pathlib import Path

import httpx

from app import logging_config
from app.main import app


def test_chat_response_log_exposes_quality_for_dashboard(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post(
                "/chat",
                json={
                    "user_id": "student-01",
                    "session_id": "session-01",
                    "feature": "qa",
                    "message": "Explain observability",
                },
            )

    response = asyncio.run(send_request())

    assert response.status_code == 200
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    response_event = next(event for event in events if event["event"] == "response_sent")
    assert response_event["quality_score"] == response.json()["quality_score"]
    assert response_event["ttft_ms"] == response.json()["ttft_ms"]
    assert response_event["tool_name"] == "retrieval"
    assert response_event["tool_success"] is True


def test_chat_middleware_headers_and_enrichment(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/chat",
                headers={"x-request-id": "req-custom99"},
                json={
                    "user_id": "student-02",
                    "session_id": "session-02",
                    "feature": "summary",
                    "message": "Contact 090 123 4567 or email me test@vinuni.edu.vn",
                },
            )

    response = asyncio.run(send_request())
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-custom99"
    assert "x-response-time-ms" in response.headers

    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    for ev in events:
        if ev.get("service") == "api":
            assert ev["correlation_id"] == "req-custom99"
            assert ev["user_id_hash"] is not None
            assert ev["session_id"] == "session-02"
            assert ev["feature"] == "summary"
            assert ev["model"] is not None

    raw_logs = log_path.read_text(encoding="utf-8")
    assert "090 123 4567" not in raw_logs
    assert "test@vinuni.edu.vn" not in raw_logs
    assert "REDACTED_PHONE_VN" in raw_logs
    assert "REDACTED_EMAIL" in raw_logs

