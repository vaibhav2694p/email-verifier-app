from __future__ import annotations

import re

FREE_EMAIL_DOMAINS: set[str] = {
    "gmail.com", "yahoo.com", "yahoo.co.in", "yahoo.co.uk", "ymail.com",
    "outlook.com", "hotmail.com", "live.com", "msn.com", "hotmail.co.uk",
    "aol.com", "aim.com", "mail.com", "inbox.com", "zoho.com",
    "protonmail.com", "proton.me", "pm.me", "tutanota.com", "tutamail.com",
    "gmx.com", "gmx.net", "gmx.de", "web.de", "mail.de", "email.com",
    "yandex.com", "yandex.ru", "icloud.com", "me.com", "mac.com",
    "qq.com", "163.com", "126.com", "sina.com", "sohu.com",
    "rediffmail.com", "indiatimes.com", "rocketmail.com",
    "fastmail.com", "fastmail.fm", "hushmail.com",
    "mailinator.com", "guerrillamail.com", "sharklasers.com",
    "trashmail.com", "tempmail.com", "10minutemail.com",
    "dispostable.com", "throwaway.email", "temp-mail.org",
}

DISPOSABLE_DOMAINS: set[str] = {
    "mailinator.com", "guerrillamail.com", "sharklasers.com",
    "trashmail.com", "tempmail.com", "10minutemail.com",
    "dispostable.com", "throwaway.email", "temp-mail.org",
    "maildrop.cc", "getnada.com", "burnermail.io",
    "tempail.com", "eyepaste.com", "mintemail.com",
    "spamgourmet.com", "spambox.us", "mailcatch.com",
    "yopmail.com", "yopmail.fr", "yopmail.net",
    "mailexpire.com", "harakirimail.com", "mailnull.com",
    "sneakemail.com", "sofort-mail.de", "nospamfor.us",
}

ROLE_PREFIXES: set[str] = {
    "info", "admin", "support", "sales", "contact", "help",
    "webmaster", "postmaster", "noreply", "no-reply", "mailer-daemon",
    "abuse", "billing", "hr", "jobs", "marketing", "media",
    "newsletter", "office", "partner", "press", "privacy",
    "register", "service", "subscribe", "team", "test", "root",
    "devnull", "enquiries", "feedback", "complaints", "careers",
    "recruitment", "notifications", "notification",
}

ROLE_PATTERN = re.compile(
    r"^(info|admin|support|sales|contact|help|webmaster|postmaster|"
    r"noreply|no-reply|abuse|billing|hr|marketing|media|newsletter|"
    r"office|partner|press|register|service|subscribe|team|test|root|"
    r"careers|recruitment|notifications|notification|feedback|"
    r"enquiries|complaints|devnull)\d*$",
    re.IGNORECASE,
)


def is_free_email(domain: str) -> bool:
    return domain.lower() in FREE_EMAIL_DOMAINS


def is_disposable_email(domain: str) -> bool:
    return domain.lower() in DISPOSABLE_DOMAINS


def is_role_account(local_part: str) -> bool:
    return bool(ROLE_PATTERN.fullmatch(local_part))
