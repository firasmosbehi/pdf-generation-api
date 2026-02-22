from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PLAN_QUOTAS: dict[str, int] = {
    "free": 100,
    "pro": 2000,
    "business": 20000,
}


@dataclass(frozen=True)
class APIKeyRecord:
    api_key_id: int
    account_id: int
    account_name: str
    plan: str
    monthly_quota: int
    account_active: bool
    api_key_active: bool
    key_prefix: str


def _db_path() -> Path:
    raw_path = os.getenv("PDF_API_DB_PATH", "output/pdf_api.sqlite3")
    path = Path(raw_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_api_key(raw_api_key: str) -> str:
    salt = os.getenv("PDF_API_KEY_SALT", "change-me-in-production")
    return hashlib.sha256(f"{salt}:{raw_api_key}".encode("utf-8")).hexdigest()


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                plan TEXT NOT NULL,
                monthly_quota INTEGER NOT NULL CHECK (monthly_quota >= 0),
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                key_prefix TEXT NOT NULL,
                key_hash TEXT NOT NULL UNIQUE,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                revoked_at TEXT
            );

            CREATE TABLE IF NOT EXISTS usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key_id INTEGER NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
                account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                request_mode TEXT NOT NULL,
                success INTEGER NOT NULL,
                status_code INTEGER NOT NULL,
                pdf_bytes INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_usage_events_account_created
                ON usage_events(account_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_usage_events_api_key_created
                ON usage_events(api_key_id, created_at);
            """
        )


def _create_account(*, name: str, plan: str, monthly_quota: int) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO accounts(name, plan, monthly_quota, is_active, created_at)
            VALUES (?, ?, ?, 1, ?)
            """,
            (name, plan, monthly_quota, _utcnow_iso()),
        )
        return int(cur.lastrowid)


def create_api_key_for_account(
    *,
    account_name: str,
    plan: str,
    monthly_quota: int | None = None,
    raw_api_key: str | None = None,
) -> str:
    normalized_plan = plan.strip().lower()
    if normalized_plan not in DEFAULT_PLAN_QUOTAS:
        raise ValueError(f"Unsupported plan '{plan}'.")

    quota = monthly_quota if monthly_quota is not None else DEFAULT_PLAN_QUOTAS[normalized_plan]
    if quota < 0:
        raise ValueError("monthly_quota must be >= 0.")

    account_id = _create_account(
        name=account_name.strip(), plan=normalized_plan, monthly_quota=quota
    )
    generated_api_key = raw_api_key or secrets.token_urlsafe(32)
    key_hash = _hash_api_key(generated_api_key)
    key_prefix = generated_api_key[:10]

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO api_keys(account_id, key_prefix, key_hash, is_active, created_at, revoked_at)
            VALUES (?, ?, ?, 1, ?, NULL)
            """,
            (account_id, key_prefix, key_hash, _utcnow_iso()),
        )

    return generated_api_key


def lookup_api_key(raw_api_key: str) -> APIKeyRecord | None:
    key_hash = _hash_api_key(raw_api_key)
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT
                k.id AS api_key_id,
                a.id AS account_id,
                a.name AS account_name,
                a.plan AS plan,
                a.monthly_quota AS monthly_quota,
                a.is_active AS account_active,
                k.is_active AS api_key_active,
                k.key_prefix AS key_prefix
            FROM api_keys k
            JOIN accounts a ON a.id = k.account_id
            WHERE k.key_hash = ?
            """,
            (key_hash,),
        ).fetchone()

    if row is None:
        return None

    return APIKeyRecord(
        api_key_id=int(row["api_key_id"]),
        account_id=int(row["account_id"]),
        account_name=str(row["account_name"]),
        plan=str(row["plan"]),
        monthly_quota=int(row["monthly_quota"]),
        account_active=bool(row["account_active"]),
        api_key_active=bool(row["api_key_active"]),
        key_prefix=str(row["key_prefix"]),
    )


def count_successful_usage_for_month(*, account_id: int, month_start_utc: datetime) -> int:
    if month_start_utc.tzinfo is None:
        raise ValueError("month_start_utc must be timezone-aware.")
    if month_start_utc.month == 12:
        month_end_utc = month_start_utc.replace(year=month_start_utc.year + 1, month=1, day=1)
    else:
        month_end_utc = month_start_utc.replace(month=month_start_utc.month + 1, day=1)

    with _connect() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM usage_events
            WHERE account_id = ?
              AND success = 1
              AND created_at >= ?
              AND created_at < ?
            """,
            (
                account_id,
                month_start_utc.isoformat(),
                month_end_utc.isoformat(),
            ),
        ).fetchone()

    return int(row["cnt"]) if row else 0


def log_usage_event(
    *,
    api_key_id: int,
    account_id: int,
    request_mode: str,
    success: bool,
    status_code: int,
    pdf_bytes: int,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO usage_events(
                api_key_id, account_id, request_mode, success, status_code, pdf_bytes, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                api_key_id,
                account_id,
                request_mode,
                1 if success else 0,
                status_code,
                max(0, pdf_bytes),
                _utcnow_iso(),
            ),
        )


def get_usage_summary_for_month(*, account_id: int, month_start_utc: datetime) -> dict[str, int]:
    if month_start_utc.tzinfo is None:
        raise ValueError("month_start_utc must be timezone-aware.")
    if month_start_utc.month == 12:
        month_end_utc = month_start_utc.replace(year=month_start_utc.year + 1, month=1, day=1)
    else:
        month_end_utc = month_start_utc.replace(month=month_start_utc.month + 1, day=1)

    with _connect() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_requests,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) AS successful_requests,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) AS failed_requests,
                COALESCE(SUM(pdf_bytes), 0) AS total_pdf_bytes
            FROM usage_events
            WHERE account_id = ?
              AND created_at >= ?
              AND created_at < ?
            """,
            (
                account_id,
                month_start_utc.isoformat(),
                month_end_utc.isoformat(),
            ),
        ).fetchone()

    if row is None:
        return {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_pdf_bytes": 0,
        }

    return {
        "total_requests": int(row["total_requests"] or 0),
        "successful_requests": int(row["successful_requests"] or 0),
        "failed_requests": int(row["failed_requests"] or 0),
        "total_pdf_bytes": int(row["total_pdf_bytes"] or 0),
    }


def update_monthly_quota_for_api_key(*, raw_api_key: str, monthly_quota: int) -> None:
    if monthly_quota < 0:
        raise ValueError("monthly_quota must be >= 0.")

    key_hash = _hash_api_key(raw_api_key)
    with _connect() as conn:
        conn.execute(
            """
            UPDATE accounts
            SET monthly_quota = ?
            WHERE id IN (
                SELECT account_id
                FROM api_keys
                WHERE key_hash = ?
            )
            """,
            (monthly_quota, key_hash),
        )


def reset_all_data() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            DELETE FROM usage_events;
            DELETE FROM api_keys;
            DELETE FROM accounts;
            """
        )
