from datetime import datetime
from utils.google_sheet import append_row_to_sheet

def save_to_csv(data: dict, sheet_name: str = "ai-feedback-data"):
    # 날짜 (startTime 기준)
    date = ""
    if data.get("startTime"):
        try:
            date = datetime.fromisoformat(data["startTime"]).strftime("%Y-%m-%d")
        except Exception:
            date = data.get("startTime", "")

    anthro = data.get("anthro_responses", [])
    motivation = data.get("motivation_responses", [])
    writings = data.get("writing", [])

    # 글쓰기 3회 → [키워드, 내용] × 3 = 6칸
    writing_fields = []
    for w in writings[:3]:
        writing_fields.append(" / ".join(w.get("keywords", [])))
        writing_fields.append(w.get("text", ""))
    while len(writing_fields) < 6:
        writing_fields.append("")

    row = [
        date,                                 # 날짜
        data.get("gender", ""),               # 성별
        data.get("age", ""),                  # 연령대
        ",".join(map(str, anthro)),           # 의인화 응답 (쉼표구분)
        *writing_fields,                      # 글1 키워드, 글1 내용, 글2 키워드, 글2 내용, 글3 키워드, 글3 내용
        data.get("feedback_set", ""),         # 피드백 세트
        ",".join(map(str, motivation)),       # 학습동기 응답 (쉼표구분)
        data.get("phone", ""),                # 전화번호
        data.get("startTime", ""),            # startTime
        data.get("endTime", ""),              # endTime
    ]

    append_row_to_sheet(sheet_name, row)
