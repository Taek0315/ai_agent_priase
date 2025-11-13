# [CHANGE] Shared UI helpers for numeric-only Likert rendering.
from __future__ import annotations

import hashlib
import re
from typing import Dict, Iterable, List, Optional

import streamlit as st

from constants import LIKERT5_NUMERIC_OPTIONS


_KEY_SANITIZER = re.compile(r"[^0-9a-zA-Z_]+")


def _sanitize_key(raw: str) -> str:
    cleaned = _KEY_SANITIZER.sub("_", raw).strip("_")
    if not cleaned:
        cleaned = "likert"
    if cleaned[0].isdigit():
        cleaned = f"_{cleaned}"
    if len(cleaned) > 100:
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
        cleaned = f"{cleaned[:91]}_{digest}"
    return cleaned


def render_likert_numeric(
    item_id: str,
    label: str,
    *,
    options: Optional[Iterable[int]] = None,
    key_prefix: str = "likert",
    horizontal: bool = True,
) -> Optional[int]:
    """
    Render a numeric-only Likert radio group without a default selection.

    Returns the selected integer (1..5 by default) or None when unanswered.
    """
    option_list: List[int] = list(options) if options is not None else LIKERT5_NUMERIC_OPTIONS
    safe_key = _sanitize_key(f"{key_prefix}_{item_id}")
    selection = st.radio(
        label,
        option_list,
        index=None,
        format_func=lambda value: f"{value}",
        horizontal=horizontal,
        key=safe_key,
    )
    if selection in option_list:
        return int(selection)
    return None


def all_answered(
    responses: Dict[str, Optional[int]],
    expected: int,
    *,
    valid_options: Optional[Iterable[int]] = None,
) -> bool:
    """
    Return True when the given response dict has `expected` answers populated with valid integers.
    """
    if len(responses) != expected:
        return False
    allowed = set(valid_options) if valid_options is not None else None
    for value in responses.values():
        if not isinstance(value, int):
            return False
        if allowed is not None and value not in allowed:
            return False
    return True
