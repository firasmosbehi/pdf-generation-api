from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class GenerateRequest(BaseModel):
    html: str | None = None
    css: str | None = None
    template_name: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    filename: str | None = None

    @model_validator(mode="after")
    def validate_render_source(self) -> "GenerateRequest":
        has_html = bool(self.html and self.html.strip())
        has_template = bool(self.template_name and self.template_name.strip())
        if has_html == has_template:
            raise ValueError("Provide exactly one of 'html' or 'template_name'.")
        return self
