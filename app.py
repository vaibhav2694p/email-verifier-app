from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from email_verifier.enhanced_verifier import FINAL_STATUS_MAP, verify_single_email
from email_verifier.export_utils import (
    dataframe_to_csv_bytes,
    dataframe_to_pdf_bytes,
    dataframe_to_xlsx_bytes,
    dataframe_to_xlsx_preserve,
    dataframe_valid_xlsx_bytes,
    dataframe_risky_xlsx_bytes,
    dataframe_invalid_xlsx_bytes,
)
from email_verifier.domain_provider import render_domain_provider_checker
from email_verifier.new_verifier import render_domain_verification
from email_verifier.io import (
    ColumnMapping,
    get_default_column_index,
    infer_column,
    read_uploaded_table_all_sheets,
)
from email_verifier.processor import VerificationOptions, process_dataframe

st.set_page_config(page_title="Email Verifier", page_icon="@", layout="wide")

STATUS_COL = "Final Status"

STATUS_UI = {
    "OK": ("🟢", "green", "✅ Send"),
    "Catch-All": ("🟡", "orange", "⚠️ Send carefully"),
    "Risky": ("🟡", "orange", "⚠️ Review first"),
    "Invalid": ("🔴", "red", "❌ Do not send"),
    "Disposable": ("🔴", "red", "❌ Do not send"),
    "Unknown": ("🟠", "orange", "⚠️ Usually avoid"),
    "Duplicate": ("⬜", "gray", "Remove"),
}


def render_single_verification() -> None:
    st.subheader("Real-Time Email Verification")
    email_input = st.text_input(
        "Enter an email address to verify",
        placeholder="e.g. name@company.com",
    )

    if not email_input:
        return

    col1, col2 = st.columns([1, 5])
    with col1:
        verify_clicked = st.button("Verify Email", type="primary")
    with col2:
        st.caption("Syntax, domain, MX, disposable, role, catch-all, and SMTP checks.")

    if not verify_clicked:
        return

    with st.spinner("Verifying email..."):
        result = verify_single_email(email_input)

    st.markdown("---")
    st.markdown(f"### Email Verification Results")
    st.markdown(f"📧 **Email:** `{result.email}`")

    icon, color, decision = STATUS_UI.get(
        result.final_status, ("❓", "gray", "Unknown")
    )
    st.markdown(
        f"### {icon} Final Status: "
        f"<span style='color:{color}'>{result.final_status}</span>  \n"
        f"**{decision}**",
        unsafe_allow_html=True,
    )

    st.markdown("━━━━━━━━━━━━━━━━━━━━")

    checks_table = [
        ("Format Status", result.format_check.status, "Valid" == result.format_check.status),
        ("Domain Status", "Valid" if result.domain_exists else "Domain Not Found", result.domain_exists),
        ("MX Record", "Found" if result.mx_records_available else "Missing", result.mx_records_available),
        ("Mailbox", result.smtp_status or "Unknown", result.smtp_status == "Exists"),
        ("Catch-All", "Yes" if result.catch_all is True else "No", result.catch_all is not True),
        ("Disposable", "Yes" if result.disposable_email else "No", not result.disposable_email),
        ("Role Account", "Yes" if result.role_account else "No", not result.role_account),
        ("Duplicate", "Yes" if result.is_duplicate else "No", not result.is_duplicate),
    ]

    for label, status_text, is_good in checks_table:
        if status_text in ("Valid", "Found", "Exists", "No"):
            icon_c = "✅"
            c = "green"
        elif status_text in ("Invalid", "Missing", "Not Found", "Yes", "Blocked"):
            icon_c = "❌"
            c = "red"
        else:
            icon_c = "⚠️"
            c = "orange"
        st.markdown(
            f"{icon_c} **{label}:** "
            f"<span style='color:{c}'>{status_text}</span>",
            unsafe_allow_html=True,
        )

    st.markdown("")
    st.markdown(f"**Send Decision:** {result.send_decision}")
    st.markdown("━━━━━━━━━━━━━━━━━━━━")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown(f"**Verification Date:** {result.verification_date}")
    with col_b:
        st.markdown(f"**Verification Time:** {result.verification_time}")
    with col_c:
        st.markdown(f"**Score:** {result.score}/100")

    st.markdown("")
    if result.final_status == "OK":
        st.success("🟢 Safe to Send Emails")
    elif result.final_status in ("Catch-All", "Risky", "Unknown"):
        st.warning("🟡 Proceed with Caution")
    else:
        st.error("🔴 Do not send")

    st.markdown("---")
    st.markdown("### Advanced Details")
    tabs = st.tabs(["Name Detection", "Domain Info", "Provider Info", "Score Breakdown"])

    with tabs[0]:
        st.markdown(f"**First Name:** {result.first_name or 'N/A'} {'✓' if result.first_name else ''}")
        st.markdown(f"**Last Name:** {result.last_name or 'N/A'} {'✓' if result.last_name else ''}")
        st.markdown(f"**Full Name:** {result.full_name or 'N/A'}")
        role_str = "⚠️ Yes - Role account" if result.role_account else "✅ No - Not a role account"
        st.markdown(f"**Role Account:** {role_str}")

    with tabs[1]:
        st.markdown(f"**Domain:** `{result.domain}`")
        mx_str = "✅ Found" if result.mx_records_available else "❌ Missing"
        st.markdown(f"**MX Record:** {mx_str}")
        catch_all_str = (
            "⚠️ Yes" if result.catch_all is True
            else ("✅ No" if result.catch_all is False else "N/A")
        )
        st.markdown(f"**Catch-All:** {catch_all_str}")

    with tabs[2]:
        provider_str = "🏢 Business" if result.provider_type == "Business" else "📧 Free Email Provider"
        st.markdown(f"**Provider Type:** {provider_str}")
        disposable_str = "❌ Yes" if result.disposable_email else "✅ No"
        st.markdown(f"**Disposable Email:** {disposable_str}")

    with tabs[3]:
        score_color = "green" if result.score >= 70 else ("orange" if result.score >= 40 else "red")
        st.markdown(
            f"### <span style='color:{score_color}'>{result.score}/100</span>",
            unsafe_allow_html=True,
        )
        st.markdown(f"- Format: {25 if result.format_check.valid else 0}/25")
        st.markdown(f"- Domain: {20 if result.domain_exists else 0}/20")
        st.markdown(f"- MX Record: {20 if result.mx_records_available else 0}/20")
        st.markdown(f"- Professional: {10 if not result.disposable_email else 0}/10")
        st.markdown(f"- Mailbox: {25 if result.smtp_status == 'Exists' else (10 if result.smtp_status in ('Blocked', 'Unknown') else 0)}/25")


def render_bulk_verification() -> None:
    st.subheader("Bulk Email Verification Upload")
    st.markdown("Upload **CSV**, **XLSX**, or **TXT** files containing email addresses.")

    with st.sidebar:
        linkedin_scope_label = st.radio(
            "LinkedIn search",
            options=["Profiles only", "All LinkedIn"],
            index=0,
        )
        dns_timeout = st.slider(
            "DNS timeout",
            min_value=1.0,
            max_value=10.0,
            value=3.0,
            step=0.5,
        )

    uploaded_file = st.file_uploader("Choose a file", type=["csv", "xlsx", "txt"])
    if uploaded_file is None:
        return

    try:
        dataframe, original_sheets = read_uploaded_table_all_sheets(uploaded_file)
    except ValueError as exc:
        st.error(str(exc))
        return

    columns = list(dataframe.columns)
    email_guess = infer_column(columns, "email")
    use_simple_mode = columns == ["Email"]

    if use_simple_mode:
        email_column = "Email"
        name_column = ""
        company_column = ""
        st.info("TXT file detected — treating each line as an email address.")
    else:
        name_guess = infer_column(columns, "name")
        company_guess = infer_column(columns, "company")
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            email_column = st.selectbox(
                "Email column",
                options=[""] + columns,
                index=get_default_column_index(columns, email_guess),
            )
        with mc2:
            name_column = st.selectbox(
                "Name column",
                options=[""] + columns,
                index=get_default_column_index(columns, name_guess),
            )
        with mc3:
            company_column = st.selectbox(
                "Company column",
                options=[""] + columns,
                index=get_default_column_index(columns, company_guess),
            )

    st.dataframe(dataframe.head(25), width="stretch", hide_index=True)
    st.caption(f"Showing first 25 of {len(dataframe)} rows")

    if not email_column:
        st.error("Select an email column before verification.")
        return

    run_clicked = st.button("Verify Emails", type="primary")
    if not run_clicked:
        return

    mapping = ColumnMapping(
        email=email_column,
        name=name_column or None,
        company=company_column or None,
    )
    options = VerificationOptions(
        linkedin_scope="profiles" if linkedin_scope_label == "Profiles only" else "all",
        dns_timeout=dns_timeout,
    )

    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(done: int, total: int) -> None:
        progress_bar.progress(done / total if total else 1.0)
        status_text.write(f"Verified {done} of {total} rows")

    try:
        result_df = process_dataframe(
            dataframe,
            mapping=mapping,
            options=options,
            progress_callback=update_progress,
        )
    except ValueError as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.error(f"Verification failed: {exc}")
        return

    status_text.write(f"Verified {len(result_df)} rows")
    st.success("Verification complete.")

    total = len(result_df)
    ok_count = int((result_df[STATUS_COL] == "OK").sum())
    catchall_count = int((result_df[STATUS_COL] == "Catch-All").sum())
    risky_count = int((result_df[STATUS_COL] == "Risky").sum())
    invalid_count = int((result_df[STATUS_COL] == "Invalid").sum())
    disposable_count = int((result_df[STATUS_COL] == "Disposable").sum())
    unknown_count = int((result_df[STATUS_COL] == "Unknown").sum())
    duplicate_count = int((result_df[STATUS_COL] == "Duplicate").sum())

    st.markdown("---")
    st.markdown("### Bulk Upload Summary")

    sm1, sm2, sm3, sm4, sm5 = st.columns(5)
    with sm1:
        st.metric("Total", f"{total:,}")
    with sm2:
        st.markdown("🟢 **OK**")
        st.markdown(f"<p style='color:green;font-size:1.3rem;font-weight:bold'>{ok_count:,}</p>", unsafe_allow_html=True)
    with sm3:
        st.markdown("🟡 **Risky/Catch-All**")
        st.markdown(f"<p style='color:orange;font-size:1.3rem;font-weight:bold'>{catchall_count + risky_count:,}</p>", unsafe_allow_html=True)
    with sm4:
        st.markdown("🔴 **Invalid/Disposable**")
        st.markdown(f"<p style='color:red;font-size:1.3rem;font-weight:bold'>{invalid_count + disposable_count:,}</p>", unsafe_allow_html=True)
    with sm5:
        st.markdown("🟠 **Unknown**")
        st.markdown(f"<p style='color:orange;font-size:1.3rem;font-weight:bold'>{unknown_count:,}</p>", unsafe_allow_html=True)

    if duplicate_count > 0:
        st.caption(f"⬜ Duplicates removed: {duplicate_count:,}")

    st.markdown("---")
    st.markdown("### Detailed Results")

    def highlight(val: object) -> str:
        s = str(val)
        if s == "OK":
            return "background-color:#d4edda;color:#155724"
        if s in ("Catch-All", "Risky"):
            return "background-color:#fff3cd;color:#856404"
        if s in ("Invalid", "Disposable"):
            return "background-color:#f8d7da;color:#721c24"
        if s == "Unknown":
            return "background-color:#ffd8a8;color:#8a4a00"
        if s == "Duplicate":
            return "background-color:#e2e3e5;color:#383d41"
        if s in ("Valid", "Found", "Exists", "No"):
            return "background-color:#d4edda;color:#155724"
        if s in ("Invalid", "Missing", "Not Found", "Yes", "Blocked"):
            return "background-color:#f8d7da;color:#721c24"
        return ""

    hl_cols = [STATUS_COL, "Format Status", "Domain Status", "MX Record",
               "SMTP Status", "Disposable", "Role Account", "Duplicate",
               "First Name", "Last Name"]
    valid_cols = [c for c in hl_cols if c in result_df.columns]
    styled_df = result_df.style.applymap(highlight, subset=valid_cols)

    st.dataframe(styled_df, width="stretch", hide_index=True)

    st.markdown("---")
    st.markdown("### Per-Email Detailed View")

    email_list = result_df["Email Address"].tolist()
    selected_email = st.selectbox("Select an email to view details", options=email_list)
    if selected_email:
        row = result_df[result_df["Email Address"] == selected_email].iloc[0]
        fs = str(row.get(STATUS_COL, ""))

        icon_c, color_c, decision_c = STATUS_UI.get(fs, ("❓", "gray", ""))
        st.markdown(f"### {icon_c} {fs} — {selected_email}")

        checks = [
            ("Format", "Format Status", "Valid"),
            ("Domain Status", "Domain Status", "Valid"),
            ("MX Record", "MX Record", "Found"),
            ("Mailbox", "SMTP Status", "Exists"),
            ("Catch-All", "Catch-All", "No"),
            ("Disposable", "Disposable", "No"),
            ("Role Account", "Role Account", "No"),
            ("Duplicate", "Duplicate", "No"),
        ]
        for label, key, good_val in checks:
            val = str(row.get(key, ""))
            is_good = val == good_val
            icon_c2 = "✅" if is_good else "❌"
            c2 = "green" if is_good else "red"
            st.markdown(f"{icon_c2} **{label}:** <span style='color:{c2}'>{val}</span>", unsafe_allow_html=True)

        st.markdown("")
        st.markdown(f"**Send Decision:** {decision_c}")

        fn = str(row.get("First Name", ""))
        ln = str(row.get("Last Name", ""))
        score_v = int(row.get("Email Score", 0))
        date_v = str(row.get("Verification Date", ""))
        smtp_v = str(row.get("SMTP Response", ""))

        c1, c2, c3 = st.columns(3)
        with c1:
            sc = "green" if score_v >= 70 else ("orange" if score_v >= 40 else "red")
            st.markdown(f"**Score:** <span style='color:{sc}'>{score_v}/100</span>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"**Name:** {fn} {ln}".strip())
        with c3:
            st.markdown(f"**SMTP:** {smtp_v[:40]}")

        st.caption(f"Verified: {date_v}")

    st.markdown("---")
    st.markdown("### Export Options")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"email_verification_report_{timestamp}"

    exp_tabs = st.tabs(["📥 Full Report", "📥 Filtered Exports"])

    with exp_tabs[0]:
        e1, e2, e3 = st.columns(3)
        with e1:
            st.download_button(
                "📄 Download CSV", data=dataframe_to_csv_bytes(result_df),
                file_name=f"{base}.csv", mime="text/csv", use_container_width=True,
            )
        with e2:
            xlsx_bytes = (
                dataframe_to_xlsx_preserve(original_sheets, result_df)
                if original_sheets is not None
                else dataframe_to_xlsx_bytes(result_df)
            )
            st.download_button(
                "📗 Download Full Report (XLSX)", data=xlsx_bytes,
                file_name=f"{base}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with e3:
            try:
                st.download_button(
                    "📕 Download PDF Report", data=dataframe_to_pdf_bytes(result_df),
                    file_name=f"{base}.pdf", mime="application/pdf", use_container_width=True,
                )
            except Exception as exc:
                st.error(f"PDF failed: {exc}")

    with exp_tabs[1]:
        f1, f2, f3 = st.columns(3)
        has_ok = ok_count > 0
        has_risky = (catchall_count + risky_count) > 0
        has_bad = (invalid_count + disposable_count) > 0
        with f1:
            if has_ok:
                st.download_button(
                    "🟢 OK Emails (XLSX)", data=dataframe_valid_xlsx_bytes(result_df),
                    file_name=f"OK_Emails_{timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            else:
                st.button("🟢 OK Emails", disabled=True, use_container_width=True)
        with f2:
            if has_risky:
                st.download_button(
                    "🟡 Risky/Catch-All (XLSX)", data=dataframe_risky_xlsx_bytes(result_df),
                    file_name=f"Risky_Emails_{timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            else:
                st.button("🟡 Risky/Catch-All", disabled=True, use_container_width=True)
        with f3:
            if has_bad:
                st.download_button(
                    "🔴 Invalid/Disposable (XLSX)", data=dataframe_invalid_xlsx_bytes(result_df),
                    file_name=f"Invalid_Emails_{timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            else:
                st.button("🔴 Invalid/Disposable", disabled=True, use_container_width=True)


def render_app() -> None:
    st.title("Email Verifier")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Single Verification",
        "📊 Bulk Upload",
        "🌐 Domain Provider Checker",
        "✅ Domain & Email Verification",
    ])

    with tab1:
        render_single_verification()

    with tab2:
        render_bulk_verification()

    with tab3:
        render_domain_provider_checker()

    with tab4:
        render_domain_verification()


if __name__ == "__main__":
    render_app()
