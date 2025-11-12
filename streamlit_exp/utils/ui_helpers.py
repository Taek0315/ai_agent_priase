# [CHANGE] Shared UI helpers for numeric-only Likert rendering.
from __future__ import annotations

from typing import Dict, Iterable, List, Optional

import streamlit as st

from constants import LIKERT5_NUMERIC_OPTIONS


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
    widget_key = f"{key_prefix}_{item_id}"
    current = st.session_state.get(widget_key)
    index = option_list.index(current) if current in option_list else None

    try:
        selection = st.radio(
            label,
            option_list,
            index=index,
            format_func=lambda value: f"{value}",
            horizontal=horizontal,
            key=widget_key,
        )
    except TypeError:
        placeholder = "선택하세요"
        display = [placeholder, *option_list]
        fallback_index = display.index(current) if current in option_list else 0
        choice = st.radio(
            label,
            display,
            index=fallback_index,
            format_func=lambda value: f"{value}",
            horizontal=horizontal,
            key=f"{widget_key}_fallback",
        )
        if choice == placeholder:
            st.session_state.pop(widget_key, None)
            return None
        selection = int(choice)
        st.session_state[widget_key] = selection
        return selection

    if selection is None:
        st.session_state.pop(widget_key, None)
        return None
    st.session_state[widget_key] = int(selection)
    return int(selection)


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
