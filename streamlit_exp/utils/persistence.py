from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

import streamlit as st

REQUIRED = ["spreadsheet_id", "worksheet_name"]


def _secrets_dict() -> Dict[str, Any]:
    if hasattr(st, "secrets"):
        try:
            return st.secrets.to_dict()
        except AttributeError:
            pass
    return {}


def get_cfg() -> Dict[str, Any]:
    """Return normalized persistence configuration with graceful fallbacks."""
    secrets = _secrets_dict()
    legacy = secrets.get("persistence", {}) or {}
    sheets = secrets.get("sheets", {}) or {}
    gcs = secrets.get("gcs", {}) or {}
    gsa = secrets.get("gcp_service_account", {}) or {}

    sheet_id = (
        legacy.get("spreadsheet_id")
        or sheets.get("spreadsheet_id")
        or sheets.get("sheet_id")
        or sheets.get("id")
        or sheets.get("key")
    )
    worksheet_name = (
        legacy.get("worksheet_name")
        or sheets.get("worksheet_name")
        or sheets.get("worksheet")
        or sheets.get("sheet_name")
        or "responses"
    )
    sheet_url = (
        legacy.get("spreadsheet_url")
        or legacy.get("url")
        or sheets.get("spreadsheet_url")
        or sheets.get("url")
    )

    cfg: Dict[str, Any] = {
        "spreadsheet_id": sheet_id,
        "spreadsheet_url": sheet_url,
        "worksheet_name": worksheet_name,
        "gcs_bucket": legacy.get("gcs_bucket") or gcs.get("bucket"),
        "service_account": gsa or legacy.get("service_account") or {},
    }

    missing = [key for key in REQUIRED if not cfg.get(key)]
    if missing:
        raise RuntimeError(
            "Missing secrets for Sheets. Provide in `st.secrets`:\n"
            "  [sheets]\n"
            '  spreadsheet_id="..."\n'
            '  worksheet_name="responses"'
        )
    return cfg


def now_utc_iso() -> str:
    """Return the current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()

