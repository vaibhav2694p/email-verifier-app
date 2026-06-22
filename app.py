import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import base64
from pathlib import Path
import traceback

from utils import (
    validate_and_normalize_email,
    extract_email_domain,
    clean_domain,
    is_public_email_domain,
    is_disposable_domain,
    is_role_based_email,
    detect_email_provider,
    lookup_mx_records,
    check_domain_website,
    calculate_verification_score,
)

st.set_page_config(
    page_title="Email Verifier",
    page_icon="📧",
    layout="centered",
    initial_sidebar_state="collapsed",
)

hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


def render_center_logo(path="assets/safebooks_logo.png", width=320):
    logo_path = Path(path)
    if not logo_path.exists():
        st.warning("Logo file not found. Please add assets/safebooks_logo.png")
        return
    encoded = base64.b64encode(logo_path.read_bytes()).decode("utf-8")
    components.html(f"""
    <div style="text-align:center; margin-bottom:1rem;">
        <img src="data:image/png;base64,{encoded}" width="{width}"
             style="display:block; margin-left:auto; margin-right:auto;">
    </div>
    """, height=200)


if "processing" not in st.session_state:
    st.session_state.processing = False
if "results_df" not in st.session_state:
    st.session_state.results_df = None


def main():
    render_center_logo()
    st.title("Email Verifier")
    st.subheader(
        "Upload your email list and verify domains, MX records, providers, and website status."
    )

    uploaded_file = st.file_uploader(
        "Choose a CSV or XLSX file",
        type=["csv", "xlsx"],
        help="Upload your email list file. Must contain an email column.",
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
            return

        if df.empty:
            st.warning("The uploaded file is empty.")
            return

        email_col = st.selectbox(
            "Select the column containing emails",
            options=df.columns,
            help="Choose the column that contains email addresses",
        )

        company_domain_col = st.selectbox(
            "Select the column containing company domain (optional)",
            options=[None] + list(df.columns),
            format_func=lambda x: "None" if x is None else x,
            help="Optional: Select column with company domains for matching verification",
        )

        if st.button("Verify Emails", type="primary", use_container_width=True):
            st.session_state.processing = True
            st.session_state.results_df = None

            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                results = []
                total_rows = len(df)

                for idx, row in df.iterrows():
                    progress = (idx + 1) / total_rows
                    progress_bar.progress(progress)
                    current_email = (
                        row[email_col] if pd.notnull(row[email_col]) else ""
                    )
                    status_text.text(
                        f"Checking {idx+1} of {total_rows}: {current_email}"
                    )

                    result = process_email_row(
                        row,
                        email_column=email_col,
                        company_domain_column=company_domain_col,
                    )
                    results.append(result)

                result_df = pd.DataFrame(results)
                st.session_state.results_df = result_df

            except Exception as e:
                st.error(f"An error occurred during processing: {str(e)}")
                st.error(traceback.format_exc())
            finally:
                progress_bar.empty()
                status_text.empty()
                st.session_state.processing = False

    if (
        st.session_state.results_df is not None
        and not st.session_state.processing
    ):
        st.subheader("Verification Results")

        column_config = {
            "Email": st.column_config.TextColumn("Email", width="medium"),
            "Normalized Email": st.column_config.TextColumn(
                "Normalized Email", width="medium"
            ),
            "Domain": st.column_config.TextColumn("Domain", width="small"),
            "Domain Active": st.column_config.TextColumn(
                "Domain Active", width="small"
            ),
            "Website Status": st.column_config.TextColumn(
                "Website Status", width="small"
            ),
            "MX Status": st.column_config.TextColumn(
                "MX Status", width="small"
            ),
            "Email Provider": st.column_config.TextColumn(
                "Email Provider", width="medium"
            ),
            "Verification Status": st.column_config.TextColumn(
                "Verification Status", width="small"
            ),
            "Verification Score": st.column_config.NumberColumn(
                "Verification Score", width="small", format="%d"
            ),
            "Notes": st.column_config.TextColumn("Notes", width="large"),
        }

        st.dataframe(
            st.session_state.results_df,
            column_config=column_config,
            hide_index=True,
            use_container_width=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            excel_data = convert_df_to_excel(st.session_state.results_df)
            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name="email_verification_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with col2:
            csv_data = convert_df_to_csv(st.session_state.results_df)
            st.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name="email_verification_results.csv",
                mime="text/csv",
                use_container_width=True,
            )

    if uploaded_file is None and not st.session_state.processing:
        st.info("👆 Please upload a CSV or XLSX file to begin verification")


def process_email_row(row, email_column, company_domain_column=None):
    result = {
        "Email": "",
        "Normalized Email": "",
        "Domain": "",
        "Domain Active": "No",
        "Website Status": "Not Checked",
        "MX Status": "Not Checked",
        "Email Provider": "Unknown",
        "Verification Status": "Invalid",
        "Verification Score": 0,
        "Notes": "",
    }

    email_value = row[email_column] if pd.notnull(row[email_column]) else ""
    result["Email"] = str(email_value).strip()

    if not result["Email"]:
        result["Notes"] = "Empty email address"
        return result

    try:
        normalized_email = validate_and_normalize_email(result["Email"])
        result["Normalized Email"] = normalized_email
    except Exception as e:
        result["Notes"] = f"Invalid email syntax: {str(e)}"
        return result

    try:
        domain = extract_email_domain(normalized_email)
        result["Domain"] = domain
    except Exception as e:
        result["Notes"] = f"Domain extraction failed: {str(e)}"
        return result

    if not domain:
        result["Notes"] = "Could not extract domain from email"
        return result

    clean_domain_val = clean_domain(domain)
    if not clean_domain_val:
        result["Notes"] = "Invalid domain after cleaning"
        return result

    try:
        if is_disposable_domain(clean_domain_val):
            result["Verification Status"] = "Disposable"
            result["Verification Score"] = min(
                10,
                calculate_verification_score(
                    normalized_email,
                    clean_domain_val,
                    False,
                    False,
                    "Unknown/Other",
                    None,
                    False,
                    True,
                    False,
                ),
            )
            result["Notes"] = "Disposable email domain detected"
            return result
    except Exception as e:
        result["Notes"] += f"; Disposable check error: {str(e)}"

    try:
        if is_public_email_domain(clean_domain_val):
            result["Verification Status"] = "Public Email"
            result["Verification Score"] = min(
                45,
                calculate_verification_score(
                    normalized_email,
                    clean_domain_val,
                    False,
                    False,
                    "Unknown/Other",
                    None,
                    False,
                    False,
                    True,
                ),
            )
            result["Notes"] = "Public/free email domain detected"
            return result
    except Exception as e:
        result["Notes"] += f"; Public email check error: {str(e)}"

    mx_records = "Not Checked"
    website_active = False
    website_status = "Not Checked"
    email_provider = "Unknown"

    try:
        mx_records = lookup_mx_records(clean_domain_val)
        result["MX Status"] = mx_records

        has_mx = (
            mx_records != "No MX Found"
            and mx_records not in ["Timeout", "Error"]
        )

        website_active, website_status, _ = check_domain_website(clean_domain_val)
        result["Domain Active"] = "Yes" if website_active else "No"
        result["Website Status"] = website_status

        if has_mx:
            email_provider = detect_email_provider(mx_records)
            result["Email Provider"] = email_provider

    except Exception as e:
        result["Notes"] += f"; Domain check error: {str(e)}"
        mx_records = "Error"
        result["MX Status"] = mx_records

    try:
        is_role = is_role_based_email(normalized_email)
    except Exception:
        is_role = False
        result["Notes"] += "; Role-based check error"

    company_match = None
    if (
        company_domain_column
        and company_domain_column in row
        and pd.notnull(row[company_domain_column])
    ):
        try:
            company_domain_val = clean_domain(str(row[company_domain_column]))
            company_match = (
                company_domain_val.lower() == clean_domain_val.lower()
                if company_domain_val
                else False
            )
        except Exception as e:
            company_match = None
            result["Notes"] += f"; Company domain check error: {str(e)}"

    has_mx_flag = (
        mx_records not in ["No MX Found", "Timeout", "Error"] and mx_records != ""
    )

    try:
        score = calculate_verification_score(
            normalized_email=normalized_email,
            domain=clean_domain_val,
            has_mx=has_mx_flag,
            website_active=website_active,
            email_provider=email_provider,
            company_match=company_match,
            is_role_based=is_role,
            is_disposable=False,
            is_public_email=False,
        )
        result["Verification Score"] = score
    except Exception as e:
        result["Verification Score"] = 0
        result["Notes"] += f"; Score calculation error: {str(e)}"

    if result["Verification Status"] not in ["Disposable", "Public Email"]:
        if not has_mx_flag:
            result["Verification Status"] = "No MX Found"
        elif (
            company_match is False
            and company_domain_column
            and company_domain_column in row
        ):
            result["Verification Status"] = "Company Domain Mismatch"
        elif is_role:
            result["Verification Status"] = "Risky"
        else:
            result["Verification Status"] = "Verified"

    notes_parts = []
    if is_role:
        notes_parts.append("Role-based email")
    if (
        company_match is False
        and company_domain_column
        and company_domain_column in row
    ):
        notes_parts.append("Company domain mismatch")
    if not website_active and has_mx_flag:
        notes_parts.append("Website not reachable")

    if notes_parts:
        result["Notes"] = "; ".join(notes_parts) + (
            "; " + result["Notes"] if result["Notes"] else ""
        )
    elif not result["Notes"]:
        result["Notes"] = "Verification completed"

    return result


def convert_df_to_excel(df):
    from io import BytesIO

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
    return output.getvalue()


def convert_df_to_csv(df):
    return df.to_csv(index=False).encode("utf-8")


if __name__ == "__main__":
    main()
