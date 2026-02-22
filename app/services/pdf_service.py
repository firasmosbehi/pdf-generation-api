from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright


class TemplateRenderError(Exception):
    """Raised when template rendering fails."""


class PDFGenerationError(Exception):
    """Raised when the HTML-to-PDF conversion fails."""


class PDFService:
    def __init__(self, template_dir: Path) -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def build_html(
        self,
        *,
        html: str | None,
        css: str | None,
        template_name: str | None,
        data: dict[str, Any] | None,
    ) -> str:
        if html:
            return self._inject_css(html=html, css=css)
        if not template_name:
            raise TemplateRenderError("Missing render source.")
        try:
            template = self.env.get_template(template_name)
        except TemplateNotFound as exc:
            raise TemplateRenderError(f"Template '{template_name}' was not found.") from exc
        return template.render(**(data or {}), css=css)

    async def generate_pdf(self, html: str) -> bytes:
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    args=["--disable-dev-shm-usage", "--no-sandbox"]
                )
                page = await browser.new_page()
                await page.set_content(html, wait_until="networkidle")
                pdf_bytes = await page.pdf(format="A4", print_background=True)
                await browser.close()
                return pdf_bytes
        except PlaywrightError as exc:
            raise PDFGenerationError("Failed to generate PDF with Playwright.") from exc

    @staticmethod
    def _inject_css(*, html: str, css: str | None) -> str:
        if not css:
            return html
        style_tag = f"<style>{css}</style>"
        head_close_index = html.lower().find("</head>")
        if head_close_index != -1:
            return f"{html[:head_close_index]}{style_tag}{html[head_close_index:]}"
        html_match = re.search(r"<html[^>]*>", html, flags=re.IGNORECASE)
        if html_match:
            insert_at = html_match.end()
            return f"{html[:insert_at]}<head>{style_tag}</head>{html[insert_at:]}"
        return f"<html><head>{style_tag}</head><body>{html}</body></html>"
