# Email Verifier

A Streamlit tool for validating uploaded CSV/XLSX lead lists and exporting enriched verification results.

## Run

```powershell
pip install -r requirements.txt
streamlit run app.py
```

## Checks

- Basic email format validation
- Domain existence
- MX records
- SPF TXT record
- DMARC TXT record
- LinkedIn search URL generation for `site:linkedin.com/in` or `site:linkedin.com`

## Output

The generated CSV includes name, company name, email, domain, DNS statuses, email format status, LinkedIn search URL, verification score, and notes.
