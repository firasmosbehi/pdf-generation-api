from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from pydantic import ValidationError

from app.api.schemas import GenerateRequest
from app.services.pdf_service import PDFGenerationError, PDFService, TemplateRenderError

router = APIRouter()
template_dir = Path(__file__).resolve().parents[1] / "templates"
pdf_service = PDFService(template_dir=template_dir)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _build_payload_from_form(
    *,
    html: str | None,
    css: str | None,
    template_name: str | None,
    data: str | None,
    filename: str | None,
) -> GenerateRequest:
    if data:
        try:
            parsed_data = json.loads(data)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=422, detail="Form field 'data' must contain valid JSON."
            ) from exc
        if not isinstance(parsed_data, dict):
            raise HTTPException(status_code=422, detail="Form field 'data' must be a JSON object.")
    else:
        parsed_data = {}

    try:
        return GenerateRequest.model_validate(
            {
                "html": html,
                "css": css,
                "template_name": template_name,
                "data": parsed_data,
                "filename": filename,
            }
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=jsonable_encoder(exc.errors())) from exc


@router.post("/generate")
async def generate_pdf(
    request: Request,
    html: str | None = Form(default=None),
    css: str | None = Form(default=None),
    template_name: str | None = Form(default=None),
    data: str | None = Form(default=None),
    filename: str | None = Form(default=None),
) -> Response:
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        try:
            raw_payload = await request.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Request body is not valid JSON.") from exc
        try:
            payload = GenerateRequest.model_validate(raw_payload)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=jsonable_encoder(exc.errors())) from exc
    else:
        payload = _build_payload_from_form(
            html=html,
            css=css,
            template_name=template_name,
            data=data,
            filename=filename,
        )

    try:
        rendered_html = pdf_service.build_html(
            html=payload.html,
            css=payload.css,
            template_name=payload.template_name,
            data=payload.data,
        )
        pdf_bytes = await pdf_service.generate_pdf(rendered_html)
    except TemplateRenderError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PDFGenerationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    filename = (payload.filename or "generated.pdf").strip()
    if not filename.endswith(".pdf"):
        filename = f"{filename}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
