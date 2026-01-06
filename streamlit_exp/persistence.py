# [CHANGE] ASCII-safe persistence helpers for Google Sheets and GCS.
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional, Tuple

from constants import MANIPULATION_CHECK_ITEMS
from utils.google_sheet import append_row_to_sheet
from utils.persistence import get_cfg, now_utc_iso

SCHEMA_VERSION = "2025-11-13.v1"

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

SHEET_COLUMNS: List[str] = [
    "saved_at",
    "start_timestamp",
    "end_timestamp",
    "participant_id",
    "condition",
    "condition_specificity",
    "phase_order",
    "completion_time_sec",
    "task_duration_seconds",
    "total_inference_questions",
    "inference_correct_count",
    "inference_accuracy_pct",
    "anthro_count",
    "achive_count",
    "motivation_count",
    "difficulty_checks_count",
    "contact_provided",
    "phone_number",
    "phone_number_raw",
    "praise_condition",
    "feedback_condition",
    "sex_biological",
    "age_years",
    "education_level",
    "consent_json",
    "consent_flags_json",
    "demographic_json",
    "anthro_responses_json",
    "achive_responses_json",
    "motivation_responses_json",
    "motivation_scores_json",
    "difficulty_checks_json",
    "manipulation_check_json",
    "inference_summary_json",
    "inference_details_json",
    "inference_responses_json",
    "feedback_messages_json",
    "open_feedback_text",
    "meta_full_json",
    "payload_full_json",
    "experiment_record_full_json",
    "schema_version",
]

JSON_COLUMNS = {
    "consent_json",
    "consent_flags_json",
    "demographic_json",
    "anthro_responses_json",
    "achive_responses_json",
    "motivation_responses_json",
    "motivation_scores_json",
    "difficulty_checks_json",
    "manipulation_check_json",
    "inference_summary_json",
    "inference_details_json",
    "inference_responses_json",
    "feedback_messages_json",
    "meta_full_json",
    "payload_full_json",
    "experiment_record_full_json",
}

AFFIRMATIVE_VALUES = {"agree", "yes", "y", "true", "1"}


def google_ready() -> bool:
    """Return True when remote Google Sheet credentials are available."""
    try:
        config = get_cfg()
    except RuntimeError:
        config = {}
    sheet_identifier = (
        config.get("spreadsheet_id")
        or config.get("spreadsheet_url")
        or os.getenv("GOOGLE_SHEET_ID")
        or os.getenv("GOOGLE_SHEET_URL")
    )
    if not sheet_identifier:
        return False

    service_account = config.get("service_account") or {}
    has_secret_credentials = bool(service_account)
    env_credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    env_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    return bool(has_secret_credentials or env_credentials_json or env_credentials_path)


def _ensure_jsonable(data: Any) -> Any:
    """
    Ensure the provided data structure can be serialized to JSON.
    Non-serializable values are converted to strings while preserving the structure.
    """
    try:
        json.dumps(data, ensure_ascii=False)
        return data
    except (TypeError, ValueError):
        return json.loads(json.dumps(data, ensure_ascii=False, default=str))


def _json_or_blank(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return json.dumps(_ensure_jsonable(value), ensure_ascii=False)


def _is_affirmative(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    text = str(value).strip()
    normalized = SANITIZE_MAP.get(text, text)
    return normalized.lower() in AFFIRMATIVE_VALUES


def _format_float(value: Any, precision: int = 3) -> Any:
    if value in (None, "", [], {}):
        return ""
    try:
        return round(float(value), precision)
    except (TypeError, ValueError):
        return value


def _format_int(value: Any) -> Any:
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _task_specificity(condition: str) -> str:
    cond = condition or ""
    if "specific" in cond:
        return "specific"
    if "superficial" in cond or "surface" in cond:
        return "surface"
    return "unknown"


def _safe_phone(phone: str) -> str:
    return "".join(ch for ch in (phone or "") if ch.isdigit() or ch == "+")


def _experiment_record_to_dict(record: Any) -> Dict[str, Any]:
    if record is None:
        return {}
    if is_dataclass(record):
        try:
            return asdict(record)
        except TypeError:
            pass
    if isinstance(record, dict):
        return dict(record)
    if hasattr(record, "__dict__"):
        return {
            key: value
            for key, value in vars(record).items()
            if not key.startswith("_")
        }
    return {"value": record}


def build_storage_record(payload: Dict[str, Any], record: Any) -> Dict[str, Any]:
    """Build a JSON-serializable record that captures all participant responses."""
    payload = dict(payload or {})

    consent = dict(payload.get("consent", {}) or {})
    demographic = dict(payload.get("demographic", {}) or {})
    anthro_responses = list(payload.get("anthro_responses", []) or [])
    achive_responses = list(payload.get("achive_responses", []) or [])
    motivation_responses = list(payload.get("motivation_responses", []) or [])
    motivation_scores = dict(payload.get("motivation_category_scores", {}) or {})
    difficulty_checks = dict(payload.get("difficulty_checks", {}) or {})
    manipulation_check = dict(payload.get("manipulation_check", {}) or {})
    inference_details = list(payload.get("inference_details", []) or [])
    feedback_messages = dict(payload.get("feedback_messages", {}) or {})
    open_feedback = (payload.get("open_feedback") or "").strip()
    phone_raw = payload.get("phone") or ""

    record_timestamps = getattr(record, "timestamps", {}) if record else {}
    start_iso = payload.get("start_time") or record_timestamps.get("start")
    end_iso = payload.get("end_time") or record_timestamps.get("end")
    saved_at = now_utc_iso()

    condition_value = (
        payload.get("praise_condition")
        or payload.get("feedback_condition")
        or getattr(record, "condition", "")
        or ""
    )
    specificity = _task_specificity(str(condition_value))
    phase_order = payload.get("phase_order") or "nouns_then_verbs"

    total_questions = len(inference_details)
    correct_count = 0
    total_response_time = 0.0
    per_round: Dict[str, Dict[str, Any]] = {}
    for detail in inference_details:
        round_key = str(detail.get("round") or "unknown")
        summary = per_round.setdefault(
            round_key,
            {"round": round_key, "questions": 0, "correct": 0, "total_time": 0.0},
        )
        summary["questions"] += 1
        if detail.get("selected_option") == detail.get("correct_idx"):
            correct_count += 1
            summary["correct"] += 1
        try:
            response_time = float(detail.get("response_time") or 0.0)
        except (TypeError, ValueError):
            response_time = 0.0
        summary["total_time"] += response_time
        total_response_time += response_time

    for summary in per_round.values():
        questions = summary["questions"]
        if questions:
            summary["accuracy_pct"] = round(summary["correct"] / questions, 4)
            summary["avg_response_time"] = round(summary["total_time"] / questions, 3)
        else:
            summary["accuracy_pct"] = None
            summary["avg_response_time"] = None

    per_round_summary = sorted(
        per_round.values(),
        key=lambda entry: entry.get("round", ""),
    )

    accuracy_pct = round(correct_count / total_questions, 4) if total_questions else None
    completion_seconds = getattr(record, "completion_time", None)
    if completion_seconds is None and total_response_time:
        completion_seconds = round(total_response_time, 3)

    payload_snapshot = _ensure_jsonable(payload)
    experiment_record = _ensure_jsonable(_experiment_record_to_dict(record))

    consent_flags = {
        "research": _is_affirmative(consent.get("consent_research")),
        "privacy": _is_affirmative(consent.get("consent_privacy")),
    }

    manipulation_complete = dict(manipulation_check)
    for item in MANIPULATION_CHECK_ITEMS:
        manipulation_complete.setdefault(item.id, manipulation_check.get(item.id))

    meta: Dict[str, Any] = {
        "saved_at": saved_at,
        "participant_id": payload.get("participant_id")
        or getattr(record, "participant_id", "")
        or "",
        "condition": condition_value,
        "condition_specificity": specificity,
        "phase_order": phase_order,
        "start_time": start_iso,
        "end_time": end_iso or saved_at,
        "completion_seconds": completion_seconds,
        "task_duration_seconds": round(total_response_time, 3)
        if total_response_time
        else None,
        "total_inference_questions": total_questions,
        "inference_correct_count": correct_count,
        "inference_accuracy_pct": accuracy_pct,
        "anthro_count": len([v for v in anthro_responses if v is not None]),
        "achive_count": len([v for v in achive_responses if v is not None]),
        "motivation_count": len([v for v in motivation_responses if v is not None]),
        "difficulty_checks_count": len(difficulty_checks),
        "phone_number": _safe_phone(phone_raw),
        "phone_number_raw": phone_raw,
        "contact_provided": bool(_safe_phone(phone_raw)),
        "praise_condition": payload.get("praise_condition")
        or getattr(record, "condition", "")
        or "",
        "feedback_condition": payload.get("feedback_condition")
        or getattr(record, "condition", "")
        or "",
        "consent_flags": consent_flags,
        "manipulation_check_full": manipulation_complete,
        "inference_summary": {
            "total_questions": total_questions,
            "correct_count": correct_count,
            "accuracy_pct": accuracy_pct,
            "total_response_time": round(total_response_time, 3)
            if total_response_time
            else 0.0,
            "per_round": per_round_summary,
            "average_response_time": (
                round(total_response_time / total_questions, 3)
                if total_questions
                else None
            ),
        },
        "timestamps": record_timestamps,
    }

    storage_record: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "meta": _ensure_jsonable(meta),
        "payload": payload_snapshot,
        "experiment_record": experiment_record,
    }

    return storage_record


def build_sheet_row(storage_record: Dict[str, Any]) -> List[Any]:
    """Convert the storage record into a stable Google Sheets row."""
    if not isinstance(storage_record, dict):
        raise ValueError("storage_record must be a dict.")

    schema_version = storage_record.get("schema_version") or SCHEMA_VERSION
    meta_raw = storage_record.get("meta") or {}
    meta = dict(meta_raw) if isinstance(meta_raw, dict) else {}

    payload_raw = storage_record.get("payload") or storage_record.get("payload_snapshot") or {}
    payload_data = dict(payload_raw) if isinstance(payload_raw, dict) else {}

    experiment_raw = storage_record.get("experiment_record") or {}
    experiment_data = dict(experiment_raw) if isinstance(experiment_raw, dict) else {}

    saved_at = meta.get("saved_at") or storage_record.get("saved_at") or now_utc_iso()
    meta.setdefault("saved_at", saved_at)

    end_timestamp = (
        meta.get("end_time")
        or payload_data.get("end_time")
        or storage_record.get("end_time")
        or saved_at
    )

    participant_id = (
        meta.get("participant_id")
        or payload_data.get("participant_id")
        or experiment_data.get("participant_id")
        or ""
    )

    condition = meta.get("condition") or payload_data.get("feedback_condition") or ""
    specificity = meta.get("condition_specificity") or _task_specificity(str(condition))
    phase_order = meta.get("phase_order") or payload_data.get("phase_order") or ""

    anthro_responses = payload_data.get("anthro_responses") or []
    achive_responses = payload_data.get("achive_responses") or []
    motivation_responses = payload_data.get("motivation_responses") or []
    difficulty_checks = payload_data.get("difficulty_checks") or {}

    consent_flags = meta.get("consent_flags") or storage_record.get("consent_flags") or {}
    manipulation_full = (
        meta.get("manipulation_check_full")
        or payload_data.get("manipulation_check")
        or {}
    )

    inference_summary = meta.get("inference_summary") or storage_record.get("inference_summary") or {}
    inference_details = payload_data.get("inference_details") or storage_record.get("inference_details") or []
    inference_responses = (
        experiment_data.get("inference_responses")
        or storage_record.get("inference_responses")
        or []
    )
    feedback_messages = payload_data.get("feedback_messages") or storage_record.get("feedback_messages") or {}
    open_feedback = payload_data.get("open_feedback") or storage_record.get("open_feedback") or ""

    phone_number = meta.get("phone_number") or storage_record.get("phone_number") or _safe_phone(
        payload_data.get("phone") or ""
    )
    phone_number_raw = meta.get("phone_number_raw") or storage_record.get("phone_number_raw") or payload_data.get(
        "phone"
    )
    contact_provided = meta.get("contact_provided")
    if contact_provided is None:
        contact_provided = bool(phone_number)

    def _count_with_fallback(meta_value: Any, responses: Any) -> Any:
        if meta_value not in (None, ""):
            return meta_value
        if isinstance(responses, list):
            return len([val for val in responses if val is not None])
        if isinstance(responses, dict):
            return len(responses)
        return ""

    row_map: Dict[str, Any] = {
        "saved_at": saved_at,
        "start_timestamp": meta.get("start_time") or payload_data.get("start_time") or "",
        "end_timestamp": end_timestamp,
        "participant_id": participant_id,
        "condition": condition,
        "condition_specificity": specificity,
        "phase_order": phase_order,
        "completion_time_sec": _format_float(meta.get("completion_seconds")),
        "task_duration_seconds": _format_float(meta.get("task_duration_seconds")),
        "total_inference_questions": _format_int(meta.get("total_inference_questions")),
        "inference_correct_count": _format_int(meta.get("inference_correct_count")),
        "inference_accuracy_pct": _format_float(meta.get("inference_accuracy_pct"), precision=4),
        "anthro_count": _format_int(_count_with_fallback(meta.get("anthro_count"), anthro_responses)),
        "achive_count": _format_int(_count_with_fallback(meta.get("achive_count"), achive_responses)),
        "motivation_count": _format_int(_count_with_fallback(meta.get("motivation_count"), motivation_responses)),
        "difficulty_checks_count": _format_int(
            _count_with_fallback(meta.get("difficulty_checks_count"), difficulty_checks)
        ),
        "contact_provided": contact_provided,
        "phone_number": phone_number or "",
        "phone_number_raw": phone_number_raw or "",
        "praise_condition": meta.get("praise_condition") or payload_data.get("praise_condition") or "",
        "feedback_condition": meta.get("feedback_condition") or payload_data.get("feedback_condition") or "",
        "sex_biological": (payload_data.get("demographic") or {}).get("sex_biological", ""),
        "age_years": _format_int((payload_data.get("demographic") or {}).get("age_years")),
        "education_level": (payload_data.get("demographic") or {}).get("education_level", ""),
        "consent_json": payload_data.get("consent"),
        "consent_flags_json": consent_flags,
        "demographic_json": payload_data.get("demographic"),
        "anthro_responses_json": anthro_responses,
        "achive_responses_json": achive_responses,
        "motivation_responses_json": motivation_responses,
        "motivation_scores_json": payload_data.get("motivation_category_scores"),
        "difficulty_checks_json": difficulty_checks,
        "manipulation_check_json": manipulation_full,
        "inference_summary_json": inference_summary,
        "inference_details_json": inference_details,
        "inference_responses_json": inference_responses,
        "feedback_messages_json": feedback_messages,
        "open_feedback_text": open_feedback,
        "meta_full_json": meta,
        "payload_full_json": payload_data,
        "experiment_record_full_json": experiment_data,
        "schema_version": schema_version,
    }

    for column in JSON_COLUMNS:
        row_map[column] = _json_or_blank(row_map.get(column))

    # Ensure primitives or blank strings for non-JSON columns.
    for key in set(SHEET_COLUMNS) - JSON_COLUMNS:
        if row_map.get(key) is None:
            row_map[key] = ""

    return [row_map.get(column, "") for column in SHEET_COLUMNS]


def save_to_sheets(row: List[Any], worksheet: Optional[str] = None) -> str:
    """Append the given row to Google Sheets with a stable header."""
    if not google_ready():
        raise RuntimeError("Google Sheets credentials not configured.")
    if len(row) != len(SHEET_COLUMNS):
        raise ValueError(
            f"Sheet row length {len(row)} does not match expected {len(SHEET_COLUMNS)} columns."
        )

    try:
        config = get_cfg()
    except RuntimeError:
        config = {}

    worksheet_name = (
        worksheet
        or config.get("worksheet_name")
        or os.getenv("GOOGLE_SHEET_WORKSHEET")
        or os.getenv("GOOGLE_SHEET_WORKSHEET_NAME")
        or "responses"
    )
    append_row_to_sheet(row, worksheet=worksheet_name, header=SHEET_COLUMNS)
    return f"sheets:{worksheet_name}"


def _storage_client():
    try:
        from google.cloud import storage
    except ImportError as exc:
        raise RuntimeError("google-cloud-storage not installed") from exc

    try:
        cfg = get_cfg()
    except RuntimeError:
        cfg = {}
    credentials_info = dict(cfg.get("service_account") or {})

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
    bucket_name = get_gcs_bucket_name()
    if not bucket_name:
        return False, "GCS bucket not configured"

    try:
        client = _storage_client()
    except Exception as exc:  # pragma: no cover - runtime dependent
        return False, f"GCS client unavailable: {exc}"

    meta = storage_record.get("meta") or {}
    participant_source = (
        meta.get("participant_id")
        or storage_record.get("participant_id")
        or "unknown"
    )
    participant_id = str(participant_source).replace("/", "_")
    finished_at = (
        meta.get("end_time")
        or storage_record.get("end_time")
        or meta.get("finished_at")
        or storage_record.get("finished_at")
        or meta.get("saved_at")
        or storage_record.get("saved_at")
        or now_utc_iso()
    )
    safe_timestamp = str(finished_at).replace(":", "-")
    blob_name = f"participants/{participant_id}_{safe_timestamp}_{uuid.uuid4().hex[:8]}.json"
    try:
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(
            json.dumps(storage_record, ensure_ascii=False, default=str),
            content_type="application/json",
        )
    except Exception as exc:  # pragma: no cover - runtime dependent
        return False, f"GCS upload failed: {exc}"
    return True, f"gcs:{bucket_name}/{blob_name}"


def get_gcs_bucket_name() -> Optional[str]:
    try:
        cfg = get_cfg()
    except RuntimeError:
        cfg = {}
    bucket = cfg.get("gcs_bucket")
    if bucket:
        return str(bucket)
    env_bucket = os.getenv("GCS_BUCKET")
    return env_bucket or None
