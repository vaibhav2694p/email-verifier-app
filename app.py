from __future__ import annotations

from datetime import datetime

import streamlit as st

from email_verifier.enhanced_verifier import verify_single_email
from email_verifier.io import (
    ColumnMapping,
    get_default_column_index,
    infer_column,
    read_uploaded_table,
)
from email_verifier.processor import VerificationOptions, process_dataframe

st.set_page_config(page_title="Email Verifier", page_icon="@", layout="wide")


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
        st.caption(
            "Performs format, domain, professional, and mailbox checks in real time."
        )

    if not verify_clicked:
        return

    with st.spinner("Verifying email..."):
        result = verify_single_email(email_input)

    st.markdown("---")
    st.markdown(f"### Email Verification Results")
    st.markdown(f"📧 **Email:** `{result.email}`")

    overall_icon = "✅" if result.overall_valid else "❌"
    overall_color = "green" if result.overall_valid else "red"
    st.markdown(
        f"### {overall_icon} Overall Status: "
        f"<span style='color:{overall_color}'>{'VALID' if result.overall_valid else 'INVALID'}</span>",
        unsafe_allow_html=True,
    )

    st.markdown("━━━━━━━━━━━━━━━━━━━━")

    checks = [
        ("Format", result.format_check),
        ("Professional", result.professional_check),
        ("Domain Status", result.domain_check),
        ("Mailbox", result.mailbox_check),
    ]

    for label, check in checks:
        icon = "✅" if check.valid else ("⚠️" if "Unable" in check.status else "❌")
        status_color = "green" if check.valid else ("orange" if "Unable" in check.status else "red")
        st.markdown(
            f"{icon} **{label}**  \n"
            f"Status: <span style='color:{status_color}'>{check.status}</span>  \n"
            f"{check.details}",
            unsafe_allow_html=True,
        )
        st.markdown("")

    st.markdown("━━━━━━━━━━━━━━━━━━━━")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown(f"**Verification Date:** {result.verification_date}")
    with col_b:
        st.markdown(f"**Verification Time:** {result.verification_time}")
    with col_c:
        result_label = result.result
        if result_label == "Deliverable":
            st.markdown(f"**Result:** 🟢 {result_label}")
        elif result_label == "Risky":
            st.markdown(f"**Result:** 🟡 {result_label}")
        else:
            st.markdown(f"**Result:** 🔴 {result_label}")

    st.markdown("")

    if result.overall_valid:
        st.success("🟢 Safe to Send Emails")
    elif result.result == "Risky":
        st.warning("🟡 Risky - Proceed with Caution")
    else:
        st.error("🔴 Undeliverable - Do not send")

    st.markdown("---")
    st.markdown("### Advanced Details")

    tabs = st.tabs(["Name Detection", "Domain Info", "Provider Info", "Score Breakdown"])

    with tabs[0]:
        st.markdown(f"**First Name:** {result.first_name or 'N/A'} {'✓' if result.first_name else ''}")
        st.markdown(f"**Last Name:** {result.last_name or 'N/A'} {'✓' if result.last_name else ''}")
        st.markdown(f"**Full Name:** {result.full_name or 'N/A'}")
        role_str = "⚠️ Yes - This appears to be a generic/role account" if result.role_account else "✅ No - This is not a role account"
        st.markdown(f"**Role Account:** {role_str}")

    with tabs[1]:
        st.markdown(f"**Domain:** `{result.domain}`")
        mx_str = "✅ Available ✓" if result.mx_records_available else "❌ Not Available"
        st.markdown(f"**MX Records:** {mx_str}")
        catch_all_str = (
            "⚠️ Yes - Domain accepts all emails"
            if result.catch_all is True
            else ("✅ No" if result.catch_all is False else "N/A")
        )
        st.markdown(f"**Catch-All:** {catch_all_str}")

    with tabs[2]:
        provider_str = "🏢 Business" if result.provider_type == "Business" else "📧 Free Email Provider"
        st.markdown(f"**Provider Type:** {provider_str}")
        disposable_str = "❌ Yes - Disposable/temporary" if result.disposable_email else "✅ No ✓"
        st.markdown(f"**Disposable Email:** {disposable_str}")

    with tabs[3]:
        score_color = "green" if result.score >= 70 else ("orange" if result.score >= 40 else "red")
        st.markdown(
            f"### <span style='color:{score_color}'>{result.score}/100</span>",
            unsafe_allow_html=True,
        )
        format_pts = 25 if result.format_check.valid else 0
        domain_pts = 25 if result.domain_check.valid else 0
        prof_pts = 20 if result.professional_check.valid else 0
        mailbox_pts = 30 if result.mailbox_check.valid else 0
        st.markdown(f"- Format: {format_pts}/25")
        st.markdown(f"- Domain: {domain_pts}/25")
        st.markdown(f"- Professional: {prof_pts}/20")
        st.markdown(f"- Mailbox: {mailbox_pts}/30")
        total_check = format_pts + domain_pts + prof_pts + mailbox_pts
        if total_check != result.score:
            st.markdown(f"- **Total: {result.score}/100**")


def render_bulk_verification() -> None:
    st.subheader("Bulk CSV / XLSX Verification")

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

    uploaded_file = st.file_uploader("Upload CSV or XLSX", type=["csv", "xlsx"])
    if uploaded_file is None:
        return

    try:
        dataframe = read_uploaded_table(uploaded_file)
    except ValueError as exc:
        st.error(str(exc))
        return

    columns = list(dataframe.columns)
    email_guess = infer_column(columns, "email")
    name_guess = infer_column(columns, "name")
    company_guess = infer_column(columns, "company")

    mapping_cols = st.columns(3)
    with mapping_cols[0]:
        email_column = st.selectbox(
            "Email column",
            options=[""] + columns,
            index=get_default_column_index(columns, email_guess),
        )
    with mapping_cols[1]:
        name_column = st.selectbox(
            "Name column",
            options=[""] + columns,
            index=get_default_column_index(columns, name_guess),
        )
    with mapping_cols[2]:
        company_column = st.selectbox(
            "Company column",
            options=[""] + columns,
            index=get_default_column_index(columns, company_guess),
        )

    st.dataframe(dataframe.head(25), width="stretch", hide_index=True)

    if not email_column:
        st.error("Select an email column before verification.")
        return

    run_clicked = st.button("Verify emails", type="primary")
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
        result = process_dataframe(
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

    status_text.write(f"Verified {len(result)} rows")
    st.success("Verification complete.")

    def highlight_rows(row: object) -> list[str]:
        row_dict = dict(row)
        email_format = str(row_dict.get("Email Format Valid/Invalid", ""))
        is_invalid = email_format.lower() != "valid"
        bg = "background-color: #ffcccc" if is_invalid else ""
        return [bg] * len(row_dict)

    styled = result.style.apply(highlight_rows, axis=1)
    st.dataframe(styled, width="stretch", hide_index=True)

    csv_bytes = result.to_csv(index=False).encode("utf-8")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name=f"email_verification_results_{timestamp}.csv",
        mime="text/csv",
    )


def render_app() -> None:
    st.title("Email Verifier")

    tab1, tab2 = st.tabs(["🔍 Single Verification", "📊 Bulk Upload"])

    with tab1:
        render_single_verification()

    with tab2:
        render_bulk_verification()


if __name__ == "__main__":
    render_app()
