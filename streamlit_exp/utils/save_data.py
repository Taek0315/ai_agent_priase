from datetime import datetime
from utils.google_sheet import append_row_to_sheet

def save_to_csv(data: dict, sheet_name: str = "resp") -> None:
    """
    main.py에서 save_to_csv(st.session_state.data)로 호출하면
    secrets의 스프레드시트 내 sheet_name(기본 'resp') 탭에 저장됩니다.
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

    # 신규: 동의 값(라디오 선택)
    consent_research = data.get("consent_research", "")  # "동의함"/"동의하지 않음"
    consent_privacy  = data.get("consent_privacy", "")   # "동의함"/"동의하지 않음"

    anthro = data.get("anthro_responses", []) or []
    motivation = data.get("motivation_responses", []) or []
    writings = data.get("writing", []) or []

    # 글쓰기 3회 → [키워드, 내용] × 3 = 6칸
    writing_fields = []
    for w in writings[:3]:
        keywords = " / ".join(w.get("keywords", []) or [])
        text = w.get("text", "") or ""
        writing_fields.extend([keywords, text])
    while len(writing_fields) < 6:
        writing_fields.append("")

    row = [
        date,                                   # A: 날짜
        consent_research,                       # B: 연구 동의 (라디오)
        consent_privacy,                        # C: 개인정보 동의 (라디오)
        data.get("gender", ""),                 # D: 성별
        data.get("age", ""),                    # E: 연령대
        ",".join(map(str, anthro)),             # F: 의인화 응답 (쉼표구분)
        *writing_fields,                        # G~L: 글1키/글1내/글2키/글2내/글3키/글3내
        data.get("feedback_set", ""),           # M: 피드백 세트
        ",".join(map(str, motivation)),         # N: 학습동기 응답 (쉼표구분)
        data.get("phone", ""),                  # O: 전화번호
        data.get("startTime", ""),              # P: startTime (ISO)
        data.get("endTime", ""),                # Q: endTime (ISO)
    ]

    append_row_to_sheet(row, worksheet=sheet_name)
