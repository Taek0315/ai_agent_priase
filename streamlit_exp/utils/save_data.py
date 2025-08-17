from datetime import datetime
from utils.google_sheet import append_row_to_sheet

def save_to_csv(data: dict, sheet_name: str = "resp") -> None:
    """
    추론 과제 기반 저장.
    main.py에서 save_to_csv(st.session_state.data)로 호출.
    - data에는 동의/인구통계/의인화/동기/피드백 세트가 들어있고,
    - 추론 결과(inference_answers/score/duration)는 data 또는 session_state에서 보완 조회.
    """

    # 날짜 (startTime 기준 → YYYY-MM-DD)
    st_time = data.get("startTime", "")
    if st_time:
        try:
            date = datetime.fromisoformat(st_time).strftime("%Y-%m-%d")
        except Exception:
            date = st_time
    else:
        date = ""

    # 동의(라디오)
    consent_research = data.get("consent_research", "")
    consent_privacy  = data.get("consent_privacy", "")

    # 인구통계/설문
    gender = data.get("gender", "")
    age    = data.get("age", "")

    anthro = data.get("anthro_responses", []) or []
    anthro_str = ",".join(map(str, anthro))

    motivation = data.get("motivation_responses", []) or []
    motivation_str = ",".join(map(str, motivation))

    phone = data.get("phone", "")

    # ─────────────────────────────────────────────────────────
    # 추론 결과: data에 없으면 session_state에서 보완 조회(안전장치)
    inference_answers = data.get("inference_answers")
    inference_score   = data.get("inference_score")
    inference_dur     = data.get("inference_duration_sec")

    try:
        import streamlit as st
        if not inference_answers:
            inference_answers = st.session_state.get("inference_answers", [])
        if inference_score is None:
            inference_score = st.session_state.get("inference_score", "")
        if inference_dur is None:
            inference_dur = st.session_state.get("inference_duration_sec", "")
    except Exception:
        # streamlit 외부에서 호출되는 상황 대비
        pass

    # 기본값 정리
    answers = inference_answers or []
    nq = 10  # 고정 10문항
    # 정확도
    if isinstance(inference_score, int):
        accuracy = round(inference_score / nq, 3)
    else:
        accuracy = ""

    # Q별 필드(선택텍스트/정답텍스트/정오/근거)
    q_fields = []
    for i in range(nq):
        if i < len(answers):
            a = answers[i] or {}
            opts = a.get("options", []) or []
            sel_idx = a.get("selected_idx", None)
            cor_idx = a.get("correct_idx", None)
            sel_txt = opts[sel_idx] if (isinstance(sel_idx, int) and 0 <= sel_idx < len(opts)) else ""
            cor_txt = opts[cor_idx] if (isinstance(cor_idx, int) and 0 <= cor_idx < len(opts)) else ""
            is_correct = 1 if (isinstance(sel_idx, int) and isinstance(cor_idx, int) and sel_idx == cor_idx) else 0 if sel_idx is not None else ""
            rationals = a.get("rationales", []) or []
            rat_str = "|".join(map(str, rationals))
            q_fields.extend([sel_txt, cor_txt, is_correct, rat_str])
        else:
            q_fields.extend(["", "", "", ""])  # 빈칸 패딩

    feedback_set = data.get("feedback_set", "")
    start_iso = data.get("startTime", "")
    end_iso   = data.get("endTime", "")

    # 최종 행 구성 (SHEET_COLUMNS 순서와 일치)
    row = [
        date, consent_research, consent_privacy,
        gender, age, anthro_str,
        inference_dur if inference_dur is not None else "",
        inference_score if inference_score is not None else "",
        accuracy,
        *q_fields,
        feedback_set, motivation_str, phone,
        start_iso, end_iso,
    ]

    append_row_to_sheet(row, worksheet=sheet_name)
