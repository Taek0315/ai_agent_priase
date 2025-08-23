# utils/save_data.py
from datetime import datetime
import streamlit as st
from utils.google_sheet import append_row_to_sheet

def save_to_csv(data: dict, sheet_name: str = "resp") -> None:
    """
    최종 저장 함수.
    - 의인화 30문항: anthro_responses -> CSV 문자열
    - 추가 설문 26문항(6점 척도): achive_responses -> CSV 문자열
    - 추론 과제: 10문항 상세(선택/정답/정오/근거) + 소요시간/점수/정확도
    - 학습동기: 7문항 -> CSV 문자열
    """
    # --- 날짜 ---
    start_iso = data.get("startTime") or data.get("startTime_iso") or ""
    try:
        date = datetime.fromisoformat(start_iso).strftime("%Y-%m-%d") if start_iso else ""
    except Exception:
        date = start_iso

    # --- 동의/인구통계 ---
    consent_research = data.get("consent_research", "")
    consent_privacy  = data.get("consent_privacy", "")
    gender = data.get("gender", "")
    age    = data.get("age", "")

    # --- 의인화 30문항 ---
    anthro = data.get("anthro_responses", []) or []
    anthro_str = ",".join(map(str, anthro))

    # --- 추가 설문 26문항(6점) ---
    achive = data.get("achive_responses", []) or []
    achive_str = ",".join("" if v is None else str(v) for v in achive)

    # --- 추론 과제 결과(세션 값 우선) ---
    answers  = st.session_state.get("inference_answers") or data.get("inference_answers") or []
    duration = st.session_state.get("inference_duration_sec") or data.get("inference_duration_sec") or ""
    score    = st.session_state.get("inference_score") or data.get("inference_score") or ""

    # 정확도
    n_items = len(answers) if len(answers) > 0 else 10
    try:
        accuracy = round((int(score) / n_items), 3) if score != "" else ""
    except Exception:
        accuracy = ""

    # --- 문항별 상세 10×(selected, correct, is_correct, rationales) ---
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

    # --- 최종 행 (헤더와 1:1) ---
    row = [
        date,                 # A
        consent_research,     # B
        consent_privacy,      # C
        gender,               # D
        age,                  # E
        anthro_str,           # F
        achive_str,           # G  ✅ 추가 설문 26문항(6점)
        duration,             # H
        score,                # I
        accuracy,             # J
        *per_q_fields,        # K..AF (Q1~Q10 * 4칸)
        feedback_set,         # AG
        motivation,           # AH
        phone,                # AI
        start_iso,            # AJ
        end_iso,              # AK
    ]

    append_row_to_sheet(row, worksheet=sheet_name)
