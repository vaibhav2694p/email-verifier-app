from __future__ import annotations

import re


def extract_names_from_email(email: str) -> dict[str, str]:
    if "@" not in email:
        return {"first_name": "", "last_name": "", "full_name": ""}

    local_part = email.split("@")[0]
    first_name = ""
    last_name = ""
    full_name = ""

    separators = re.split(r"[._\-+]", local_part)
    meaningful = [s for s in separators if s and not s.isdigit()]

    if len(meaningful) == 1:
        name = _split_camel_case(meaningful[0])
        parts = name.split()
        if len(parts) >= 2:
            first_name = parts[0].capitalize()
            last_name = parts[-1].capitalize()
            full_name = f"{first_name} {last_name}"
        else:
            first_name = parts[0].capitalize()
            full_name = first_name
    elif len(meaningful) >= 2:
        first_name = _clean_name_part(meaningful[0])
        last_name = _clean_name_part(meaningful[-1])
        full_name = f"{first_name} {last_name}"

    return {
        "first_name": first_name,
        "last_name": last_name,
        "full_name": full_name,
    }


def _clean_name_part(part: str) -> str:
    cleaned = re.sub(r"\d+", "", part).strip()
    if not cleaned:
        return ""
    parts = _split_camel_case(cleaned)
    split = parts.split()
    return split[0].capitalize() if split else cleaned.capitalize()


def _split_camel_case(text: str) -> str:
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
