from __future__ import annotations

import re


LOCAL_PART_PATTERN = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$")
DOMAIN_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9-]+$")


def normalize_email(value: object) -> str:
    return str(value or "").strip()


def validate_email_format(email: str) -> tuple[bool, str]:
    normalized = normalize_email(email)
    if not normalized:
        return False, "Missing email"
    if len(normalized) > 254:
        return False, "Email exceeds 254 characters"
    if any(character.isspace() for character in normalized):
        return False, "Email contains whitespace"
    if normalized.count("@") != 1:
        return False, "Email must contain exactly one @"

    local_part, domain = normalized.rsplit("@", 1)
    if not local_part:
        return False, "Email is missing the local part"
    if len(local_part) > 64:
        return False, "Email local part exceeds 64 characters"
    if local_part.startswith(".") or local_part.endswith(".") or ".." in local_part:
        return False, "Email local part has invalid dots"
    if not LOCAL_PART_PATTERN.fullmatch(local_part):
        return False, "Email local part has invalid characters"

    valid_domain, domain_reason = validate_domain_format(domain)
    if not valid_domain:
        return False, domain_reason

    return True, "Valid"


def extract_domain(email: str) -> str:
    normalized = normalize_email(email)
    if "@" not in normalized:
        return ""
    return normalized.rsplit("@", 1)[1].strip().strip(".").lower()


def validate_domain_format(domain: str) -> tuple[bool, str]:
    normalized_domain = str(domain or "").strip().strip(".")
    if not normalized_domain:
        return False, "Email is missing the domain"
    if len(normalized_domain) > 253:
        return False, "Email domain exceeds 253 characters"
    if "." not in normalized_domain:
        return False, "Email domain must contain a dot"

    try:
        ascii_domain = normalized_domain.encode("idna").decode("ascii")
    except UnicodeError:
        return False, "Email domain has invalid international characters"

    labels = ascii_domain.split(".")
    for label in labels:
        if not label:
            return False, "Email domain has an empty label"
        if len(label) > 63:
            return False, "Email domain label exceeds 63 characters"
        if label.startswith("-") or label.endswith("-"):
            return False, "Email domain label has invalid hyphens"
        if not DOMAIN_LABEL_PATTERN.fullmatch(label):
            return False, "Email domain has invalid characters"

    top_level_domain = labels[-1]
    if len(top_level_domain) < 2:
        return False, "Email top-level domain is too short"
    if top_level_domain.isdigit():
        return False, "Email top-level domain cannot be all numeric"

    return True, "Valid"
