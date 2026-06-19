# safe_email_check

A safe, RFC-compliant email validation library for Python.

## Philosophy

- **Signup validation**: Full syntax + domain deliverability checks (MX/DNS).
- **Login validation**: Syntax only — no slow DNS lookups before database lookup.
- **No SMTP probing**: Does not connect to mail servers or probe mailboxes.
- **No fake scores**: Does not assign arbitrary confidence scores.
- **Internationalized**: Supports Unicode emails and IDN domains.

## Quick Start

```python
from safe_email_check import validate_signup_email, validate_login_email

# During signup — validates syntax + domain deliverability
result = validate_signup_email("User <Test@Example.com>", allow_display_name=True)
print(result.normalized_email)   # "test@example.com" ← store this
print(result.domain)             # "example.com"
print(result.display_name)       # "User"
print(result.is_deliverable)     # True (MX records exist)

# During login — syntax only, no DNS
result = validate_login_email("user@example.com")
print(result.is_deliverable)     # None (not checked)
```

## API

### `validate_signup_email(email, allow_display_name=False)`

Validates email with full deliverability (MX/DNS) checks. Raises `SafeEmailError` if the domain cannot receive mail.

### `validate_login_email(email, allow_display_name=False)`

Validates syntax only. No DNS queries. Use this before looking up the user in your database.

### `validate_email_address(email, *, check_deliverability=True, allow_display_name=False, test_environment=False)`

Low-level function with full control.

## Return Value

All functions return an `EmailCheckResult` dataclass:

| Field | Type | Description |
|-------|------|-------------|
| `original` | `str` | Input as provided |
| `normalized_email` | `str` | Lowercased, normalized form — store this |
| `local_part` | `str` | Part before `@` |
| `domain` | `str` | Part after `@` |
| `ascii_email` | `str or None` | Punycode-encoded form |
| `ascii_domain` | `str or None` | Punycode-encoded domain |
| `display_name` | `str or None` | Parsed display name (if allowed) |
| `deliverability_checked` | `bool` | Whether DNS was checked |
| `is_deliverable` | `bool or None` | `True` if DNS checks passed, `None` if skipped |

## Errors

`SafeEmailError` (subclass of `ValueError`) is raised on:

- Invalid syntax
- Disposable/role-based detection (if configured)
- Domain without MX records (only in signup mode)
- Localhost / special-use domains (unless `test_environment=True`)

## Rules

1. **Use `validate_signup_email` during account creation** — confirms the domain can receive mail.
2. **Use `validate_login_email` before database lookup** — fast syntax check only.
3. **Store only `normalized_email`** in your database.
4. **DNS checks can be slow** (1-5 seconds) — never run them on login.
5. **This library validates address format and domain deliverability**, not actual mailbox ownership.
6. **Email ownership still requires sending a verification email** to the address.
