import re

_PHONE = re.compile(r"^(01[0-9])[- ]?\d{3,4}[- ]?\d{4}$")


def validate_phone(s: str) -> bool:
    s = (s or "").strip()
    return bool(_PHONE.match(s))
