from __future__ import annotations

import os
import sys
from importlib import import_module
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

billing_store = import_module("app.services.billing_store")
create_api_key_for_account = billing_store.create_api_key_for_account
init_db = billing_store.init_db
reset_all_data = billing_store.reset_all_data

os.environ["PDF_API_DB_PATH"] = str(ROOT / "output" / "test_api.sqlite3")
os.environ["PDF_API_ADMIN_TOKEN"] = "test-admin-token"

init_db()


@pytest.fixture
def api_key() -> str:
    reset_all_data()
    init_db()
    return create_api_key_for_account(account_name="Test Account", plan="pro", monthly_quota=50)
