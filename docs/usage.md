# safe_email_check

A safe, RFC-compliant email validation library for Python.

- Validates email syntax per RFC 5321/5322
- Checks domain deliverability (MX records) for signup
- Skips DNS for login flow
- Supports internationalized email addresses (Unicode/IDN)
- Rejects localhost, special-use domains, quoted locals, domain literals
- Raises friendly, human-readable errors
- No SMTP probing — does not connect to mail servers
- No fake confidence scores

## Installation

```bash
pip install safe-email-check
```

Requires Python 3.10+.

## Usage

### Signup validation (with DNS checks)

```python
from safe_email_check import validate_signup_email

try:
    result = validate_signup_email("User <Test@Example.com>", allow_display_name=True)
    print("Normalized:", result.normalized_email)   # test@example.com
    print("Domain:", result.domain)                  # example.com
    print("Display name:", result.display_name)      # User
    print("Is deliverable:", result.is_deliverable)  # True
except ValueError as e:
    print("Invalid:", e)
```

### Login validation (syntax only, no DNS)

```python
from safe_email_check import validate_login_email

result = validate_login_email("user@example.com")
print(result.is_deliverable)  # None — not checked
```

### Low-level API

```python
from safe_email_check import validate_email_address

# With deliverability check
result = validate_email_address("user@example.com", check_deliverability=True)

# Allow test environments (localhost)
result = validate_email_address("user@localhost", test_environment=True)
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
