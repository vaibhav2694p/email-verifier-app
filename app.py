from __future__ import annotations

import os
from io import BytesIO

import pandas as pd
import streamlit as st
import openpyxl  # noqa: F401

from email_verifier.new_verifier import verify_email

st.set_page_config(page_title="Email Verifier", page_icon="@", layout="wide")

# ─── Brand colours ───────────────────────────────────────────────────────────
SB_PRIMARY   = "#0055A5"   # Safebooks blue
SB_ACCENT    = "#003D73"   # dark blue
SB_LIGHT     = "#EAF1FB"   # pale blue tint
SB_BG        = "#F4F6FA"   # page background
SB_CARD      = "#FFFFFF"
SB_TEXT      = "#1B2A4A"
SB_MUTED     = "#6B7DAA"
SB_GREEN     = "#16A34A"
SB_AMBER     = "#D97706"
SB_RED       = "#DC2626"
SB_GREY      = "#6B7280"
SB_BORDER    = "#E2E8F0"

LOGO_PATHS = [
    "LinkedIn Banner Resize (1586\u00d7390).jpg",
    "assets/LinkedIn Banner Resize (1586\u00d7390).jpg",
    "static/LinkedIn Banner Resize (1586\u00d7390).jpg",
    "assets/logo.jpg",
    "static/logo.jpg",
    "logo.jpg",
]

CSS = f"""
<style>
/* ── hide Streamlit chrome ──────────────────────────────────────────── */
#MainMenu {{visibility: hidden;}}
footer    {{visibility: hidden;}}
header    {{visibility: hidden;}}

/* ── global ─────────────────────────────────────────────────────────── */
.stApp {{
    background: {SB_BG};
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
}}

/* ── banner / header ────────────────────────────────────────────────── */
.banner-wrapper {{
    background: linear-gradient(135deg, {SB_PRIMARY} 0%, {SB_ACCENT} 100%);
    border-radius: 0 0 20px 20px;
    padding: 0 0 28px 0;
    margin: -10px -10px 28px -10px;
    box-shadow: 0 4px 20px rgba(0, 85, 165, 0.18);
}}
.banner-logo {{
    display: block;
    margin: 0 auto;
    padding: 24px 40px 16px;
    max-height: 160px;
    object-fit: contain;
}}
.banner-title {{
    text-align: center;
    color: #FFFFFF;
    font-size: 34px;
    font-weight: 800;
    margin: 0 0 6px 0;
    letter-spacing: -0.3px;
}}
.banner-subtitle {{
    text-align: center;
    color: rgba(255,255,255,0.82);
    font-size: 15px;
    font-weight: 400;
    margin: 0;
    padding: 0 20px;
}}

/* ── cards ──────────────────────────────────────────────────────────── */
.card {{
    background: {SB_CARD};
    padding: 26px 28px;
    border-radius: 16px;
    box-shadow: 0 2px 12px rgba(27, 42, 74, 0.07);
    margin-bottom: 24px;
    border: 1px solid {SB_BORDER};
}}

/* ── metric cards ───────────────────────────────────────────────────── */
.metric-card {{
    background: {SB_CARD};
    padding: 20px 14px;
    border-radius: 14px;
    box-shadow: 0 2px 10px rgba(27, 42, 74, 0.06);
    border: 1px solid {SB_BORDER};
    text-align: center;
    transition: box-shadow 0.2s;
}}
.metric-card:hover {{
    box-shadow: 0 4px 16px rgba(27, 42, 74, 0.12);
}}
.metric-label {{
    color: {SB_MUTED};
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.6px;
}}
.metric-value {{
    color: {SB_TEXT};
    font-size: 30px;
    font-weight: 800;
    margin-top: 2px;
}}

/* ── buttons ────────────────────────────────────────────────────────── */
.stButton > button[kind="primary"] {{
    background: {SB_PRIMARY};
    color: white;
    border-radius: 10px;
    border: none;
    padding: 10px 24px;
    font-weight: 700;
    font-size: 15px;
    letter-spacing: 0.2px;
    transition: background 0.2s;
}}
.stButton > button[kind="primary"]:hover {{
    background: {SB_ACCENT};
    color: white;
}}

.stDownloadButton > button {{
    border-radius: 10px;
    font-weight: 700;
    padding: 11px 20px;
    border: 1px solid {SB_BORDER};
    background: {SB_CARD};
    color: {SB_TEXT};
    transition: all 0.2s;
}}
.stDownloadButton > button:hover {{
    border-color: {SB_PRIMARY};
    color: {SB_PRIMARY};
}}

/* ── progress bar ───────────────────────────────────────────────────── */
.stProgress > div > div > div > div {{
    background: linear-gradient(90deg, {SB_PRIMARY}, #2B8AD9);
    border-radius: 999px;
}}
.stProgress > div > div > div {{
    background: {SB_LIGHT};
    border-radius: 999px;
    height: 8px;
}}

/* ── inputs ─────────────────────────────────────────────────────────── */
.stSelectbox > div > div {{
    border-radius: 10px;
    border: 1px solid {SB_BORDER};
}}
.stSelectbox > div > div:focus-within {{
    border-color: {SB_PRIMARY};
    box-shadow: 0 0 0 3px rgba(0, 85, 165, 0.12);
}}

.stFileUploader > div {{
    border-radius: 14px;
    border: 2px dashed {SB_BORDER};
    background: {SB_LIGHT};
    padding: 24px;
}}
.stFileUploader > div:hover {{
    border-color: {SB_PRIMARY};
    background: #E0EBFA;
}}
.stFileUploader > div:focus-within {{
    border-color: {SB_PRIMARY};
    box-shadow: 0 0 0 3px rgba(0, 85, 165, 0.12);
}}

/* ── data frame ─────────────────────────────────────────────────────── */
.stDataFrame {{
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid {SB_BORDER};
}}
[data-testid="stTable"] {{
    border-radius: 12px;
    overflow: hidden;
}}

/* ── section headings ───────────────────────────────────────────────── */
.section-title {{
    font-size: 17px;
    font-weight: 700;
    color: {SB_TEXT};
    margin: 4px 0 14px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}}

/* ── status badges ──────────────────────────────────────────────────── */
.status-badge {{
    display: inline-block;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    color: white;
    text-align: center;
    min-width: 90px;
}}
.badge-verified {{ background: {SB_GREEN}; }}
.badge-risky    {{ background: {SB_AMBER}; }}
.badge-invalid  {{ background: {SB_RED}; }}
.badge-nomx     {{ background: {SB_GREY}; }}

/* ── misc ───────────────────────────────────────────────────────────── */
.upload-icon {{ font-size: 32px; margin-bottom: 12px; }}
.upload-text {{ color: {SB_MUTED}; font-size: 14px; }}
.result-row:hover {{ background: #FAFBFD; }}
</style>
"""

STATUS_COLORS = {
    "Verified":      SB_GREEN,
    "Risky":         SB_AMBER,
    "Invalid":       SB_RED,
    "No MX Found":   SB_GREY,
    "NXDOMAIN":      SB_GREY,
    "DNS error":     SB_GREY,
    "DNS timeout":   SB_GREY,
    "No domain":     SB_GREY,
    "Timeout":       SB_GREY,
    "Unreachable":   SB_GREY,
    "Inactive":      SB_GREY,
    "Active (No SSL)": SB_AMBER,
    "Error":         SB_RED,
}


def status_badge(status: str) -> str:
    color = STATUS_COLORS.get(status, SB_GREY)
    cls = ""
    if "Verified" in status:
        cls = "badge-verified"
    elif "Risky" in status:
        cls = "badge-risky"
    elif "Invalid" in status:
        cls = "badge-invalid"
    elif "No MX" in status or "NXDOMAIN" in status or "DNS" in status or "No domain" in status:
        cls = "badge-nomx"
    return f"<span class='status-badge {cls}' style='background:{color};'>{status}</span>"


def _find_logo() -> str | None:
    """Return the first logo path that exists on disk."""
    for p in LOGO_PATHS:
        if os.path.isfile(p):
            return p
    return None


def render_app() -> None:
    st.markdown(CSS, unsafe_allow_html=True)

    # ── Header banner ──────────────────────────────────────────────────
    logo_file = _find_logo()
    logo_html = ""
    if logo_file:
        logo_html = f'<img class="banner-logo" src="data:image/jpeg;base64,{_img_to_b64(logo_file)}" alt="Safebooks Global" />'

    st.markdown(f"""
    <div class="banner-wrapper">
        {logo_html}
        <h1 class="banner-title">Email Verifier</h1>
        <p class="banner-subtitle">Upload your email list and verify domains, MX records, providers, and website status.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Upload ─────────────────────────────────────────────────────────
    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=["csv", "xlsx"],
        label_visibility="collapsed",
    )

    if uploaded_file is None:
        st.markdown(f"""
        <div class="card" style="text-align: center; padding: 60px 24px;">
            <div class="upload-icon">&#128206;</div>
            <p style="font-size: 18px; font-weight: 600; color: {SB_TEXT}; margin-bottom: 8px;">
                Drag &amp; drop your file here</p>
            <p class="upload-text">or click to browse</p>
            <p class="upload-text" style="margin-top: 16px;">Accepted formats: <strong>CSV</strong>, <strong>XLSX</strong></p>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Read file ──────────────────────────────────────────────────────
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)
        else:
            df = pd.read_excel(uploaded_file, dtype=str, keep_default_na=False)
    except Exception as e:
        st.error(f"Failed to read file: {e}")
        return

    df = df.fillna("").astype(str)
    columns = list(df.columns)

    # ── Preview ────────────────────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">&#128203; File Preview</div>', unsafe_allow_html=True)
    st.dataframe(df.head(10), hide_index=True, use_container_width=True)
    st.caption(f"Total rows: {len(df):,}  &bull;  Columns: {len(columns)}")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Column selection ───────────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">&#9881;&#65039; Column Selection</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        email_col = st.selectbox("Email column *", columns, index=_guess_email_column(columns))
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Required &bull; Select the column containing email addresses")

    verify_clicked = st.button("Verify Emails", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if not verify_clicked:
        return

    total = len(df)
    if total == 0:
        st.warning("The file is empty.")
        return

    progress_bar = st.progress(0)
    status_text = st.empty()
    results = []

    # ── Processing ─────────────────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">&#128260; Processing</div>', unsafe_allow_html=True)

    for idx, row in df.iterrows():
        email = str(row.get(email_col, "")).strip()
        status_text.text(f"Verifying {idx + 1} of {total}: {email or '(empty)'}")
        result = verify_email(email)
        results.append(result)
        progress_bar.progress((idx + 1) / total)

    result_df = pd.DataFrame(results)
    status_text.success(f"Verification complete. {total} emails processed.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Summary cards ──────────────────────────────────────────────────
    total_count   = len(result_df)
    verified_count = int((result_df["Verification Status"] == "Verified").sum())
    risky_count    = int((result_df["Verification Status"] == "Risky").sum())
    invalid_count  = int((result_df["Verification Status"] == "Invalid").sum())

    st.markdown(f'<div class="section-title">&#128202; Summary</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Emails</div>
            <div class="metric-value">{total_count:,}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label" style="color:{SB_GREEN};">Verified</div>
            <div class="metric-value" style="color:{SB_GREEN};">{verified_count:,}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label" style="color:{SB_AMBER};">Risky</div>
            <div class="metric-value" style="color:{SB_AMBER};">{risky_count:,}</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label" style="color:{SB_RED};">Invalid</div>
            <div class="metric-value" style="color:{SB_RED};">{invalid_count:,}</div>
        </div>""", unsafe_allow_html=True)

    # ── Results table ──────────────────────────────────────────────────
    st.markdown(f'<div class="section-title">&#128203; Results</div>', unsafe_allow_html=True)

    display_df = result_df.copy()
    display_df["Verification Status"] = display_df["Verification Status"].apply(status_badge)

    st.markdown(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)

    # ── Downloads ──────────────────────────────────────────────────────
    st.markdown(f'<div class="section-title">&#128190; Download</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    excel_buf = BytesIO()
    with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
        result_df.to_excel(writer, index=False, sheet_name="Results")
    excel_bytes = excel_buf.getvalue()

    with c1:
        st.download_button(
            "Download Excel",
            data=excel_bytes,
            file_name="email_verification_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "Download CSV",
            data=result_df.to_csv(index=False).encode("utf-8"),
            file_name="email_verification_results.csv",
            mime="text/csv",
            use_container_width=True,
        )


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _guess_email_column(columns: list[str]) -> int:
    lower = [c.strip().lower() for c in columns]
    for keyword in ("email", "e-mail", "mail", "email address"):
        if keyword in lower:
            return lower.index(keyword)
    return 0


def _img_to_b64(path: str) -> str:
    import base64
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


if __name__ == "__main__":
    render_app()
