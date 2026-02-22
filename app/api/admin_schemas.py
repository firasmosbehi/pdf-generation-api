from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CreateAPIKeyRequest(BaseModel):
    account_name: str = Field(min_length=2, max_length=120)
    plan: Literal["free", "pro", "business"]
    monthly_quota: int | None = Field(default=None, ge=0)


class CreateAPIKeyResponse(BaseModel):
    account_name: str
    plan: str
    monthly_quota: int
    api_key: str


class UsageSummaryResponse(BaseModel):
    account_name: str
    plan: str
    monthly_quota: int
    month: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_pdf_bytes: int
