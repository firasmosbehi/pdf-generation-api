from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api import routes
from app.main import app
from app.services.billing_store import update_monthly_quota_for_api_key

client = TestClient(app)


def test_generate_requires_api_key() -> None:
    response = client.post(
        "/generate",
        files=[("html_file", ("input.html", "<h1>Hello</h1>", "text/html"))],
    )
    assert response.status_code == 401
    assert "missing api key" in response.json()["detail"].lower()


def test_generate_rejects_invalid_api_key() -> None:
    response = client.post(
        "/generate",
        files=[("html_file", ("input.html", "<h1>Hello</h1>", "text/html"))],
        headers={"X-API-Key": "invalid-key"},
    )
    assert response.status_code == 401
    assert "invalid api key" in response.json()["detail"].lower()


def test_generate_rejects_quota_exceeded(monkeypatch, api_key: str) -> None:
    async def fake_generate_pdf(html: str) -> bytes:
        return b"%PDF-1.7\nfake"

    monkeypatch.setattr(routes.pdf_service, "generate_pdf", fake_generate_pdf)
    update_monthly_quota_for_api_key(raw_api_key=api_key, monthly_quota=0)

    response = client.post(
        "/generate",
        files=[("html_file", ("input.html", "<h1>Hello</h1>", "text/html"))],
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 429
    assert "quota exceeded" in response.json()["detail"].lower()


def test_admin_can_create_api_key(api_key: str) -> None:
    response = client.post(
        "/admin/api-keys",
        headers={"X-Admin-Token": "test-admin-token"},
        json={"account_name": "Acme Billing", "plan": "free", "monthly_quota": 7},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["account_name"] == "Acme Billing"
    assert body["plan"] == "free"
    assert body["monthly_quota"] == 7
    assert isinstance(body["api_key"], str)
    assert len(body["api_key"]) >= 20


def test_admin_usage_summary(monkeypatch, api_key: str) -> None:
    async def fake_generate_pdf(html: str) -> bytes:
        return b"%PDF-1.7\nfake-usage"

    monkeypatch.setattr(routes.pdf_service, "generate_pdf", fake_generate_pdf)

    generate_response = client.post(
        "/generate",
        files=[("html_file", ("input.html", "<h1>Hello</h1>", "text/html"))],
        headers={"X-API-Key": api_key},
    )
    assert generate_response.status_code == 200

    month = datetime.now(timezone.utc).strftime("%Y-%m")
    usage_response = client.get(
        "/admin/usage",
        headers={"X-Admin-Token": "test-admin-token"},
        params={"api_key": api_key, "month": month},
    )
    assert usage_response.status_code == 200
    body = usage_response.json()
    assert body["month"] == month
    assert body["successful_requests"] == 1
    assert body["total_requests"] >= 1
    assert body["total_pdf_bytes"] > 0
