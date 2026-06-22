import streamlit as st
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

st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

:root {
    --primary-blue: #2563eb;
    --blue-light: #dbeafe;
    --blue-dark: #1d4ed8;
    --grey-light: #f8fafc;
    --grey-medium: #e2e8f0;
    --grey-dark: #64748b;
    --white: #ffffff;
    --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
    --shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
    --shadow-md: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -2px rgb(0 0 0 / 0.1);
    --radius: 16px;
    --radius-sm: 8px;
}

.main .block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    background-color: var(--grey-light);
}

.header {
    text-align: center;
    padding: 2rem 0 1.5rem 0;
}

.logo-container {
    display: flex;
    justify-content: center;
    margin-bottom: 1rem;
}

.logo-img {
    max-width: 200px;
    height: auto;
    display: block;
}

.title {
    font-size: 2rem;
    font-weight: 700;
    color: var(--blue-dark);
    margin: 0 0 0.5rem 0;
    letter-spacing: -0.5px;
}

.subtitle {
    font-size: 1.1rem;
    color: var(--grey-dark);
    margin: 0;
    font-weight: 400;
}

.upload-card {
    background: var(--white);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 2rem;
    margin: 2rem 0;
    border: 1px solid var(--grey-medium);
}

.upload-card h3 {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--blue-dark);
    margin: 0 0 1.5rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.upload-card h3::before {
    content: "\1F4CE";
    font-size: 1.5rem;
}

.stButton > button {
    background: var(--primary-blue) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    padding: 0.75rem 1.5rem !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    transition: all 0.2s ease !important;
    box-shadow: var(--shadow-sm) !important;
    width: 100% !important;
}

.stButton > button:hover {
    background: var(--blue-dark) !important;
    transform: translateY(-2px) !important;
    box-shadow: var(--shadow) !important;
}

.stButton > button:active {
    transform: translateY(0) !important;
}

.stSelectbox > div > div {
    border-radius: var(--radius-sm) !important;
    border: 1px solid var(--grey-medium) !important;
}

.stSelectbox > div > div:focus-within {
    border-color: var(--primary-blue) !important;
    box-shadow: 0 0 0 3px var(--blue-light) !important;
}

.stFileUploader > div {
    border: 2px dashed var(--grey-medium) !important;
    border-radius: var(--radius) !important;
    padding: 2rem !important;
    text-align: center !important;
    background-color: var(--grey-light) !important;
    transition: all 0.2s ease !important;
}

.stFileUploader > div:hover {
    border-color: var(--primary-blue) !important;
    background-color: var(--blue-light) !important;
}

.stFileUploader > div > div {
    color: var(--grey-dark) !important;
}

.stFileUploader > div > div > div {
    color: var(--primary-blue) !important;
    font-weight: 600 !important;
}

.processing-section {
    margin: 2rem 0;
    text-align: center;
}

.status-text {
    font-size: 1rem;
    color: var(--grey-dark);
    margin: 1rem 0;
    min-height: 2rem;
}

.stProgress > div > div > div > div {
    background-color: var(--primary-blue) !important;
}

.results-section {
    margin: 2rem 0;
}

.results-section h3 {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--blue-dark);
    margin: 0 0 1.5rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.results-section h3::before {
    content: "\2705";
    font-size: 1.5rem;
}

.dataframe {
    border-radius: var(--radius-sm) !important;
    overflow: hidden !important;
    box-shadow: var(--shadow-sm) !important;
    border: 1px solid var(--grey-medium) !important;
}

.dataframe thead {
    background-color: var(--blue-light) !important;
}

.dataframe th {
    font-weight: 600 !important;
    color: var(--blue-dark) !important;
    text-align: left !important;
    padding: 1rem !important;
    border-bottom: 2px solid var(--grey-medium) !important;
}

.dataframe td {
    padding: 1rem !important;
    border-bottom: 1px solid var(--grey-medium) !important;
    vertical-align: middle !important;
}

.dataframe tbody tr:hover {
    background-color: var(--blue-light) !important;
}

.status-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.status-verified {
    background-color: #dcfce7;
    color: #166534;
}

.status-risky {
    background-color: #fef3c7;
    color: #92400e;
}

.status-invalid {
    background-color: #fee2e2;
    color: #991b1b;
}

.status-no-mx {
    background-color: #fef3c7;
    color: #92400e;
}

.status-public {
    background-color: #dbeafe;
    color: #1e40af;
}

.status-disposable {
    background-color: #fecaca;
    color: #991b1b;
}

.status-mismatch {
    background-color: #fed7aa;
    color: #9a3412;
}

.download-section {
    margin: 2.5rem 0 0 0;
    display: flex;
    gap: 1rem;
}

.download-section .stButton > button {
    flex: 1;
    font-size: 0.95rem;
    padding: 0.75rem !important;
}

.download-section .stButton > button:nth-child(1) {
    background: var(--primary-blue) !important;
}

.download-section .stButton > button:nth-child(1):hover {
    background: var(--blue-dark) !important;
}

.download-section .stButton > button:nth-child(2) {
    background: #64748b !important;
}

.download-section .stButton > button:nth-child(2):hover {
    background: #475569 !important;
}

.empty-state {
    text-align: center;
    padding: 3rem 0;
    color: var(--grey-dark);
}

.empty-state-icon {
    font-size: 4rem;
    margin-bottom: 1.5rem;
    opacity: 0.5;
}

.empty-state-title {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--blue-dark);
    margin: 0 0 1rem 0;
}

.empty-state-text {
    font-size: 1.1rem;
    line-height: 1.6;
    max-width: 400px;
    margin: 0 auto;
}

@media (max-width: 768px) {
    .title {
        font-size: 1.75rem;
    }
    .subtitle {
        font-size: 1rem;
    }
    .upload-card {
        padding: 1.5rem;
    }
    .download-section {
        flex-direction: column;
    }
}
</style>
""", unsafe_allow_html=True)


def _find_logo():
    """Return the first logo file that exists on disk."""
    candidates = [
        "LinkedIn Banner Resize (1586\u00d7390).jpg",
        "assets/safebooks_logo.jpg",
        "assets/safebooks_logo.png",
        "assets/safebooks_logo.jpeg",
        "Safebooks Global Logo.png",
    ]
    for p in candidates:
        if Path(p).is_file():
            return p
    return None


def render_logo():
    logo_path = _find_logo()
    if logo_path is None:
        st.warning("Logo file not found. Please add assets/safebooks_logo.jpg")
        return

    ext = Path(logo_path).suffix.lower().lstrip(".")
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext

    encoded = base64.b64encode(Path(logo_path).read_bytes()).decode("utf-8")
    st.markdown(f"""
    <div class="logo-container">
        <img src="data:image/{mime};base64,{encoded}" class="logo-img" alt="Safebooks Logo">
    </div>
    """, unsafe_allow_html=True)


if "processing" not in st.session_state:
    st.session_state.processing = False
if "results_df" not in st.session_state:
    st.session_state.results_df = None


def main():
    render_logo()
    st.markdown('<h1 class="title">Email Verifier</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Upload your email list and verify domains, MX records, providers, and website status.</p>',
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "Choose a CSV or XLSX file",
        type=["csv", "xlsx"],
        label_visibility="collapsed",
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

        st.markdown('<div class="upload-card">', unsafe_allow_html=True)
        st.markdown("<h3>Select Columns</h3>", unsafe_allow_html=True)

        email_col = st.selectbox(
            "Email Column",
            options=df.columns,
            label_visibility="collapsed",
            help="Choose the column that contains email addresses",
        )

        company_domain_col = st.selectbox(
            "Company Domain Column (Optional)",
            options=[None] + list(df.columns),
            format_func=lambda x: "None" if x is None else x,
            label_visibility="collapsed",
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

        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.results_df is not None and not st.session_state.processing:
        st.markdown('<div class="results-section">', unsafe_allow_html=True)
        st.markdown("<h3>Verification Results</h3>", unsafe_allow_html=True)

        display_df = st.session_state.results_df.copy()

        status_to_badge = {
            "Verified": '<span class="status-badge status-verified">Verified</span>',
            "Risky": '<span class="status-badge status-risky">Risky</span>',
            "Invalid": '<span class="status-badge status-invalid">Invalid</span>',
            "No MX Found": '<span class="status-badge status-no-mx">No MX Found</span>',
            "Public Email": '<span class="status-badge status-public">Public Email</span>',
            "Disposable": '<span class="status-badge status-disposable">Disposable</span>',
            "Company Domain Mismatch": '<span class="status-badge status-mismatch">Company Domain Mismatch</span>',
        }
        display_df["Verification Status"] = display_df["Verification Status"].map(
            lambda x: status_to_badge.get(x, x)
        )

        html = display_df.to_html(
            classes="dataframe", escape=False, index=False, table_id="results-table"
        )
        st.markdown(html, unsafe_allow_html=True)

        st.markdown('<div class="download-section">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            excel_data = convert_df_to_excel(st.session_state.results_df)
            st.download_button(
                label="\U0001F4E5 Download Excel",
                data=excel_data,
                file_name="email_verification_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with col2:
            csv_data = convert_df_to_csv(st.session_state.results_df)
            st.download_button(
                label="\U0001F4E5 Download CSV",
                data=csv_data,
                file_name="email_verification_results.csv",
                mime="text/csv",
                use_container_width=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if uploaded_file is None and not st.session_state.processing:
        st.markdown('<div class="empty-state">', unsafe_allow_html=True)
        st.markdown('<div class="empty-state-icon">📧</div>', unsafe_allow_html=True)
        st.markdown(
            '<h2 class="empty-state-title">Ready to verify emails</h2>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p class="empty-state-text">Upload a CSV or XLSX file containing email addresses to begin verification.</p>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)


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

        has_mx = mx_records != "No MX Found" and mx_records not in ["Timeout", "Error"]

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
