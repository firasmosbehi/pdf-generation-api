from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.api.admin_schemas import CreateAPIKeyRequest, CreateAPIKeyResponse, UsageSummaryResponse
from app.api.security import AuthContext, require_admin_token, require_api_key
from app.services.billing_store import (
    DEFAULT_PLAN_QUOTAS,
    create_api_key_for_account,
    get_usage_summary_for_month,
    log_usage_event,
    lookup_api_key,
)
from app.services.pdf_service import PDFGenerationError, PDFService, TemplateRenderError

router = APIRouter()
template_dir = Path(__file__).resolve().parents[1] / "templates"
pdf_service = PDFService(template_dir=template_dir)


@router.get("/health", tags=["System"], summary="Health check")
async def health() -> dict[str, str]:
    return {"status": "ok"}


async def _read_text_upload(file: UploadFile, field_name: str) -> str:
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail=f"'{field_name}' must not be empty.")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"'{field_name}' must be UTF-8 text.") from exc


async def _read_json_object_upload(file: UploadFile) -> dict[str, Any]:
    raw_json = await _read_text_upload(file, "data_file")
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="'data_file' must contain valid JSON.") from exc

    if not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail="'data_file' must contain a JSON object.")
    return parsed


def _parse_month_start_utc(month: str | None) -> datetime:
    if month is None:
        now_utc = datetime.now(timezone.utc)
        return now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    try:
        parsed = datetime.strptime(month, "%Y-%m")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="month must be in YYYY-MM format.") from exc
    return parsed.replace(tzinfo=timezone.utc, day=1, hour=0, minute=0, second=0, microsecond=0)


@router.post(
    "/generate",
    tags=["PDF"],
    summary="Generate PDF",
    description=(
        "Generate a PDF from uploaded files. "
        "Upload exactly one of `html_file` or `template_file`."
    ),
    responses={
        200: {"description": "PDF generated successfully"},
        401: {"description": "Missing or invalid API key"},
        403: {"description": "Inactive API key"},
        429: {"description": "Monthly quota exceeded"},
        422: {"description": "Validation error"},
        500: {"description": "PDF generation failed"},
    },
)
async def generate_pdf(
    html_file: UploadFile | None = File(
        default=None, description="Raw HTML file (.html). Use this OR template_file."
    ),
    template_file: UploadFile | None = File(
        default=None, description="Jinja2 template file (.html). Use this OR html_file."
    ),
    css_file: UploadFile | None = File(default=None, description="Optional CSS file (.css)."),
    data_file: UploadFile | None = File(
        default=None, description="Optional JSON data file for template rendering."
    ),
    filename: str | None = Form(default=None, description="Output filename."),
    auth: AuthContext = Depends(require_api_key),
) -> Response:
    request_mode = (
        "html_file" if html_file is not None else "template_file" if template_file else "unknown"
    )
    status_code = 200
    pdf_bytes = b""
    success = False

    try:
        has_html_file = html_file is not None
        has_template_file = template_file is not None
        if has_html_file == has_template_file:
            status_code = 422
            raise HTTPException(
                status_code=422, detail="Provide exactly one of 'html_file' or 'template_file'."
            )

        if auth.successful_requests_this_month >= auth.record.monthly_quota:
            status_code = 429
            raise HTTPException(
                status_code=429,
                detail=(
                    "Monthly PDF quota exceeded. "
                    f"Plan quota={auth.record.monthly_quota}, used={auth.successful_requests_this_month}."
                ),
            )

        css_text = await _read_text_upload(css_file, "css_file") if css_file is not None else None
        if html_file is not None:
            html_text = await _read_text_upload(html_file, "html_file")
            rendered_html = pdf_service.build_html(
                html=html_text,
                css=css_text,
                template_name=None,
                data=None,
            )
        else:
            template_text = await _read_text_upload(template_file, "template_file")
            data = await _read_json_object_upload(data_file) if data_file is not None else {}
            rendered_html = pdf_service.render_template_content(
                template_content=template_text,
                css=css_text,
                data=data,
            )

        pdf_bytes = await pdf_service.generate_pdf(rendered_html)
        success = True
        status_code = 200
    except TemplateRenderError as exc:
        status_code = 422
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PDFGenerationError as exc:
        status_code = 500
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except HTTPException as exc:
        status_code = exc.status_code
        raise
    finally:
        log_usage_event(
            api_key_id=auth.record.api_key_id,
            account_id=auth.record.account_id,
            request_mode=request_mode,
            success=success,
            status_code=status_code,
            pdf_bytes=len(pdf_bytes),
        )

    output_filename = (filename or "generated.pdf").strip()
    if not output_filename.endswith(".pdf"):
        output_filename = f"{output_filename}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{output_filename}"'},
    )


@router.post(
    "/admin/api-keys",
    tags=["Admin"],
    summary="Create API key",
    description="Create an account API key and return the raw key once.",
    response_model=CreateAPIKeyResponse,
    responses={401: {"description": "Invalid admin token"}},
)
async def create_api_key(
    payload: CreateAPIKeyRequest, _: str = Depends(require_admin_token)
) -> CreateAPIKeyResponse:
    raw_api_key = create_api_key_for_account(
        account_name=payload.account_name,
        plan=payload.plan,
        monthly_quota=payload.monthly_quota,
    )
    resolved_quota = (
        payload.monthly_quota
        if payload.monthly_quota is not None
        else DEFAULT_PLAN_QUOTAS[payload.plan]
    )
    return CreateAPIKeyResponse(
        account_name=payload.account_name,
        plan=payload.plan,
        monthly_quota=resolved_quota,
        api_key=raw_api_key,
    )


@router.get(
    "/admin/usage",
    tags=["Admin"],
    summary="Get usage summary",
    description="Returns monthly usage and quota utilization for a provided API key.",
    response_model=UsageSummaryResponse,
    responses={
        401: {"description": "Invalid admin token"},
        404: {"description": "API key not found"},
    },
)
async def get_usage_summary(
    api_key: str = Query(..., min_length=10, description="Raw API key to inspect."),
    month: str | None = Query(
        default=None, description="Month in YYYY-MM format. Defaults to current UTC month."
    ),
    _: str = Depends(require_admin_token),
) -> UsageSummaryResponse:
    record = lookup_api_key(api_key)
    if record is None:
        raise HTTPException(status_code=404, detail="API key not found.")

    month_start_utc = _parse_month_start_utc(month)
    summary = get_usage_summary_for_month(
        account_id=record.account_id, month_start_utc=month_start_utc
    )

    return UsageSummaryResponse(
        account_name=record.account_name,
        plan=record.plan,
        monthly_quota=record.monthly_quota,
        month=month_start_utc.strftime("%Y-%m"),
        total_requests=summary["total_requests"],
        successful_requests=summary["successful_requests"],
        failed_requests=summary["failed_requests"],
        total_pdf_bytes=summary["total_pdf_bytes"],
    )
