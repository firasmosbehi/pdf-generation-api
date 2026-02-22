from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GenerateRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "html": "<h1>Hello PDF</h1>",
                    "css": "h1 { color: #1d4ed8; }",
                    "filename": "hello.pdf",
                },
                {
                    "template": "invoice.html",
                    "data": {"customer_name": "Acme Corp", "invoice_number": "INV-100"},
                    "filename": "invoice-100.pdf",
                },
            ]
        },
    )

    html: str | None = Field(default=None, description="Raw HTML markup to render.")
    css: str | None = Field(default=None, description="Optional CSS appended to the HTML.")
    template: str | None = Field(
        default=None, description="Template filename from app/templates, for example invoice.html."
    )
    data: dict[str, Any] = Field(
        default_factory=dict, description="Template variables; used when template is provided."
    )
    filename: str | None = Field(
        default=None, description="Output filename used in Content-Disposition."
    )

    @model_validator(mode="before")
    @classmethod
    def map_legacy_template_name(cls, raw: Any) -> Any:
        if isinstance(raw, dict):
            raw = dict(raw)
            legacy_template = raw.pop("template_name", None)
            if "template" not in raw and legacy_template:
                raw["template"] = legacy_template
        return raw

    @model_validator(mode="after")
    def validate_render_source(self) -> "GenerateRequest":
        has_html = bool(self.html and self.html.strip())
        has_template = bool(self.template and self.template.strip())
        if has_html == has_template:
            raise ValueError("Provide exactly one of 'html' or 'template'.")
        return self
