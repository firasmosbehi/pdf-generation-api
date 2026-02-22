# PDF Generation API

FastAPI service that generates high-quality PDFs from:

- Raw HTML/CSS
- Jinja2 templates + JSON data

## Quickstart

```bash
poetry install
poetry run playwright install chromium
poetry run uvicorn app.main:app --reload
```

## Run with Docker Compose

```bash
docker compose up --build
```

## Generate from raw HTML

```bash
curl -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"html":"<h1>Hello</h1>","css":"h1 { color: #1d4ed8; }","filename":"hello"}' \
  --output hello.pdf
```

## Generate from template

```bash
curl -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"template_name":"invoice.html","data":{"customer_name":"Acme","invoice_number":"INV-1"}}' \
  --output invoice.pdf
```

## Generate from multipart/form-data

```bash
curl -X POST http://127.0.0.1:8000/generate \
  -F 'template_name=invoice.html' \
  -F 'data={"customer_name":"Acme","invoice_number":"INV-2"}' \
  -F 'filename=invoice-multipart' \
  --output invoice-multipart.pdf
```
