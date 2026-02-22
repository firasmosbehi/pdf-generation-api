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

## Deploy on Render

This repo includes a Blueprint at `render.yaml`.

1. Push your branch to GitHub.
2. In Render: `New +` -> `Blueprint`.
3. Select this repository and branch.
4. Fill secret env vars when prompted:
   - `PDF_API_ADMIN_TOKEN`
   - `PDF_API_KEY_SALT`
5. Create the Blueprint.

Notes:
- The Blueprint uses `plan: starter` to support a persistent disk for SQLite billing data.
- Billing DB path is set to `/var/data/pdf_api.sqlite3`.

## API Docs & Welcome Page

- Welcome page: `http://127.0.0.1:8000/`
- Swagger UI: `http://127.0.0.1:8000/swagger`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## Auth & Admin

- `POST /generate` requires header: `X-API-Key: <your_api_key>`
- Admin endpoints require header: `X-Admin-Token: <admin_token>`
- Local default admin token (override in production): `dev-admin-token`

Create an API key:

```bash
curl -X POST http://127.0.0.1:8000/admin/api-keys \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: dev-admin-token" \
  -d '{"account_name":"Acme Team","plan":"pro"}'
```

Get monthly usage summary:

```bash
curl "http://127.0.0.1:8000/admin/usage?api_key=YOUR_API_KEY&month=2026-02" \
  -H "X-Admin-Token: dev-admin-token"
```

## Generate from raw HTML

```bash
curl -X POST http://127.0.0.1:8000/generate \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "html_file=@./samples/html/operations_review_q4_2025.html;type=text/html" \
  -F "css_file=@./samples/css/operations_review_q4_2025.css;type=text/css" \
  -F "filename=hello" \
  --output hello.pdf
```

## Generate from template

```bash
curl -X POST http://127.0.0.1:8000/generate \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "template_file=@./samples/template/enterprise_invoice.html;type=text/html" \
  -F "data_file=@./samples/data/enterprise_invoice.json;type=application/json" \
  -F "css_file=@./samples/css/enterprise_invoice.css;type=text/css" \
  -F "filename=invoice" \
  --output invoice.pdf
```
