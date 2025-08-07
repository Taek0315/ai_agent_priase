import json
from datetime import datetime
from utils.google_sheet import append_row_to_sheet

def save_to_csv(data: dict, sheet_name: str = "ai-feedback-data"):
    try:
        # 날짜 (startTime 기준)
        date = datetime.fromisoformat(data.get("startTime")).strftime("%Y-%m-%d")

        # 의인화, 동기 응답
        anthro = data.get("anthro_responses", [])
        motivation = data.get("motivation_responses", [])

        # 글쓰기 응답
        writings = data.get("writing", [])
        writing_fields = []
        for w in writings:
            writing_fields.append(" / ".join(w.get("keywords", [])))
            writing_fields.append(w.get("text", ""))

        # 총 6칸 확보: 글쓰기1 키워드, 내용 / 글쓰기2 키워드, 내용 / 글쓰기3 키워드, 내용
        while len(writing_fields) < 6:
            writing_fields.append("")

        # 최종 정리된 row
        row = [
            date,
            data.get("gender", ""),
            data.get("age", ""),
            ",".join(map(str, anthro)),
            *writing_fields,
            data.get("feedback_set", ""),
            ",".join(map(str, motivation)),
            data.get("phone", ""),
            data.get("startTime", ""),
            data.get("endTime", "")
        ]

        append_row_to_sheet(sheet_name, row)

    except Exception as e:
        print(f"[ERROR] 구글 시트 저장 중 오류 발생: {e}")
