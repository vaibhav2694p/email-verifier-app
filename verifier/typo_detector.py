import json
from pathlib import Path
from typing import Optional, Tuple, List
from difflib import SequenceMatcher
from .models import TypoResult

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_TYPO_FILE = _DATA_DIR / "domain_typos.json"

_TYPO_DB: dict[str, list[str]] = {}

# reverse lookup: typo_domain -> correct_domain
_reverse_lookup: dict[str, str] = {}


def _load_typo_db() -> dict[str, list[str]]:
    """Load the typo database from data/domain_typos.json.

    The JSON maps correct_domain -> [list of common typos].
    Falls back to a hard-coded built-in map if the file is missing.
    """
    if _TYPO_DB:
        return _TYPO_DB

    if _TYPO_FILE.exists():
        with open(_TYPO_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        for correct, typos in data.items():
            _TYPO_DB[correct.lower()] = [t.lower() for t in typos]
    else:
        _TYPO_DB.update(_BUILTIN_TYPOS)

    for correct, typos in _TYPO_DB.items():
        for typo in typos:
            _reverse_lookup[typo.lower()] = correct.lower()

    return _TYPO_DB


def _build_reverse_lookup() -> dict[str, str]:
    if _reverse_lookup:
        return _reverse_lookup
    _load_typo_db()
    return _reverse_lookup


# ── Levenshtein distance (pure-Python, no external dependency) ────────

def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the Levenshtein (edit) distance between two strings.

    Uses the standard dynamic-programming approach with O(min(m, n))
    space.
    """
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

    if len(s1) < len(s2):
        s1, s2 = s2, s1

    prev = list(range(len(s2) + 1))
    curr = [0] * (len(s2) + 1)

    for i, ch1 in enumerate(s1, start=1):
        curr[0] = i
        for j, ch2 in enumerate(s2, start=1):
            cost = 0 if ch1 == ch2 else 1
            curr[j] = min(
                prev[j] + 1,       # deletion
                curr[j - 1] + 1,   # insertion
                prev[j - 1] + cost, # substitution
            )
        prev, curr = curr, prev

    return prev[len(s2)]


# ── Similarity helpers ───────────────────────────────────────────────

def get_suggestion_confidence(original: str, suggested: str) -> float:
    """Return a confidence score between 0.0 and 1.0 indicating how
    likely *suggested* is the correct domain for *original*.

    Uses a blended score of SequenceMatcher ratio and Levenshtein
    distance normalised against the longer string length.
    """
    if original == suggested:
        return 1.0
    if not original or not suggested:
        return 0.0

    seq_score = SequenceMatcher(None, original, suggested).ratio()

    lev = levenshtein_distance(original, suggested)
    max_len = max(len(original), len(suggested))
    lev_score = 1.0 - (lev / max_len) if max_len > 0 else 0.0

    return round(0.5 * seq_score + 0.5 * lev_score, 4)


# ── Common subdomain typos ──────────────────────────────────────────

_PREFIXES_TO_STRIP = ("www.", "mail.", "webmail.", "mx.", "imap.", "smtp.")

def _strip_common_prefix(domain: str) -> str:
    """Remove prefixes that users mistakenly prepend before the real domain."""
    lower = domain.lower()
    for prefix in _PREFIXES_TO_STRIP:
        if lower.startswith(prefix):
            return domain[len(prefix):]
    return domain


# ── Hard-coded fallback typos (used when JSON file is absent) ───────

_BUILTIN_TYPOS: dict[str, list[str]] = {
    "gmail.com": [
        "gmial.com", "gamil.com", "gmail.co", "gmail.con", "gmaill.com",
        "gmael.com", "gmali.com", "gmal.com", "gmaol.com", "gmailo.com",
        "gmaikl.com", "gmai.com", "gmaul.com", "gmailcom", "gmail.cm",
    ],
    "yahoo.com": [
        "yaho.com", "yahoo.co", "yahoo.con", "yahooo.com", "yaho0.com",
        "yaoo.com", "yhaoo.com", "yahhoo.com", "yahool.com", "yahoocom",
        "yahoo.cm",
    ],
    "outlook.com": [
        "outlok.com", "outloo.com", "outlook.co", "outlook.con",
        "outlookcom", "outlook.cm",
    ],
    "hotmail.com": [
        "hotmial.com", "hotmil.com", "hotmali.com", "hotmale.com",
        "hotmal.com", "hotmail.co", "hotmail.con", "hotmailcom", "hotmail.cm",
    ],
    "live.com": ["live.co", "live.con", "livecom", "live.cm"],
    "aol.com": ["aol.co", "aol.con", "aool.com", "aolcom"],
    "icloud.com": [
        "iclod.com", "icloud.co", "icloud.con", "icloudcom", "icloud.cm",
    ],
    "protonmail.com": [
        "protonmail.co", "protonmail.con", "protomail.com", "protonmailcom",
    ],
    "proton.me": ["pronon.me", "protonm.me", "protonme"],
    "zoho.com": ["zoho.co", "zoho.con", "zohomail.com", "zohocom"],
    "fastmail.com": [
        "fastmail.co", "fastmail.con", "fstmail.com", "fastmailcom",
    ],
    "mail.com": ["mail.co", "mail.con", "mailcom"],
    "gmx.com": ["gmx.co", "gmx.con", "gmxcom"],
    "tutanota.com": [
        "tutanota.co", "tutanota.con", "tutamail.com", "tutanotamail.com",
    ],
    "yandex.com": ["yandex.co", "yandex.con", "yandexcom"],
}

# ── Fuzzy-match threshold ───────────────────────────────────────────

_FUZZY_THRESHOLD = 0.70


# ── Public API ──────────────────────────────────────────────────────

def detect_typo(domain: str) -> TypoResult:
    """Detect if *domain* is a likely typo of a known email provider.

    Detection strategy (in order):
      1. Exact match in the reverse lookup (typo -> correct).
      2. Fuzzy match against all known typo variants using Levenshtein
         distance (edit distance threshold).
      3. Common-subdomain prefix stripping (e.g. www.gmail.com).
      4. Levenshtein-based fuzzy match against all *correct* domains in
         the database.

    Returns a TypoResult with is_possible_typo, suggested_email,
    suggested_domain, original_domain, and suggestion_confidence.
    """
    result = TypoResult(original_domain=domain)
    lower_domain = domain.lower().strip()

    reverse = _build_reverse_lookup()
    _load_typo_db()

    # If domain is itself a known correct domain, not a typo
    if lower_domain in _TYPO_DB:
        return result

    # ── 1. Exact reverse lookup ─────────────────────────────────────
    if lower_domain in reverse:
        correct = reverse[lower_domain]
        conf = get_suggestion_confidence(lower_domain, correct)
        return TypoResult(
            is_possible_typo=True,
            suggested_domain=correct,
            original_domain=domain,
            suggestion_confidence=conf,
        )

    # ── 2. Fuzzy match against known typo variants ──────────────────
    best_match: Optional[str] = None
    best_score: float = 0.0
    for correct, typos in _TYPO_DB.items():
        if lower_domain == correct:
            continue
        for typo in typos:
            score = get_suggestion_confidence(lower_domain, typo)
            if score > best_score and score >= _FUZZY_THRESHOLD:
                best_score = score
                best_match = correct

    if best_match:
        conf = get_suggestion_confidence(lower_domain, best_match)
        return TypoResult(
            is_possible_typo=True,
            suggested_domain=best_match,
            original_domain=domain,
            suggestion_confidence=conf,
        )

    # ── 3. Common subdomain prefix stripping ────────────────────────
    stripped = _strip_common_prefix(lower_domain)
    if stripped != lower_domain and stripped in reverse:
        correct = reverse[stripped]
        conf = get_suggestion_confidence(lower_domain, correct)
        return TypoResult(
            is_possible_typo=True,
            suggested_domain=correct,
            original_domain=domain,
            suggestion_confidence=conf,
        )

    # ── 4. Fuzzy match against all *correct* domains ────────────────
    best_correct: Optional[str] = None
    best_domain_score: float = 0.0
    for correct in _TYPO_DB:
        if lower_domain == correct:
            continue
        score = get_suggestion_confidence(lower_domain, correct)
        if score > best_domain_score and score >= _FUZZY_THRESHOLD:
            best_domain_score = score
            best_correct = correct

    if best_correct:
        conf = get_suggestion_confidence(lower_domain, best_correct)
        return TypoResult(
            is_possible_typo=True,
            suggested_domain=best_correct,
            original_domain=domain,
            suggestion_confidence=conf,
        )

    return result
