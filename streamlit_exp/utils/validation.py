import re

def validate_phone(phone: str) -> bool:
    pattern = r"^01[0-9]-\d{3,4}-\d{4}$"
    return re.match(pattern, phone) is not None

def validate_text(text: str, keywords: list) -> tuple:
    text = text.strip()
    if len(text) < 10:
        return False, "최소 10자 이상 작성해야 합니다."
    missing = [kw for kw in keywords if kw not in text]
    if missing:
        return False, f"다음 단어를 반드시 포함해야 합니다: {', '.join(missing)}"
    if re.search(r"(.)\1{6,}", text):
        return False, "의미 없는 반복된 글자를 사용하지 마세요."
    return True, ""
