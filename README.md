# Email Verifier

A Streamlit application for verifying email lists with domain validation, MX checks, and scoring.

## Features
- Single-page interface with professional UI
- Safebooks Global branding
- CSV/XLSX file upload
- Email validation with syntax normalization
- Domain extraction and cleaning
- MX record lookup with DNS timeout handling
- Website reachability checking
- Email provider detection (Google, Microsoft, etc.)
- Disposable email detection
- Public email domain detection
- Role-based email identification
- Company domain matching verification
- Accurate scoring system (0-100)
- Results table with status badges
- Excel and CSV download options

## Installation
1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Place the Safebooks Global logo at `assets/safebooks_logo.png`

## Usage
Run the application:
```bash
streamlit run app.py
```
1. Upload your CSV or XLSX file containing email addresses
2. Select the email column
3. (Optional) Select a company domain column for matching verification
4. Click "Verify Emails"
5. View results and download as Excel or CSV

## Output Columns
- **Email**: Original email address
- **Normalized Email**: Validated and normalized email
- **Domain**: Extracted domain from email
- **Domain Active**: Whether website is reachable (Yes/No)
- **Website Status**: Detailed website check result
- **MX Status**: MX records found or error status
- **Email Provider**: Detected email service provider
- **Verification Status**: Final status (Verified, Risky, Invalid, etc.)
- **Verification Score**: Score from 0-100 based on verification checks
- **Notes**: Additional information about the verification

## Scoring Logic
The application uses a weighted scoring system with caps:

| Check | Points |
|-------|--------|
| Valid email syntax | +10 |
| MX records found | +20 |
| Website active | +15 |
| Known email provider | +10 |
| Company domain match | +30 |
| Not public/free email | +10 |
| Not disposable | +10 |
| Role-based email | -10 |

Score caps (applied in order):
- Invalid syntax: 0
- Disposable email: max 10
- No MX found: max 20
- Public/free email: max 45
- Company domain mismatch: max 50

Final score is clamped between 0-100.

## Important Notes
- MX records indicate server configuration, not mailbox existence
- Public email domains (Gmail, Yahoo, etc.) are capped at 45 points
- True email ownership verification requires sending a confirmation email
- The application does not perform SMTP mailbox probing for security and privacy reasons
