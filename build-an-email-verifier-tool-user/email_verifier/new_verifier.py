from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

import dns.resolver
import pandas as pd
import streamlit as st

ROLE_PREFIXES = (
    "info", "sales", "support", "admin", "contact",
    "hello", "marketing", "hr", "careers", "billing",
    "team", "help", "enquiries", "enquiry", "office",
    "noreply", "no-reply", "newsletter", "jobs",
)

_PUBLIC_DOMAINS: frozenset[str] = frozenset({
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "aol.com", "icloud.com", "proton.me", "protonmail.com",
    "live.com", "msn.com", "ymail.com", "mail.com",
    "zoho.com", "yandex.com", "gmx.com", "gmx.net",
    "fastmail.com", "tutanota.com", "tutamail.com",
    "rediffmail.com", "qq.com", "naver.com", "daum.net",
    "163.com", "126.com", "sina.com", "sohu.com",
})

_DISPOSABLE_DOMAINS: set[str] | None = None


def _load_disposable_domains() -> set[str]:
    global _DISPOSABLE_DOMAINS
    if _DISPOSABLE_DOMAINS is not None:
        return _DISPOSABLE_DOMAINS
    _DISPOSABLE_DOMAINS = set()
    txt_path = Path(__file__).parent / "disposable_domains.txt"
    if txt_path.exists():
        for line in txt_path.read_text(encoding="utf-8").splitlines():
            domain = line.strip().lower()
            if domain and not domain.startswith("#"):
                _DISPOSABLE_DOMAINS.add(domain)
    return _DISPOSABLE_DOMAINS


def clean_domain(value: str) -> str:
    if pd.isna(value):
        return ""
    domain = str(value).strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = re.sub(r"^www\.", "", domain)
    domain = domain.split("/")[0]
    domain = domain.split(":")[0]
    domain = domain.strip()
    if not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", domain):
        return ""
    return domain


def extract_email_domain(email: str) -> str:
    email = str(email).strip()
    if "@" in email:
        return email.split("@", 1)[1].strip().lower()
    return ""


def is_valid_email(email: str) -> bool:
    email = str(email).strip()
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def lookup_mx_records(domain: str) -> tuple[bool, str]:
    if not domain:
        return False, "No domain provided"
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        records = sorted(
            [f"{r.preference} {str(r.exchange).rstrip('.')}" for r in answers]
        )
        if records:
            return True, ", ".join(records)
        return False, "No MX records found"
    except dns.resolver.NXDOMAIN:
        return False, "Domain does not exist"
    except dns.resolver.NoAnswer:
        return False, "No MX records found"
    except dns.resolver.NoNameservers:
        return False, "DNS error"
    except dns.exception.Timeout:
        return False, "DNS timeout"
    except Exception as e:
        return False, f"Lookup failed: {e}"


def check_spf(domain: str) -> bool:
    if not domain:
        return False
    try:
        answers = dns.resolver.resolve(domain, "TXT", lifetime=5)
        for r in answers:
            txt = str(r).lower()
            if "v=spf1" in txt:
                return True
    except Exception:
        pass
    return False


def check_dmarc(domain: str) -> bool:
    if not domain:
        return False
    try:
        dmarc_domain = f"_dmarc.{domain}"
        answers = dns.resolver.resolve(dmarc_domain, "TXT", lifetime=5)
        for r in answers:
            txt = str(r).lower()
            if "v=dmarc1" in txt:
                return True
    except Exception:
        pass
    return False


def is_public_email_domain(domain: str) -> bool:
    return domain.strip().lower() in _PUBLIC_DOMAINS


def is_disposable_domain(domain: str) -> bool:
    disposables = _load_disposable_domains()
    return domain.strip().lower() in disposables


def is_role_based_email(email: str) -> bool:
    local = str(email).split("@", 1)[0].strip().lower() if "@" in email else ""
    local = re.sub(r"[^a-zA-Z0-9]", "", local)
    return local in ROLE_PREFIXES


def calculate_verification_score(result: dict) -> tuple[int, str, str]:
    if not result.get("syntax_valid", False):
        return 0, "Invalid", "Invalid email syntax"

    if result.get("is_disposable", False):
        return 10, "Disposable", "Disposable email domain"

    score = 10
    notes = []

    if result.get("mx_found", False):
        score += 20
    else:
        return min(score, 20), "No MX Found", "Domain has no MX records"

    if result.get("spf_found", False):
        score += 10
    else:
        notes.append("SPF missing")

    if result.get("dmarc_found", False):
        score += 10
    else:
        notes.append("DMARC missing")

    if result.get("company_domain_match") is True:
        score += 30
    elif result.get("company_domain_match") is False:
        score = min(score, 50)
        notes.append("Email domain does not match company domain")

    if not result.get("is_public_email", False):
        score += 10
    else:
        score = min(score, 45)
        notes.append("Public/free email provider")

    if not result.get("is_disposable", False):
        score += 10

    if result.get("is_role_based", False):
        score -= 10
        notes.append("Role-based email")

    score = max(0, min(score, 100))

    if result.get("is_public_email", False):
        status = "Public Email"
    elif result.get("company_domain_match") is False:
        status = "Company Domain Mismatch"
    elif score >= 80:
        status = "Verified"
    elif score >= 50:
        status = "Risky"
    else:
        status = "Invalid"

    return score, status, "; ".join(notes) or status


def verify_email_row(
    email: str,
    company_domain_input: str | None = None,
) -> dict:
    email = str(email).strip()
    email_domain = extract_email_domain(email)
    syntax_valid = is_valid_email(email)
    is_disposable = is_disposable_domain(email_domain) if email_domain else False
    is_public = is_public_email_domain(email_domain) if email_domain else False
    role_based = is_role_based_email(email) if email_domain else False

    mx_found = False
    mx_details = ""
    spf_found = False
    dmarc_found = False

    if syntax_valid and email_domain and not is_disposable:
        mx_found, mx_details = lookup_mx_records(email_domain)
        if mx_found:
            spf_found = check_spf(email_domain)
            dmarc_found = check_dmarc(email_domain)

    company_domain_match: bool | None = None
    if company_domain_input:
        clean_company = clean_domain(company_domain_input)
        if clean_company:
            company_domain_match = email_domain == clean_company

    result = {
        "email": email,
        "email_domain": email_domain,
        "syntax_valid": syntax_valid,
        "mx_found": mx_found,
        "mx_details": mx_details,
        "spf_found": spf_found,
        "dmarc_found": dmarc_found,
        "is_public_email": is_public,
        "is_disposable": is_disposable,
        "is_role_based": role_based,
        "company_domain_match": company_domain_match,
    }

    score, status, notes = calculate_verification_score(result)
    result["score"] = score
    result["status"] = status
    result["notes"] = notes

    return result


def render_domain_verification() -> None:
    st.subheader("Domain & Email Verification")
    st.write(
        "Upload a CSV/XLSX file with email addresses. "
        "Optionally provide a company domain column for company-domain matching."
    )

    uploaded_file = st.file_uploader(
        "Upload Excel or CSV file", type=["xlsx", "csv"], key="domain_verifier"
    )

    if uploaded_file:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)
            else:
                df = pd.read_excel(uploaded_file, dtype=str, keep_default_na=False)

            df = df.fillna("")

            st.subheader("Uploaded Data Preview")
            st.dataframe(df.head())

            columns = list(df.columns)
            email_col = st.selectbox("Select the email column", columns)
            company_col = st.selectbox(
                "Select the company domain column (optional)",
                [""] + columns,
                index=0,
            )

            if st.button("Verify Emails"):
                total = len(df)
                progress_bar = st.progress(0)
                status_text = st.empty()

                results = []
                for idx, row in df.iterrows():
                    email = str(row.get(email_col, "")).strip()
                    company_domain = (
                        str(row.get(company_col, "")).strip()
                        if company_col
                        else None
                    )
                    status_text.text(
                        f"Verifying {idx + 1} of {total}: {email or '(empty)'}"
                    )
                    result = verify_email_row(email, company_domain)

                    results.append(
                        {
                            "Email": result["email"],
                            "Email Domain": result["email_domain"],
                            "Clean Company Domain": clean_domain(company_domain) if company_domain else "",
                            "Syntax Valid": "Yes" if result["syntax_valid"] else "No",
                            "MX Records": result["mx_details"] if result["mx_found"] else "Not Found",
                            "SPF Found": "Yes" if result["spf_found"] else "No",
                            "DMARC Found": "Yes" if result["dmarc_found"] else "No",
                            "Public Email": "Yes" if result["is_public_email"] else "No",
                            "Disposable Email": "Yes" if result["is_disposable"] else "No",
                            "Role Based Email": "Yes" if result["is_role_based"] else "No",
                            "Company Domain Match": (
                                "Yes" if result["company_domain_match"] is True
                                else "No" if result["company_domain_match"] is False
                                else "N/A"
                            ),
                            "Verification Score": result["score"],
                            "Verification Status": result["status"],
                            "Notes": result["notes"],
                        }
                    )

                    progress_bar.progress((idx + 1) / total)

                result_df = pd.DataFrame(results)
                status_text.success("Verification complete.")

                st.subheader("Results")
                st.dataframe(result_df, hide_index=True)

                output = BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    result_df.to_excel(writer, index=False, sheet_name="Verification Results")
                excel_bytes = output.getvalue()

                col_a, col_b = st.columns(2)
                with col_a:
                    st.download_button(
                        "Download Excel",
                        data=excel_bytes,
                        file_name="email_verification_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                with col_b:
                    st.download_button(
                        "Download CSV",
                        data=result_df.to_csv(index=False).encode("utf-8"),
                        file_name="email_verification_results.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

        except Exception as e:
            st.error(f"File processing failed: {e}")
