from datetime import datetime
import streamlit as st
from utils.google_sheet import append_row_to_sheet

def save_to_csv(data: dict, sheet_name: str = "resp") -> None:
    """
    추론 과제 저장용 최종본.
    main.py에서 save_to_csv(st.session_state.data)로 호출하면
    secrets의 스프레드시트 내 sheet_name(기본 'resp') 탭에 저장됩니다.
    """

    # --- 날짜(YYYY-MM-DD) ---
    start_iso = data.get("startTime") or data.get("startTime_iso") or ""
    try:
        date = datetime.fromisoformat(start_iso).strftime("%Y-%m-%d") if start_iso else ""
    except Exception:
        date = start_iso

    # --- 기본 메타 ---
    consent_research = data.get("consent_research", "")
    consent_privacy  = data.get("consent_privacy", "")
    gender = data.get("gender", "")
    age    = data.get("age", "")

    anthro = data.get("anthro_responses", []) or []
    anthro_str = ",".join(map(str, anthro))

    # --- 추론 결과(세션 값 우선) ---
    answers  = st.session_state.get("inference_answers") or data.get("inference_answers") or []
    duration = st.session_state.get("inference_duration_sec") or data.get("inference_duration_sec") or ""
    score    = st.session_state.get("inference_score") or data.get("inference_score") or ""

    # 정확도(소수 3자리). 문항 수가 비어있으면 10으로 가정
    n_items = len(answers) if len(answers) > 0 else 10
    try:
        accuracy = round((int(score) / n_items), 3) if score != "" else ""
    except Exception:
        accuracy = ""

    # --- 문항별 필드(10×[selected, correct, is_correct, rationales]) ---
    # 헤더 순서: Q1_selected Q1_correct Q1_is_correct Q1_rationales ... Q10_*
    per_q_fields = []
    for i in range(10):
        if i < len(answers):
            a = answers[i] or {}
            sel = a.get("selected_idx", "")
            cor = a.get("correct_idx", "")
            is_ok = ""
            if sel != "" and cor != "":
                try:
                    is_ok = 1 if int(sel) == int(cor) else 0
                except Exception:
                    is_ok = ""
            rats = ",".join(a.get("rationales", []) or [])
            per_q_fields.extend([sel, cor, is_ok, rats])
        else:
            per_q_fields.extend(["", "", "", ""])

    # --- 나머지 ---
    feedback_set = data.get("feedback_set", "")
    motivation   = ",".join(map(str, data.get("motivation_responses", []) or []))
    phone        = data.get("phone", "")
    end_iso      = data.get("endTime") or data.get("endTime_iso") or ""

    # --- 최종 행 구성 (헤더와 1:1 매칭) ---
    row = [
        date,
        consent_research,
        consent_privacy,
        gender,
        age,
        anthro_str,
        duration,
        score,
        accuracy,
        *per_q_fields,
        feedback_set,
        motivation,
        phone,
        start_iso,
        end_iso,
    ]

    append_row_to_sheet(row, worksheet=sheet_name)
