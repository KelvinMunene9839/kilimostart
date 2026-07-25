"""Basic input validation for phone numbers used as farmer IDs."""

import re

_PHONE_PATTERN = re.compile(r"^\+?\d{9,13}$")


def is_valid_phone(phone: str) -> bool:
    return bool(_PHONE_PATTERN.match(phone.strip()))
