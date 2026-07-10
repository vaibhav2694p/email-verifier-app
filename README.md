# Email Verifier

A production-ready bulk email verification and intelligence app built with Streamlit. Uses a 16-stage verification pipeline with SMTP probing, catch-all detection, typo suggestions, IDN support, comprehensive scoring, and public profile enrichment.

## Features

- **Triple-tab UI** - Bulk verification, single email, and email intelligence
- **16-stage pipeline** - Syntax → Typo → DNS/MX → Provider → SMTP → Catch-All → Disposable → Role → Scoring
- **Email Intelligence** - Public profile enrichment from company websites and social profiles
- **Three SMTP modes** - Disabled, Test (Mailpit), and Real (recipient MX probing)
- **SMTP mailbox probing** - EHLO/MAIL FROM/RCPT TO with provider-specific overrides
- **Catch-all detection** - Probes random addresses to detect catch-all mail servers
- **Domain typo detection** - Levenshtein + reverse-lookup correction suggestions
- **IDN support** - Internationalized domain names with punycode conversion
- **500+ disposable domains** - Built-in blocklist with custom file support
- **Role-based detection** - Identifies admin@, info@, support@, etc.
- **TTL cache** - Thread-safe caching to avoid repeated DNS/SMTP probes
- **Dashboard** - Real-time metrics, filters, and score breakdown
- **Export** - CSV, multi-sheet Excel with domain summaries and statistics
- **Mailpit integration** - Free local SMTP test server via Docker Compose
- **Email Intelligence** - Person and company enrichment from public web sources
- **Domain-deduplicated lookups** - Company data cached per domain, not per email
- **Profile matching** - Confidence-ranked person profiles with source tracking

## Architecture

```
app.py                          # Streamlit UI (dual-tab)
verifier/
  pipeline.py                   # 16-stage orchestrator
  models.py                     # VerificationResult, PipelineStage, enums
  config.py                     # VerifierConfig (env vars + defaults)
  cache.py                      # Thread-safe TTLCache
  normalizer.py                 # Email/domain normalization, IDN/punycode
  syntax_validator.py           # 15-rule RFC-compliant syntax check
  typo_detector.py              # Levenshtein + reverse-lookup
  dns_validator.py              # MX lookup with retry + TTL cache
  mx_provider.py                # Provider classification from MX records
  smtp_validator.py             # SMTP probing (test mode + real MX)
  catch_all.py                  # Random-address catch-all detection
  disposable.py                 # Disposable domain detection
  role_detector.py              # Role-based address detection
  scoring.py                    # Weighted confidence scoring
services/
  bulk_processor.py             # ThreadPoolExecutor + duplicate detection
  export_service.py             # CSV/XLSX export with multi-sheet Excel
  summary_service.py            # Dashboard stats and filter application
data/
  disposable_domains.txt        # 500+ disposable domains
  public_domains.json           # Free domains + workspace MX patterns
  role_prefixes.json            # Role prefixes with risk adjustments
  domain_typos.json             # Common domain typos
tests/
  smtp_test_server.py           # Deterministic Python SMTP test server
  test_smtp_validation.py       # SMTP tests including test mode
  ...                           # 143 tests total
```

## SMTP Verification Modes

| Mode | Description | Port 25 Required |
|------|-------------|-----------------|
| **Disabled** | No SMTP checks. Syntax, DNS, MX, classification only. | No |
| **Test** | Connects to Mailpit or local test server. Safe for dev. | No |
| **Real** | Connects directly to recipient MX servers (EHLO/MAIL FROM/RCPT TO). | Yes |

**Safety**: The SMTP verifier never sends the `DATA` command. No emails are ever sent to the public internet during verification.

### Mailpit (Test Mode)

Mailpit is a free local SMTP test server. It captures all emails for inspection without sending them.

**Docker Compose** (recommended):
```bash
docker compose up --build
```
- Streamlit app: http://localhost:8501
- Mailpit inbox: http://localhost:8025

**Standalone Docker**:
```bash
docker run --rm --name mailpit -p 1025:1025 -p 8025:8025 axllent/mailpit
```

**Python-only** (no Docker):
```bash
streamlit run app.py
# Then set SMTP mode to "Test" in the sidebar
# Point to any SMTP server on port 1025
```

### Test Email Addresses (for test mode only)

```
accepted@example.test       -> SMTP 250
rejected@example.test       -> SMTP 550
temporary@example.test      -> SMTP 451
greylisted@example.test     -> SMTP 450
catchall@example.test       -> SMTP 250
timeout@example.test        -> simulated timeout
tlsrequired@example.test    -> SMTP 530
```

### SMTP Fallback Logic

```
Test mode enabled -> local Mailpit or test SMTP server
Real mode enabled + port 25 available -> recipient MX servers
Real mode enabled + port 25 blocked -> connection_blocked status
SMTP disabled -> skip SMTP, continue with other checks
```

## Installation

```bash
git clone https://github.com/vaibhav2694p/email-verifier-app.git
cd email-verifier-app
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Place your logo at `assets/safebooks_logo.png`.

## Quick Start

### With Docker (recommended)

```bash
docker compose up --build
```

Open http://localhost:8501 for the app and http://localhost:8025 for Mailpit inbox.

### Without Docker

```bash
cp .env.example .env          # optional, customize settings
streamlit run app.py
```

Set SMTP mode to "Test" in the sidebar and configure the test SMTP host/port.

## Usage

### Bulk Verification
1. Upload CSV/XLSX
2. Select email column and optional company domain column
3. Click "Verify Emails"
4. View dashboard, filter results, download exports

### Single Email
1. Enter email address
2. Optionally enter company domain
3. Click "Verify Email"
4. View stage-by-stage analysis with score breakdown

### SMTP Configuration (Sidebar)
- Select verification mode: Disabled / Test / Real
- In Test mode: configure Mailpit host/port
- In Real mode: configure verifier email/domain, port, timeout
- Click "Test SMTP Connection" to verify connectivity
- Port 25 availability is checked automatically in Real mode

## Scoring

| Factor | Points |
|--------|--------|
| Valid syntax | +15 |
| MX records resolved | +20 |
| SMTP accepted | +15 |
| Known provider | +5 |
| Company domain match | +25 |
| Not public/free | +10 |
| Not disposable | +5 |
| Not role-based | +5 |
| Catch-all detected | -10 |
| Typo detected | -15 |
| Role-based email | -10 |
| Disposable domain | -50 |
| No MX records | -40 |

Status mapping: Valid (≥75), Likely Valid (≥50), Risky (≥30), Invalid (<30)

## Environment Variables

See `.env.example` for all configuration options. Key variables:

```env
# SMTP mode: disabled | test | real
SMTP_VERIFICATION_MODE=disabled

# Real MX probing
ENABLE_SMTP_CHECK=false
VERIFIER_EMAIL=verifier@company.com
VERIFIER_DOMAIN=company.com

# Test mode (Mailpit)
SMTP_TEST_MODE=false
TEST_SMTP_HOST=localhost
TEST_SMTP_PORT=1025

# Notifications (optional, admin only)
NOTIFICATION_SMTP_ENABLED=false
```

## Testing

```bash
.venv\Scripts\python.exe -m pytest tests/ -v
```

173 tests covering syntax, normalization, DNS, SMTP (test mode + real), catch-all, disposable, role detection, scoring, pipeline, bulk processing, export, caching, and email enrichment.

## Email Intelligence

The enrichment engine searches public web sources (no API keys required) to build person and company profiles from email addresses.

### What it extracts

| Category | Fields |
|----------|--------|
| **Person** | First/last name, full name, job title, department, location, phone |
| **Social** | LinkedIn, GitHub, Twitter/X, Facebook, Instagram URLs |
| **Company** | Name, description, industry, employee count, social links |
| **Domain** | Age, registrar (WHOIS) |
| **AI Summary** | Natural-language profile summary |

### Architecture

```
enrichment/
├── __init__.py          # Package exports
├── models.py            # PersonProfile, CompanyProfile, EnrichmentResult
├── cache.py             # Thread-safe TTL cache for web requests
├── search_engine.py     # Query generation, HTML/text extraction
├── company_lookup.py    # Company scraping from meta tags, social links
├── person_lookup.py     # Person enrichment from email local part
├── profile_matcher.py   # Confidence ranking, profile deduplication
├── whois_lookup.py      # Domain WHOIS (python-whois + DNS fallback)
└── summary.py           # Natural-language AI summary generation
```

### How it works

1. **Email parsing** → Extract first/last name from local part (`john.smith@`)
2. **Company lookup** → Scrape company website for meta tags, social links, employee names
3. **Person lookup** → Search for person profiles by name + company
4. **Profile matching** → Rank multiple profile candidates by confidence
5. **WHOIS** → Domain age and registrar from public WHOIS data
6. **Summary** → Generate natural-language summary from all collected data

## Production Safety

- Keep `SMTP_TEST_MODE=false` in production
- Keep `ENABLE_SMTP_CHECK=false` unless port 25 is available and use is authorized
- Never expose port 1025 or Mailpit inbox publicly
- Never commit `.env` or SMTP credentials
- Never use verification to send unsolicited messages
