# [CHANGE] ASCII-safe persistence helpers for Google Sheets and GCS.
from __future__ import annotations

import csv
import json
import os
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import streamlit as st

from constants import MANIPULATION_CHECK_ITEMS
from utils.google_sheet import get_google_sheet

TASK_EXPORT_COUNT = 10
ANTH_COUNT = 30
ACHIVE_COUNT = 26
MOTIVATION_COUNT = 26

SANITIZE_MAP: Dict[str, str] = {
    "동의함": "agree",
    "동의하지 않음": "disagree",
    "남자": "male",
    "여자": "female",
    "고등학교 졸업 이하": "high_school_or_lower",
    "대학(재학/졸업)": "college",
    "대학원(재학/졸업)": "graduate",
    "기타": "other",
    "선택해 주세요": "",
}

COLS: List[str] = [
    "participant_id",
    "consent_research",
    "consent_privacy",
    "sex_biological",
    "age_years",
    "education_level",
    "condition",
    "specificity",
    "phase_order",
    "started_at",
    "finished_at",
    "task_duration_sec",
    "task_score_total",
    "task_accuracy_pct",
    *[f"task_ans_{idx:02d}" for idx in range(1, TASK_EXPORT_COUNT + 1)],
    *[f"anth_{idx:02d}" for idx in range(1, ANTH_COUNT + 1)],
    *[f"ach_{idx:02d}" for idx in range(1, ACHIVE_COUNT + 1)],
    *[f"lm_{idx:02d}" for idx in range(1, MOTIVATION_COUNT + 1)],
    *[item.id for item in MANIPULATION_CHECK_ITEMS],
    "difficulty_after_round1",
    "difficulty_final",
    "open_feedback",
    "phone",
    "praise_condition",
]


def google_ready() -> bool:
    """Return True when remote Google Sheet credentials are available."""
    try:
        has_secrets = bool(getattr(st.secrets, "google_sheet", {}) or {})
    except Exception:
        has_secrets = False
    has_env = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"))
    return has_secrets or has_env


def normalize_for_storage(value: Any) -> Any:
    """Coerce survey values into ASCII-safe primitives for persistence."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return ""
        mapped = SANITIZE_MAP.get(trimmed, trimmed)
        cleaned = mapped.replace(",", "; ").replace("\n", " ").replace("\r", " ").replace("\t", " ")
        cleaned = " ".join(cleaned.split())
        try:
            cleaned.encode("ascii")
            return cleaned
        except UnicodeEncodeError:
            translit = (
                unicodedata.normalize("NFKD", cleaned)
                .encode("ascii", "ignore")
                .decode("ascii")
            )
            if translit:
                return translit
            return cleaned.encode("unicode_escape").decode("ascii")
    return str(value)


def _expand(values: Iterable[Any], total: int) -> List[Any]:
    seq = list(values) if isinstance(values, list) else list(values or [])
    buffer: List[Any] = []
    for idx in range(total):
        raw = seq[idx] if idx < len(seq) else ""
        buffer.append(normalize_for_storage("" if raw is None else raw))
    return buffer


def _task_specificity(condition: str) -> str:
    cond = condition or ""
    if "specific" in cond:
        return "specific"
    if "surface" in cond:
        return "surface"
    return "unknown"


def _safe_phone(phone: str) -> str:
    stripped = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    return normalize_for_storage(stripped)


def build_storage_record(payload: Dict[str, Any], record: Any) -> Dict[str, Any]:
    """Prepare a normalized dict ready for Sheet row + JSON export."""
    consent = payload.get("consent", {}) or {}
    demographic = payload.get("demographic", {}) or {}
    anthro = payload.get("anthro_responses", []) or []
    achive = payload.get("achive_responses", []) or []
    motivation = payload.get("motivation_responses", []) or []
    manipulation = payload.get("manipulation_check", {}) or {}
    inference_details = payload.get("inference_details", []) or []

    start_iso = payload.get("start_time") or (record.timestamps.get("start") if getattr(record, "timestamps", None) else None)
    end_iso = payload.get("end_time") or (record.timestamps.get("end") if getattr(record, "timestamps", None) else None)

    condition = payload.get("praise_condition") or payload.get("feedback_condition") or getattr(record, "condition", "")
    condition = normalize_for_storage(condition)
    specificity = _task_specificity(str(condition))
    phase_order = "nouns_then_verbs"

    task_answers: List[Any] = []
    for detail in inference_details[:TASK_EXPORT_COUNT]:
        selected = detail.get("selected_option")
        if isinstance(selected, int):
            task_answers.append(normalize_for_storage(selected + 1))
        else:
            task_answers.append("")
    while len(task_answers) < TASK_EXPORT_COUNT:
        task_answers.append("")

    total_questions = len(inference_details) if inference_details else 0
    score = sum(
        1
        for detail in inference_details
        if detail.get("selected_option") == detail.get("correct_idx")
    )
    duration = sum(float(detail.get("response_time") or 0.0) for detail in inference_details)
    accuracy = round(score / total_questions, 3) if total_questions else ""

    manip_values = [
        normalize_for_storage(manipulation.get(item.id, ""))
        for item in MANIPULATION_CHECK_ITEMS
    ]

    storage: Dict[str, Any] = {
        "participant_id": normalize_for_storage(
            payload.get("participant_id") or getattr(record, "participant_id", "")
        ),
        "consent_research": normalize_for_storage(consent.get("consent_research")),
        "consent_privacy": normalize_for_storage(consent.get("consent_privacy")),
        "sex_biological": normalize_for_storage(demographic.get("sex_biological")),
        "age_years": normalize_for_storage(demographic.get("age_years")),
        "education_level": normalize_for_storage(demographic.get("education_level")),
        "condition": condition,
        "specificity": normalize_for_storage(specificity),
        "phase_order": normalize_for_storage(phase_order),
        "started_at": normalize_for_storage(start_iso),
        "finished_at": normalize_for_storage(end_iso or datetime.utcnow().isoformat()),
        "task_duration_sec": round(duration, 2) if duration else "",
        "task_score_total": score if total_questions else "",
        "task_accuracy_pct": accuracy,
    }

    storage.update(
        {f"task_ans_{idx:02d}": value for idx, value in enumerate(task_answers, start=1)}
    )
    storage.update(
        {
            f"anth_{idx:02d}": value
            for idx, value in enumerate(_expand(anthro, ANTH_COUNT), start=1)
        }
    )
    storage.update(
        {
            f"ach_{idx:02d}": value
            for idx, value in enumerate(_expand(achive, ACHIVE_COUNT), start=1)
        }
    )
    storage.update(
        {
            f"lm_{idx:02d}": value
            for idx, value in enumerate(_expand(motivation, MOTIVATION_COUNT), start=1)
        }
    )
    storage.update({item.id: manip_values[idx] for idx, item in enumerate(MANIPULATION_CHECK_ITEMS)})

    storage["difficulty_after_round1"] = normalize_for_storage(
        payload.get("difficulty_checks", {}).get("after_round1")
    )
    storage["difficulty_final"] = normalize_for_storage(
        payload.get("difficulty_checks", {}).get("final")
    )
    storage["open_feedback"] = normalize_for_storage(payload.get("open_feedback", ""))
    storage["phone"] = _safe_phone(payload.get("phone", ""))
    storage["praise_condition"] = normalize_for_storage(
        payload.get("praise_condition") or getattr(record, "condition", "")
    )

    return storage


def build_sheet_row(storage_record: Dict[str, Any]) -> List[Any]:
    """Return list aligned with COLS for Google Sheets append operations."""
    return [storage_record.get(column, "") for column in COLS]


def save_to_sheets(row: List[Any], worksheet: str = "resp") -> str:
    """Append the given row to Google Sheets with a stable header."""
    if not google_ready():
        raise RuntimeError("Google Sheets credentials not configured.")

    import gspread
    from gspread.utils import rowcol_to_a1

    sheet = get_google_sheet()
    try:
        ws = sheet.worksheet(worksheet)
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title=worksheet, rows=2, cols=len(COLS))
    ws.resize(rows=max(ws.row_count, 2), cols=max(ws.col_count, len(COLS)))

    header_range = f"A1:{rowcol_to_a1(1, len(COLS))}"
    if ws.row_values(1) != COLS:
        ws.update(header_range, [COLS])

    ws.append_rows(
        [row],
        value_input_option="RAW",
        insert_data_option="INSERT_ROWS",
    )
    return f"sheet://{worksheet}"


def write_local_csv(row: List[Any], path: Path = Path("/tmp/ai_praise_resp.csv")) -> str:
    """Persist the row to a local CSV fallback (for DRY_RUN/local dev)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as file_obj:
        writer = csv.writer(file_obj)
        if not file_exists or path.stat().st_size == 0:
            writer.writerow(COLS)
        writer.writerow(row)
    return f"LOCAL::{path}"


def _storage_client():
    try:
        from google.cloud import storage
    except ImportError as exc:
        raise RuntimeError("google-cloud-storage not installed") from exc

    credentials_info = None
    try:
        credentials_info = dict(st.secrets["gcp_service_account"])
    except Exception:
        credentials_info = None

    env_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if env_json:
        credentials_info = json.loads(env_json)

    if credentials_info:
        from google.oauth2.service_account import Credentials

        private_key = credentials_info.get("private_key")
        if isinstance(private_key, str) and "\\n" in private_key:
            credentials_info["private_key"] = private_key.replace("\\n", "\n")
        credentials = Credentials.from_service_account_info(credentials_info)
        return storage.Client(credentials=credentials, project=credentials.project_id)

    return storage.Client()


def save_to_gcs(storage_record: Dict[str, Any]) -> Tuple[bool, str]:
    """Upload normalized record JSON to GCS if configured."""
    bucket_name = os.getenv("GCS_BUCKET")
    if not bucket_name:
        return False, "GCS_BUCKET not configured"

    try:
        client = _storage_client()
    except Exception as exc:  # pragma: no cover - runtime dependent
        return False, f"GCS client unavailable: {exc}"

    participant_id = storage_record.get("participant_id") or "unknown"
    finished_at = storage_record.get("finished_at") or datetime.utcnow().isoformat()
    safe_timestamp = finished_at.replace(":", "-")
    blob_name = f"participants/{participant_id}_{safe_timestamp}.json"
    try:
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(
            json.dumps(storage_record, ensure_ascii=True),
            content_type="application/json",
        )
    except Exception as exc:  # pragma: no cover - runtime dependent
        return False, f"GCS upload failed: {exc}"
    return True, f"gs://{bucket_name}/{blob_name}"
