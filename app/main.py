from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="PDF Generation API",
    description="Generate high-quality PDFs from raw HTML/CSS or Jinja2 templates.",
    version="0.1.0",
)
app.include_router(router)
