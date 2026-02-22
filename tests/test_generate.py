from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import routes
from app.main import app

client = TestClient(app)


def test_generate_pdf_from_raw_html(monkeypatch) -> None:
    async def fake_generate_pdf(html: str) -> bytes:
        assert "Hello PDF" in html
        return b"%PDF-1.7\nfake"

    monkeypatch.setattr(routes.pdf_service, "generate_pdf", fake_generate_pdf)

    response = client.post(
        "/generate",
        json={"html": "<h1>Hello PDF</h1>", "css": "h1 { color: red; }", "filename": "hello"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "hello.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_generate_pdf_from_template(monkeypatch) -> None:
    async def fake_generate_pdf(html: str) -> bytes:
        assert "Acme Corp" in html
        return b"%PDF-1.7\ntemplate"

    monkeypatch.setattr(routes.pdf_service, "generate_pdf", fake_generate_pdf)

    response = client.post(
        "/generate",
        json={
            "template_name": "invoice.html",
            "data": {"customer_name": "Acme Corp", "invoice_number": "INV-101"},
        },
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_generate_pdf_from_form_payload(monkeypatch) -> None:
    async def fake_generate_pdf(html: str) -> bytes:
        assert "Form Mode" in html
        return b"%PDF-1.7\nform"

    monkeypatch.setattr(routes.pdf_service, "generate_pdf", fake_generate_pdf)

    response = client.post(
        "/generate",
        data={"html": "<h1>Form Mode</h1>", "css": "h1 { font-weight: 700; }", "filename": "form-doc"},
    )

    assert response.status_code == 200
    assert "form-doc.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_generate_pdf_from_multipart_template_payload(monkeypatch) -> None:
    async def fake_generate_pdf(html: str) -> bytes:
        assert "Multipart Corp" in html
        return b"%PDF-1.7\nmultipart"

    monkeypatch.setattr(routes.pdf_service, "generate_pdf", fake_generate_pdf)

    response = client.post(
        "/generate",
        files=[
            ("template_name", (None, "invoice.html")),
            ("data", (None, '{"customer_name":"Multipart Corp","invoice_number":"INV-202"}')),
        ],
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_generate_rejects_non_object_form_data_field() -> None:
    response = client.post("/generate", data={"template_name": "invoice.html", "data": '["bad"]'})
    assert response.status_code == 422
    assert "json object" in response.json()["detail"].lower()


def test_generate_requires_exactly_one_input_mode() -> None:
    response = client.post("/generate", json={"html": "<p>Hi</p>", "template_name": "invoice.html"})
    assert response.status_code == 422


def test_generate_template_not_found() -> None:
    response = client.post("/generate", json={"template_name": "missing.html"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
