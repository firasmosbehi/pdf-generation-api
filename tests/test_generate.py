from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import routes
from app.main import app

client = TestClient(app)


def test_generate_pdf_from_raw_html(monkeypatch, api_key: str) -> None:
    async def fake_generate_pdf(html: str) -> bytes:
        assert "Hello PDF" in html
        assert "color: red" in html
        return b"%PDF-1.7\nfake"

    monkeypatch.setattr(routes.pdf_service, "generate_pdf", fake_generate_pdf)

    response = client.post(
        "/generate",
        files=[
            ("html_file", ("input.html", "<h1>Hello PDF</h1>", "text/html")),
            ("css_file", ("styles.css", "h1 { color: red; }", "text/css")),
        ],
        data={"filename": "hello"},
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "hello.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_generate_pdf_from_template(monkeypatch, api_key: str) -> None:
    async def fake_generate_pdf(html: str) -> bytes:
        assert "Acme Corp" in html
        return b"%PDF-1.7\ntemplate"

    monkeypatch.setattr(routes.pdf_service, "generate_pdf", fake_generate_pdf)

    response = client.post(
        "/generate",
        files=[
            (
                "template_file",
                (
                    "invoice.html",
                    "<h1>{{ customer_name }}</h1><p>{{ invoice_number }}</p>",
                    "text/html",
                ),
            ),
            (
                "data_file",
                (
                    "data.json",
                    '{"customer_name":"Acme Corp","invoice_number":"INV-101"}',
                    "application/json",
                ),
            ),
        ],
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_generate_rejects_non_object_data_file(api_key: str) -> None:
    response = client.post(
        "/generate",
        files=[
            ("template_file", ("invoice.html", "<h1>{{ customer_name }}</h1>", "text/html")),
            ("data_file", ("data.json", '["bad"]', "application/json")),
        ],
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 422
    assert "json object" in response.json()["detail"].lower()


def test_generate_rejects_invalid_json_in_data_file(api_key: str) -> None:
    response = client.post(
        "/generate",
        files=[
            ("template_file", ("invoice.html", "<h1>{{ customer_name }}</h1>", "text/html")),
            ("data_file", ("data.json", "{", "application/json")),
        ],
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 422
    assert "valid json" in response.json()["detail"].lower()


def test_generate_requires_exactly_one_render_file(api_key: str) -> None:
    response = client.post("/generate", data={"filename": "x"}, headers={"X-API-Key": api_key})
    assert response.status_code == 422
    assert "exactly one" in response.json()["detail"].lower()


def test_generate_rejects_two_render_files(api_key: str) -> None:
    response = client.post(
        "/generate",
        files=[
            ("html_file", ("input.html", "<p>Hi</p>", "text/html")),
            ("template_file", ("invoice.html", "<h1>{{ customer_name }}</h1>", "text/html")),
        ],
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 422
    assert "exactly one" in response.json()["detail"].lower()
