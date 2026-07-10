# Email Verifier

A production-ready bulk email verification app built with Streamlit. Uses a 16-stage verification pipeline with SMTP probing, catch-all detection, typo suggestions, IDN support, and comprehensive scoring.

## Features

- **Dual-tab UI** - Bulk verification (CSV/XLSX upload) and single-email lookup
- **16-stage pipeline** - Syntax → Typo → DNS/MX → Provider → SMTP → Catch-All → Disposable → Role → Scoring
- **SMTP mailbox probing** - EHLO/MAIL FROM/RCPT TO conversation with provider-specific overrides (Gmail, Outlook, Yahoo)
- **Catch-all detection** - Probes random addresses to detect catch-all mail servers
- **Domain typo detection** - Levenshtein + reverse-lookup correction suggestions
- **IDN support** - Internationalized domain names with punycode conversion
- **500+ disposable domains** - Built-in blocklist with custom file support
- **Role-based detection** - Identifies admin@, info@, support@, etc.
- **TTL cache** - Thread-safe caching to avoid repeated DNS/SMTP probes
- **Dashboard** - Real-time metrics, filters, and score breakdown
- **Export** - CSV, multi-sheet Excel with domain summaries and statistics

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
  smtp_validator.py             # SMTP EHLO/MAIL FROM/RCPT TO probing
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
```

## Installation

```bash
git clone https://github.com/vaibhav2694p/email-verifier-Streamlit-app.git
cd email-verifier-Streamlit-app
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Place your logo at `assets/safebooks_logo.png`.

## Usage

```bash
streamlit run app.py
```

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

## Docker

```bash
docker compose up --build
```

## Testing

```bash
.venv\Scripts\python.exe -m pytest tests/ -v
```

131 tests covering syntax, normalization, DNS, SMTP, catch-all, disposable, role detection, scoring, pipeline, bulk processing, export, and caching.
