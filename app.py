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

# ── Custom CSS (fully responsive) ──────────────────────────────────────
st.markdown("""
<style>
/* ── hide chrome ───────────────────────────────────────────── */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* ── page ──────────────────────────────────────────────────── */
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    background-color: #f4f6f9 !important;
    max-width: 100% !important;
    overflow-x: hidden !important;
}

/* ── header ────────────────────────────────────────────────── */
.header-wrap {
    text-align: center;
    margin: 0 auto 1.8rem;
    max-width: 100%;
    padding: 0 0.5rem;
    box-sizing: border-box;
}
.header-wrap .logo-img {
    max-width: 200px;
    width: 100%;
    height: auto;
    display: block;
    margin: 0 auto 1rem;
}
.header-wrap h1 {
    font-size: clamp(1.4rem, 4vw, 2rem);
    font-weight: 700;
    color: #1e3a5f;
    margin: 0 0 0.4rem 0;
    letter-spacing: -0.3px;
    word-break: break-word;
}
.header-wrap p {
    font-size: clamp(0.85rem, 2.2vw, 1.05rem);
    color: #64748b;
    margin: 0;
    padding: 0 0.5rem;
}

/* ── white card ────────────────────────────────────────────── */
.white-card {
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.07);
    padding: 1.8rem 2rem 2rem;
    margin-bottom: 1.8rem;
    border: 1px solid #e9edf2;
    box-sizing: border-box;
    overflow: hidden;
}
.white-card h3 {
    font-size: 1.2rem;
    font-weight: 600;
    color: #1e3a5f;
    margin: 0 0 1.4rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* ── upload area ───────────────────────────────────────────── */
.stFileUploader > div {
    border: 2px dashed #d0d5dd !important;
    border-radius: 12px !important;
    padding: 2rem 1rem !important;
    text-align: center !important;
    background: #f8fafc !important;
    transition: border-color 0.2s, background 0.2s !important;
}
.stFileUploader > div:hover {
    border-color: #2563eb !important;
    background: #eff6ff !important;
}

/* ── select boxes ──────────────────────────────────────────── */
.stSelectbox > div > div {
    border-radius: 8px !important;
    border: 1px solid #d0d5dd !important;
}
.stSelectbox > div > div:focus-within {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
}

/* ── primary button ────────────────────────────────────────── */
.stButton > button[kind="primary"] {
    background: #2563eb !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.7rem 1.5rem !important;
    font-weight: 600 !important;
    font-size: clamp(0.85rem, 2vw, 1rem) !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
    transition: background 0.2s, transform 0.15s !important;
    width: 100% !important;
}
.stButton > button[kind="primary"]:hover {
    background: #1d4ed8 !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="primary"]:active {
    transform: translateY(0) !important;
}

/* ── progress bar ──────────────────────────────────────────── */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #2563eb, #60a5fa) !important;
}
.stProgress > div > div > div {
    background: #e2e8f0 !important;
    height: 8px !important;
    border-radius: 999px !important;
}

/* ── summary metrics ───────────────────────────────────────── */
.metric-grid {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
}
.metric-card {
    flex: 1 1 calc(25% - 1rem);
    min-width: 120px;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    padding: 1rem;
    text-align: center;
    border: 1px solid #e9edf2;
    box-sizing: border-box;
}
.metric-card .metric-label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #64748b;
    margin-bottom: 0.25rem;
}
.metric-card .metric-value {
    font-size: clamp(1.2rem, 4vw, 1.8rem);
    font-weight: 800;
}
.metric-card.metric-total .metric-value { color: #1e3a5f; }
.metric-card.metric-verified .metric-value { color: #16a34a; }
.metric-card.metric-risky .metric-value { color: #d97706; }
.metric-card.metric-invalid .metric-value { color: #dc2626; }

/* ── results table wrapper (scroll on overflow) ────────────── */
.table-wrap {
    width: 100%;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    margin-bottom: 0.5rem;
    border-radius: 10px;
    border: 1px solid #e9edf2;
}
.results-table {
    width: 100%;
    min-width: 700px;
    border-collapse: collapse;
    font-size: clamp(0.72rem, 1.6vw, 0.88rem);
}
.results-table thead {
    background: #eff6ff;
}
.results-table th {
    font-weight: 600;
    color: #1e3a5f;
    text-align: left;
    padding: 0.85rem 0.9rem;
    border-bottom: 2px solid #dbeafe;
    white-space: nowrap;
}
.results-table td {
    padding: 0.7rem 0.9rem;
    border-bottom: 1px solid #f0f2f5;
    vertical-align: middle;
    word-break: break-word;
}
.results-table tbody tr:hover {
    background: #f8fafc;
}

/* ── status badges ─────────────────────────────────────────── */
.sbadge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: clamp(0.65rem, 1.4vw, 0.78rem);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    white-space: nowrap;
}
.sbadge-verified { background: #dcfce7; color: #166534; }
.sbadge-risky    { background: #fef3c7; color: #92400e; }
.sbadge-invalid  { background: #fee2e2; color: #991b1b; }
.sbadge-nomx     { background: #f1f5f9; color: #475569; }

/* ── download buttons ──────────────────────────────────────── */
.dl-wrap {
    display: flex;
    gap: 1rem;
    margin-top: 0.5rem;
}
.dl-wrap .stDownloadButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.65rem 1.2rem !important;
    font-size: clamp(0.8rem, 1.8vw, 0.9rem) !important;
    border: 1px solid #d0d5dd !important;
    background: #fff !important;
    color: #1e3a5f !important;
    transition: border-color 0.2s, background 0.2s !important;
    width: 100% !important;
}
.dl-wrap .stDownloadButton > button:hover {
    border-color: #2563eb !important;
    background: #eff6ff !important;
}

/* ── empty state ───────────────────────────────────────────── */
.empty-state {
    text-align: center;
    padding: 3rem 0.5rem 1.5rem;
}
.empty-state .icon { font-size: clamp(2.5rem, 8vw, 3.5rem); opacity: 0.4; margin-bottom: 0.8rem; }
.empty-state h2 { font-size: clamp(1.1rem, 3vw, 1.4rem); font-weight: 600; color: #1e3a5f; margin: 0 0 0.5rem; }
.empty-state p  { font-size: clamp(0.85rem, 2vw, 1rem); color: #64748b; margin: 0; }

/* ── processing text ───────────────────────────────────────── */
.proc-text {
    font-size: clamp(0.8rem, 1.8vw, 0.95rem);
    color: #64748b;
    margin: 0.5rem 0;
    min-height: 1.5rem;
}

/* ════════════════════════════════════════════════════════════════
   RESPONSIVE BREAKPOINTS
   ════════════════════════════════════════════════════════════════ */

/* ── tablets & small laptops (≤1024px) ─────────────────────── */
@media (max-width: 1024px) {
    .white-card { padding: 1.5rem; }
    .metric-card { flex: 1 1 calc(50% - 1rem); }
    .results-table { min-width: 600px; }
}

/* ── tablets (≤768px) ──────────────────────────────────────── */
@media (max-width: 768px) {
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    .header-wrap { margin-bottom: 1.2rem; }
    .header-wrap .logo-img { max-width: 140px; }
    .white-card { padding: 1.2rem 1rem; }
    .stFileUploader > div { padding: 1.2rem 0.8rem !important; }
    .metric-card { flex: 1 1 calc(50% - 0.6rem); padding: 0.7rem; }
    .metric-grid { gap: 0.6rem; margin-bottom: 1rem; }
    .dl-wrap { flex-direction: column; gap: 0.5rem; }
    .results-table { min-width: 500px; }
    .results-table th,
    .results-table td { padding: 0.55rem 0.6rem; }
}

/* ── phones (≤480px) ───────────────────────────────────────── */
@media (max-width: 480px) {
    .block-container { padding-top: 0.6rem !important; }
    .header-wrap { margin-bottom: 1rem; }
    .header-wrap .logo-img { max-width: 100px; margin-bottom: 0.6rem; }
    .white-card { padding: 0.9rem 0.7rem; border-radius: 12px; }
    .white-card h3 { font-size: 1rem; margin-bottom: 1rem; }
    .stFileUploader > div { padding: 0.8rem 0.5rem !important; border-radius: 10px !important; }
    .stButton > button[kind="primary"] { padding: 0.6rem 1rem !important; }
    .metric-card { flex: 1 1 100%; padding: 0.6rem; }
    .metric-card .metric-value { font-size: 1.3rem; }
    .results-table { min-width: 420px; font-size: 0.7rem; }
    .results-table th,
    .results-table td { padding: 0.4rem 0.5rem; }
    .sbadge { font-size: 0.6rem; padding: 0.15rem 0.45rem; }
    .dl-wrap .stDownloadButton > button { padding: 0.55rem 1rem !important; font-size: 0.8rem !important; }
    .empty-state { padding: 2rem 0.5rem 1rem; }
}

/* ── very small screens (≤360px) ───────────────────────────── */
@media (max-width: 360px) {
    .block-container { padding-left: 0.3rem !important; padding-right: 0.3rem !important; }
    .white-card { padding: 0.7rem 0.5rem; }
    .results-table { min-width: 320px; font-size: 0.65rem; }
    .results-table th,
    .results-table td { padding: 0.3rem 0.4rem; }
}
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────
if "processing" not in st.session_state:
    st.session_state.processing = False
if "results_df" not in st.session_state:
    st.session_state.results_df = None


# ── Logo helpers ───────────────────────────────────────────────────────
def _find_logo():
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
        st.warning("Logo not found. Place the file in assets/safebooks_logo.png")
        return
    ext = Path(logo_path).suffix.lower().lstrip(".")
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    encoded = base64.b64encode(Path(logo_path).read_bytes()).decode("utf-8")
    st.markdown(f"""
    <div class="header-wrap">
        <img src="data:image/{mime};base64,{encoded}" class="logo-img" alt="Safebooks Logo">
        <h1>Email Verifier</h1>
        <p>Upload your email list and verify domains, MX records, providers, and website status.</p>
    </div>
    """, unsafe_allow_html=True)


# ── Status badge HTML ──────────────────────────────────────────────────
def badge(status: str) -> str:
    mapping = {
        "Verified":             ("sbadge-verified", "Verified"),
        "Risky":                ("sbadge-risky", "Risky"),
        "Invalid":              ("sbadge-invalid", "Invalid"),
        "No MX Found":          ("sbadge-nomx", "No MX"),
        "Public Email":         ("sbadge-risky", "Public"),
        "Disposable":           ("sbadge-invalid", "Disposable"),
        "Company Domain Mismatch": ("sbadge-risky", "Mismatch"),
    }
    cls, label = mapping.get(status, ("sbadge-nomx", status))
    return f'<span class="sbadge {cls}">{label}</span>'


# ── Main app ───────────────────────────────────────────────────────────
def main():
    render_logo()

    uploaded_file = st.file_uploader(
        "Upload CSV or XLSX",
        type=["csv", "xlsx"],
        label_visibility="collapsed",
    )

    # ── File selected ──────────────────────────────────────────────────
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") \
                 else pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"Could not read file: {e}")
            return

        if df.empty:
            st.warning("The uploaded file is empty.")
            return

        # ── Column selection card ──────────────────────────────────────
        st.markdown('<div class="white-card">', unsafe_allow_html=True)
        st.markdown("<h3>\u2699\ufe0f Configure Columns</h3>", unsafe_allow_html=True)

        email_col = st.selectbox(
            "Email column *",
            df.columns,
            index=_guess_email_col(df.columns),
            label_visibility="visible",
            help="Column containing email addresses",
        )

        company_col = st.selectbox(
            "Company domain column (optional)",
            [None] + list(df.columns),
            format_func=lambda x: "None – skip company match" if x is None else x,
            label_visibility="visible",
            help="Optional column with company domains",
        )

        if st.button("Verify Emails", type="primary", use_container_width=True):
            st.session_state.processing = True
            st.session_state.results_df = None

            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                results = []
                total = len(df)

                for idx, row in df.iterrows():
                    pct = (idx + 1) / total
                    progress_bar.progress(pct)
                    email = row[email_col] if pd.notna(row[email_col]) else ""
                    status_text.markdown(
                        f'<p class="proc-text">Processing {idx+1} of {total} &mdash; '
                        f"{email or '(empty)'}</p>",
                        unsafe_allow_html=True,
                    )

                    results.append(
                        process_email_row(row, email_col, company_col)
                    )

                st.session_state.results_df = pd.DataFrame(results)
            except Exception as e:
                st.error(f"Processing error: {e}")
                st.error(traceback.format_exc())
            finally:
                progress_bar.empty()
                status_text.empty()
                st.session_state.processing = False

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Results ────────────────────────────────────────────────────────
    if st.session_state.results_df is not None and not st.session_state.processing:
        rdf = st.session_state.results_df

        # summary metrics
        total = len(rdf)
        verified = int((rdf["Verification Status"] == "Verified").sum())
        risky = int((rdf["Verification Status"] == "Risky").sum())
        invalid = int((rdf["Verification Status"] == "Invalid").sum())
        nomx = int((rdf["Verification Status"] == "No MX Found").sum())

        st.markdown('<div class="metric-grid">', unsafe_allow_html=True)
        for cls, label, value in [
            ("metric-total", "Total", total),
            ("metric-verified", "Verified", verified),
            ("metric-risky", "Risky", risky + nomx),
            ("metric-invalid", "Invalid", invalid),
        ]:
            st.markdown(
                f'<div class="metric-card {cls}">'
                f'<div class="metric-label">{label}</div>'
                f'<div class="metric-value">{value}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        # results table with badges
        st.markdown('<div class="white-card">', unsafe_allow_html=True)
        st.markdown("<h3>\u2705 Results</h3>", unsafe_allow_html=True)

        display = rdf.copy()
        display["Verification Status"] = display["Verification Status"].apply(badge)

        html = display.to_html(
            classes="results-table",
            escape=False,
            index=False,
            table_id="tbl",
        )
        st.markdown(f'<div class="table-wrap">{html}</div>', unsafe_allow_html=True)

        # download buttons
        st.markdown('<div class="dl-wrap">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "Download Excel",
                data=convert_df_to_excel(rdf),
                file_name="email_verification_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with c2:
            st.download_button(
                "Download CSV",
                data=convert_df_to_csv(rdf),
                file_name="email_verification_results.csv",
                mime="text/csv",
                use_container_width=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Empty state ────────────────────────────────────────────────────
    if uploaded_file is None and not st.session_state.processing:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">📧</div>
            <h2>Ready to verify emails</h2>
            <p>Upload a CSV or XLSX file containing email addresses to begin.</p>
        </div>
        """, unsafe_allow_html=True)


# ── Backend (unchanged) ────────────────────────────────────────────────
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


def _guess_email_col(cols):
    lower = [c.strip().lower() for c in cols]
    for kw in ("email", "e-mail", "mail", "email address"):
        if kw in lower:
            return lower.index(kw)
    return 0


def convert_df_to_excel(df):
    from io import BytesIO

    report_df = df.copy()

    report_df["MX Yes/No"] = report_df["MX Status"].apply(
        lambda x: "Yes" if x not in [
            "No MX Found", "Timeout", "Error", "Not Checked", ""
        ] else "No"
    )

    if "SPF Record" in report_df.columns:
        report_df["SPF Yes/No"] = report_df["SPF Record"].apply(
            lambda x: "Yes" if isinstance(x, str) and x.lower().startswith("v=spf1") else "No"
        )
    else:
        report_df["SPF Yes/No"] = ""

    if "DMARC Record" in report_df.columns:
        report_df["DMARC Yes/No"] = report_df["DMARC Record"].apply(
            lambda x: "Yes" if isinstance(x, str) and x.lower().startswith("v=dmarc1") else "No"
        )
    else:
        report_df["DMARC Yes/No"] = ""

    report_df["Domain Active/Not Active"] = report_df["Domain Active"].apply(
        lambda x: "Yes" if str(x).strip().lower() == "yes" else "No"
    )

    report_columns = [
        "Email", "Domain", "MX Yes/No", "SPF Yes/No", "DMARC Yes/No",
        "Domain Active/Not Active", "Verification Score",
        "Verification Status", "Notes",
    ]

    for col in report_columns:
        if col not in report_df.columns:
            report_df[col] = ""

    final_report = report_df[report_columns].copy()

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        final_report.to_excel(w, index=False, sheet_name="Results")
    return buf.getvalue()


def convert_df_to_csv(df):
    report_df = df.copy()

    report_df["MX Yes/No"] = report_df["MX Status"].apply(
        lambda x: "Yes" if x not in [
            "No MX Found", "Timeout", "Error", "Not Checked", ""
        ] else "No"
    )

    if "SPF Record" in report_df.columns:
        report_df["SPF Yes/No"] = report_df["SPF Record"].apply(
            lambda x: "Yes" if isinstance(x, str) and x.lower().startswith("v=spf1") else "No"
        )
    else:
        report_df["SPF Yes/No"] = ""

    if "DMARC Record" in report_df.columns:
        report_df["DMARC Yes/No"] = report_df["DMARC Record"].apply(
            lambda x: "Yes" if isinstance(x, str) and x.lower().startswith("v=dmarc1") else "No"
        )
    else:
        report_df["DMARC Yes/No"] = ""

    report_df["Domain Active/Not Active"] = report_df["Domain Active"].apply(
        lambda x: "Yes" if str(x).strip().lower() == "yes" else "No"
    )

    report_columns = [
        "Email", "Domain", "MX Yes/No", "SPF Yes/No", "DMARC Yes/No",
        "Domain Active/Not Active", "Verification Score",
        "Verification Status", "Notes",
    ]

    for col in report_columns:
        if col not in report_df.columns:
            report_df[col] = ""

    final_report = report_df[report_columns].copy()
    return final_report.to_csv(index=False).encode("utf-8")


if __name__ == "__main__":
    main()
