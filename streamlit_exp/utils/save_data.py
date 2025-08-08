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
        date,                                 # A: 날짜
        data.get("gender", ""),               # B: 성별
        data.get("age", ""),                  # C: 연령대
        ",".join(map(str, anthro)),           # D: 의인화 응답 (쉼표구분)
        *writing_fields,                      # E~J: 글1키/글1내/글2키/글2내/글3키/글3내
        data.get("feedback_set", ""),         # K: 피드백 세트
        ",".join(map(str, motivation)),       # L: 학습동기 응답 (쉼표구분)
        data.get("phone", ""),                # M: 전화번호
        data.get("startTime", ""),            # N: startTime
        data.get("endTime", ""),              # O: endTime
    ]

    # row를 첫 인자로, 워크시트는 인자로 명시
    append_row_to_sheet(row, worksheet=sheet_name)
