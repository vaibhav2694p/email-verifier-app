from __future__ import annotations

import re
from io import BytesIO

import dns.resolver
import pandas as pd
import streamlit as st

PROVIDER_PATTERNS = {
    "Google Workspace": ["google.com", "googlemail.com", "aspmx.l.google.com"],
    "Microsoft 365 / Outlook": ["outlook.com", "protection.outlook.com", "office365.com", "microsoft.com"],
    "Zoho Mail": ["zoho.com", "zohomail.com"],
    "Yahoo / AOL": ["yahoo.com", "yahoodns.net", "aol.com"],
    "Fastmail": ["fastmail.com", "messagingengine.com"],
    "Proton Mail": ["protonmail.ch", "protonmail.com", "proton.me"],
    "GoDaddy": ["secureserver.net", "godaddy.com"],
    "Namecheap": ["privateemail.com", "namecheap.com"],
    "Rackspace": ["emailsrvr.com", "rackspace.com"],
}


def clean_domain(domain: str) -> str:
    if pd.isna(domain):
        return ""
    domain = str(domain).strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = re.sub(r"^www\.", "", domain)
    domain = domain.split("/")[0]
    domain = domain.split(":")[0]
    domain = domain.strip()
    if not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", domain):
        return ""
    return domain


def lookup_mx_records(domain: str) -> str:
    if not domain:
        return "Invalid Domain"
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        mx_records = sorted(
            [f"{r.preference} {str(r.exchange).rstrip('.')}" for r in answers]
        )
        if not mx_records:
            return "No MX Found"
        return ", ".join(mx_records)
    except dns.resolver.NXDOMAIN:
        return "Invalid Domain"
    except dns.resolver.NoAnswer:
        return "No MX Found"
    except dns.resolver.NoNameservers:
        return "DNS Error"
    except dns.exception.Timeout:
        return "DNS Timeout"
    except Exception as e:
        return f"Lookup Failed: {str(e)}"


def detect_email_provider(mx_records: str) -> str:
    if mx_records in ("No MX Found", "Invalid Domain", "DNS Error", "DNS Timeout"):
        return mx_records if mx_records == "No MX Found" else "Other / Unknown"
    mx_lower = str(mx_records).lower()
    for provider, patterns in PROVIDER_PATTERNS.items():
        if any(pattern in mx_lower for pattern in patterns):
            return provider
    return "Other / Unknown"


def process_dataframe(df: pd.DataFrame, domain_column: str) -> pd.DataFrame:
    total = len(df)
    progress_bar = st.progress(0)
    status_text = st.empty()
    mx_cache: dict[str, str] = {}

    clean_domains: list[str] = []
    mx_records_list: list[str] = []
    providers: list[str] = []

    for index, row in df.iterrows():
        raw_domain = row[domain_column]
        clean = clean_domain(raw_domain)
        status_text.text(f"Checking {index + 1} of {total}: {clean or raw_domain}")

        if clean in mx_cache:
            mx_records = mx_cache[clean]
        else:
            mx_records = lookup_mx_records(clean)
            mx_cache[clean] = mx_records

        provider = detect_email_provider(mx_records)
        clean_domains.append(clean)
        mx_records_list.append(mx_records)
        providers.append(provider)
        progress_bar.progress((index + 1) / total)

    df["Clean Domain"] = clean_domains
    df["Email Provider"] = providers
    df["MX Records"] = mx_records_list

    status_text.success("Domain checking completed.")
    return df


def render_domain_provider_checker() -> None:
    st.subheader("Domain Email Provider Checker")
    st.write("Upload a company domain list and automatically detect each company's email provider.")

    uploaded_file = st.file_uploader(
        "Upload Excel or CSV file", type=["xlsx", "csv"], key="domain_provider"
    )

    if uploaded_file:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            st.subheader("Uploaded Data Preview")
            st.dataframe(df.head())

            domain_column = st.selectbox(
                "Select the column containing company domains", df.columns
            )

            if st.button("Check Email Providers"):
                result_df = process_dataframe(df.copy(), domain_column)

                st.subheader("Verified Results")
                st.dataframe(result_df)

                output = BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    result_df.to_excel(writer, index=False, sheet_name="Verified Domains")
                excel_bytes = output.getvalue()

                st.download_button(
                    label="Download Updated Excel File",
                    data=excel_bytes,
                    file_name="verified_email_providers.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

                st.download_button(
                    label="Download Updated CSV File",
                    data=result_df.to_csv(index=False).encode("utf-8"),
                    file_name="verified_email_providers.csv",
                    mime="text/csv",
                )

        except Exception as e:
            st.error(f"File processing failed: {e}")
