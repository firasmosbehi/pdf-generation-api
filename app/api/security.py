from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.services.billing_store import (
    APIKeyRecord,
    count_successful_usage_for_month,
    lookup_api_key,
)

api_key_header = APIKeyHeader(name="X-API-Key", scheme_name="ApiKeyAuth", auto_error=False)
admin_token_header = APIKeyHeader(
    name="X-Admin-Token", scheme_name="AdminTokenAuth", auto_error=False
)


@dataclass(frozen=True)
class AuthContext:
    record: APIKeyRecord
    successful_requests_this_month: int
    month_start_utc: datetime


def require_api_key(api_key: str | None = Security(api_key_header)) -> AuthContext:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Pass it in the X-API-Key header.",
        )

    record = lookup_api_key(api_key)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    if not record.account_active or not record.api_key_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key is inactive.",
        )

    now_utc = datetime.now(timezone.utc)
    month_start_utc = now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = count_successful_usage_for_month(
        account_id=record.account_id, month_start_utc=month_start_utc
    )
    return AuthContext(
        record=record, successful_requests_this_month=used, month_start_utc=month_start_utc
    )


def require_admin_token(admin_token: str | None = Security(admin_token_header)) -> str:
    expected = os.getenv("PDF_API_ADMIN_TOKEN", "dev-admin-token")
    if not admin_token or admin_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token.",
        )
    return admin_token
