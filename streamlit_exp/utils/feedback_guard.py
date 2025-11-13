from __future__ import annotations

from typing import Any, Callable

import streamlit as st


def _feedback_cache_key(phase_id: str) -> str:
    return f"feedback_payload_{phase_id}"


def _feedback_flag_key(phase_id: str) -> str:
    return f"feedback_generated_{phase_id}"


def get_feedback_once(
    phase_id: str, generate_fn: Callable[..., Any], *args: Any, **kwargs: Any
) -> Any:
    """
    Generate feedback exactly once per phase_id.
    Subsequent calls in the same session rerun only return cached payload.
    """
    cache_key = _feedback_cache_key(phase_id)
    flag_key = _feedback_flag_key(phase_id)
    if cache_key not in st.session_state:
        payload = generate_fn(*args, **kwargs)
        st.session_state[cache_key] = payload
        st.session_state[flag_key] = True
    return st.session_state[cache_key]
