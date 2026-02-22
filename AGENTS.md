# Repository Guidelines

## Agent Context
Build a high-performance REST API that converts HTML/CSS to high-quality PDFs.

- Runtime: Python 3.10+
- Package manager: Poetry
- API framework: FastAPI + Uvicorn
- PDF engine: Playwright (primary), WeasyPrint (optional fallback)
- Templates: Jinja2

## Project Structure & Module Organization
Use a Python-first layout:

- `app/main.py`: FastAPI app entrypoint.
- `app/api/routes.py`: HTTP endpoints (including `POST /generate`).
- `app/services/pdf_service.py`: HTML render + PDF generation logic.
- `app/templates/`: Jinja2 templates.
- `tests/`: pytest tests mirroring `app/`.
- `output/`: local generated PDFs for development checks (gitignored).

## Build, Test, and Development Commands
Initialize and run with Poetry:

- `poetry init`
- `poetry add fastapi uvicorn playwright jinja2 python-multipart`
- `poetry add --group dev pytest httpx ruff black`
- `poetry run playwright install chromium`
- `poetry run uvicorn app.main:app --reload`
- `poetry run pytest`

## API Contract: `/generate`
Implement `POST /generate` to support:

- Raw HTML/CSS input (`html`, optional `css`).
- Template rendering (`template_name`, `data` JSON payload for Jinja2).

Return `application/pdf` bytes and set `Content-Disposition` when filename is provided.

## Coding Style & Naming Conventions
- 4-space indentation, type hints on public functions, and small focused modules.
- File/function names: `snake_case`; classes: `PascalCase`; constants: `UPPER_SNAKE_CASE`.
- Run `poetry run ruff check .` and `poetry run black .` before commits.

## Testing Guidelines
- Use `pytest`; name files `test_*.py`.
- Cover success and failure paths for `/generate` (invalid payload, template missing, engine failure).
- Validate generated PDF headers (`%PDF`) and non-empty output.

## Recommended Skills
Use these skills when relevant:

- `pdf`: PDF rendering/extraction validation and layout checks.
- `playwright`: browser-driven HTML-to-PDF debugging and automation.
- `security-best-practices`: security review for Python/FastAPI codepaths.

## Recommended MCP Servers
- `filesystem`: save, inspect, and verify generated PDF files locally.
- `api2pdf`: reference robust API-to-PDF architecture patterns and operational practices.

## Commit & PR Guidelines
Use Conventional Commits (`feat:`, `fix:`, `chore:`). PRs must include a concise summary, test evidence (`poetry run pytest`), and at least one sample output note (path in `output/` or screenshot when relevant).
