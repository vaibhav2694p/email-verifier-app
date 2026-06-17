from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from email_verifier.enhanced_verifier import FINAL_STATUS_MAP, verify_single_email
from email_verifier.io import ColumnMapping, clean_cell


ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class VerificationOptions:
    linkedin_scope: str = "profiles"
    dns_timeout: float = 3.0


OUTPUT_COLUMNS = [
    "Email Address",
    "First Name",
    "Last Name",
    "Format Status",
    "Domain Status",
    "MX Record",
    "SMTP Status",
    "Catch-All",
    "Disposable",
    "Role Account",
    "Duplicate",
    "Company Website",
    "Email Score",
    "SMTP Response",
    "LinkedIn URL",
    "Verification Date",
    "Verification Source",
    "MillionVerifier Result",
    "Mail Validation Status",
    "Final Status",
    "Send Decision",
]


def process_dataframe(
    dataframe: pd.DataFrame,
    mapping: ColumnMapping,
    options: VerificationOptions | None = None,
    progress_callback: ProgressCallback | None = None,
) -> pd.DataFrame:
    if mapping.email not in dataframe.columns:
        raise ValueError("The selected email column was not found in the uploaded file.")

    mv_result_col = "result" if "result" in dataframe.columns else None
    mv_mail_status_col = "Mail Validation Status" if "Mail Validation Status" in dataframe.columns else None

    total_rows = len(dataframe)
    output_rows: list[dict[str, object]] = []
    seen_emails: set[str] = set()

    for processed_count, (_, row) in enumerate(dataframe.iterrows(), start=1):
        email_raw = clean_cell(row.get(mapping.email, ""))
        if not email_raw:
            output_rows.append(_empty_row(email_raw))
            if progress_callback:
                progress_callback(processed_count, total_rows)
            continue

        try:
            result = verify_single_email(email_raw, seen_emails)
            output_row = _result_to_row(result)
        except Exception:
            output_row = _empty_row(email_raw)

        output_row["MillionVerifier Result"] = str(row.get(mv_result_col, "")) if mv_result_col else ""
        output_row["Mail Validation Status"] = str(row.get(mv_mail_status_col, "")) if mv_mail_status_col else ""

        output_row["Final Status"] = _determine_mv_final_status(
            output_row,
            str(output_row["MillionVerifier Result"]),
            str(output_row["Mail Validation Status"]),
        )
        output_row["Send Decision"] = FINAL_STATUS_MAP.get(
            str(output_row["Final Status"]), "⚠️ Unknown"
        )

        output_rows.append(output_row)

        if progress_callback:
            progress_callback(processed_count, total_rows)

    return pd.DataFrame(output_rows, columns=OUTPUT_COLUMNS)


def _determine_mv_final_status(
    output_row: dict[str, object],
    mv_result: str,
    mv_mail_status: str,
) -> str:
    mv_result = mv_result.strip().lower()
    mv_mail_status = mv_mail_status.strip().lower()

    if mv_result == "ok" or mv_mail_status == "valid":
        return "OK"
    if mv_result == "catch_all" or mv_mail_status == "risky":
        return "Catch-All"
    if mv_result in ("invalid", "bad") or mv_mail_status == "invalid":
        return "Invalid"
    if mv_result == "disposable":
        return "Disposable"

    is_duplicate = str(output_row.get("Duplicate", "No")) == "Yes"
    syntax_valid = str(output_row.get("Format Status", "")) == "Valid"
    domain_valid = str(output_row.get("Domain Status", "")) == "Valid"
    mx_found = str(output_row.get("MX Record", "")) == "Found"
    is_disposable = str(output_row.get("Disposable", "No")) == "Yes"
    is_catchall = str(output_row.get("Catch-All", "")) == "Yes"
    smtp = str(output_row.get("SMTP Status", "")).strip().lower()

    if is_duplicate:
        return "Duplicate"
    if not syntax_valid:
        return "Invalid"
    if not domain_valid or not mx_found:
        return "Invalid"
    if is_disposable:
        return "Disposable"
    if is_catchall:
        return "Catch-All"

    if smtp in ("exists", "mailbox_exists"):
        return "OK"
    return "Unknown"


def _result_to_row(result: object) -> dict[str, object]:
    from email_verifier.enhanced_verifier import EnhancedVerificationResult
    r = result
    if not isinstance(r, EnhancedVerificationResult):
        return _empty_row(getattr(r, "email", ""))
    return {
        "Email Address": r.email,
        "First Name": r.first_name or "Not Found",
        "Last Name": r.last_name or "Not Found",
        "Format Status": "Valid" if r.format_check.valid else "Invalid",
        "Domain Status": "Valid" if r.domain_exists else "Domain Not Found",
        "MX Record": "Found" if r.mx_records_available else "Missing",
        "SMTP Status": r.smtp_status or "Unknown",
        "Catch-All": "Yes" if r.catch_all is True else ("No" if r.catch_all is False else "N/A"),
        "Disposable": "Yes" if r.disposable_email else "No",
        "Role Account": "Yes" if r.role_account else "No",
        "Duplicate": "Yes" if r.is_duplicate else "No",
        "Company Website": r.domain or "Not Found",
        "Email Score": r.score,
        "SMTP Response": r.smtp_response or "N/A",
        "LinkedIn URL": r.linkedin_url or "",
        "Verification Date": f"{r.verification_date} {r.verification_time}",
        "Verification Source": r.verification_source,
        "MillionVerifier Result": "",
        "Mail Validation Status": "",
        "Final Status": r.final_status,
        "Send Decision": r.send_decision,
    }


def _empty_row(email: str) -> dict[str, object]:
    return {
        "Email Address": email,
        "First Name": "Not Found",
        "Last Name": "Not Found",
        "Format Status": "Invalid",
        "Domain Status": "Invalid",
        "MX Record": "Missing",
        "SMTP Status": "Unknown",
        "Catch-All": "N/A",
        "Disposable": "N/A",
        "Role Account": "N/A",
        "Duplicate": "No",
        "Company Website": "Not Found",
        "Email Score": 0,
        "SMTP Response": "N/A",
        "LinkedIn URL": "",
        "Verification Date": "",
        "Verification Source": "Real-Time",
        "MillionVerifier Result": "",
        "Mail Validation Status": "",
        "Final Status": "Invalid",
        "Send Decision": "❌ Do not send",
    }
