from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.routes import router
from app.services.billing_store import init_db

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="PDF Generation API",
    description=(
        "Generate high-quality PDFs from raw HTML/CSS or Jinja2 templates using "
        "Playwright Chromium."
    ),
    version="1.0.0",
    docs_url="/swagger",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "PDF Generation API Support",
        "url": "https://github.com/firasmosbehi/pdf-generation-api",
    },
    license_info={"name": "MIT"},
    lifespan=lifespan,
)
app.include_router(router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def welcome(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "welcome.html", {})
