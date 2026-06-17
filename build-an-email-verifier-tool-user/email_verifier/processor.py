from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from email_verifier.dns_checks import DnsVerifier, empty_domain_verification
from email_verifier.email_checks import (
    extract_domain,
    normalize_email,
    validate_email_format,
)
from email_verifier.io import ColumnMapping, clean_cell
from email_verifier.linkedin import build_linkedin_search_url
from email_verifier.scoring import build_notes, calculate_verification_score


ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class VerificationOptions:
    linkedin_scope: str = "profiles"
    dns_timeout: float = 3.0


OUTPUT_COLUMNS = [
    "Name",
    "Company Name",
    "Email",
    "Domain",
    "MX Status",
    "SPF Status",
    "DMARC Status",
    "Email Format Valid/Invalid",
    "LinkedIn Search URL",
    "Verification Score",
    "Notes",
]


def process_dataframe(
    dataframe: pd.DataFrame,
    mapping: ColumnMapping,
    options: VerificationOptions | None = None,
    progress_callback: ProgressCallback | None = None,
) -> pd.DataFrame:
    if mapping.email not in dataframe.columns:
        raise ValueError("The selected email column was not found in the uploaded file.")
    if mapping.name and mapping.name not in dataframe.columns:
        raise ValueError("The selected name column was not found in the uploaded file.")
    if mapping.company and mapping.company not in dataframe.columns:
        raise ValueError("The selected company column was not found in the uploaded file.")

    resolved_options = options or VerificationOptions()
    dns_verifier = DnsVerifier(timeout=resolved_options.dns_timeout)
    total_rows = len(dataframe)
    output_rows: list[dict[str, object]] = []

    for processed_count, (_, row) in enumerate(dataframe.iterrows(), start=1):
        name = clean_cell(row.get(mapping.name, "")) if mapping.name else ""
        company = clean_cell(row.get(mapping.company, "")) if mapping.company else ""
        email = normalize_email(row.get(mapping.email, ""))
        format_valid, format_reason = validate_email_format(email)
        domain = extract_domain(email)

        dns_result = (
            dns_verifier.verify_domain(domain)
            if domain
            else empty_domain_verification(domain)
        )
        linkedin_url = build_linkedin_search_url(
            name=name,
            company=company,
            scope=resolved_options.linkedin_scope,
        )
        score = calculate_verification_score(format_valid, dns_result)
        notes = build_notes(
            format_valid=format_valid,
            format_reason=format_reason,
            dns_result=dns_result,
            name=name,
            company=company,
        )

        output_rows.append(
            {
                "Name": name,
                "Company Name": company,
                "Email": email,
                "Domain": domain,
                "MX Status": dns_result.mx.status,
                "SPF Status": dns_result.spf.status,
                "DMARC Status": dns_result.dmarc.status,
                "Email Format Valid/Invalid": "Valid" if format_valid else "Invalid",
                "LinkedIn Search URL": linkedin_url,
                "Verification Score": score,
                "Notes": notes,
            }
        )

        if progress_callback:
            progress_callback(processed_count, total_rows)

    return pd.DataFrame(output_rows, columns=OUTPUT_COLUMNS)
