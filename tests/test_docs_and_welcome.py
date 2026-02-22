from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_welcome_page_loads() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "PDF Generation API" in response.text
    assert "/swagger" in response.text


def test_swagger_page_loads() -> None:
    response = client.get("/swagger")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_openapi_schema_contains_generate_route() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    body = response.json()
    assert "/generate" in body["paths"]
    assert body["info"]["version"] == "1.0.0"
    generate_post = body["paths"]["/generate"]["post"]
    assert generate_post["security"]
    request_content = generate_post["requestBody"]["content"]
    assert list(request_content.keys()) == ["multipart/form-data"]
    schema_ref = request_content["multipart/form-data"]["schema"]["$ref"]
    schema_name = schema_ref.rsplit("/", maxsplit=1)[-1]
    properties = body["components"]["schemas"][schema_name]["properties"]
    assert "html_file" in properties
    assert "template_file" in properties
    html_type = properties["html_file"]["anyOf"][0]
    assert html_type["type"] == "string"
    assert html_type["contentMediaType"] == "application/octet-stream"
    security_schemes = body["components"]["securitySchemes"]
    assert any(
        scheme.get("type") == "apiKey" and scheme.get("name") == "X-API-Key"
        for scheme in security_schemes.values()
    )
