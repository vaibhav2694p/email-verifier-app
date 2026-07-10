import base64
import traceback
from pathlib import Path
from typing import Dict, List

import pandas as pd
import streamlit as st

from enrichment.company_lookup import lookup_company
from enrichment.models import EnrichmentResult
from enrichment.person_lookup import lookup_person
from enrichment.summary import generate_summary as generate_enrichment_summary
from services.bulk_processor import BulkProcessor
from services.export_service import ExportService
from services.input_service import parse_upload
from services.summary_service import SummaryService
from verifier.config import VerifierConfig
from verifier.models import PipelineStage, VerificationResult
from verifier.pipeline import VerificationPipeline
from verifier.smtp_validator import check_port_25_available

st.set_page_config(
    page_title="Email Verifier",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS (fully responsive + extended) ─────────────────────────────
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
.white-card-sm {
    padding: 1rem 1.2rem;
    margin-bottom: 1rem;
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

/* ── secondary button ──────────────────────────────────────── */
.stButton > button[kind="secondary"] {
    border-radius: 8px !important;
    font-weight: 600 !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #2563eb !important;
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

/* ── summary metrics (extended) ────────────────────────────── */
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
    transition: transform 0.15s;
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
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
.metric-card.metric-average .metric-value { color: #2563eb; }
.metric-card.metric-risky .metric-value { color: #d97706; }
.metric-card.metric-invalid .metric-value { color: #dc2626; }
.metric-card.metric-unknown .metric-value { color: #6b7280; }
.metric-card.metric-disposable .metric-value { color: #ea580c; }
.metric-card.metric-catchall .metric-value { color: #7c3aed; }
.metric-card.metric-role .metric-value { color: #0891b2; }
.metric-card.metric-duplicate .metric-value { color: #be185d; }
.metric-card.metric-nomx .metric-value { color: #78716c; }
.metric-card.metric-smtp-blocked .metric-value { color: #b91c1c; }
.metric-card.metric-score .metric-value { color: #2563eb; }
.metric-card.metric-unique .metric-value { color: #0f766e; }

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

/* ── status badges (extended) ──────────────────────────────── */
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
.sbadge-average  { background: #dbeafe; color: #1e40af; }
.sbadge-risky    { background: #fef3c7; color: #92400e; }
.sbadge-invalid  { background: #fee2e2; color: #991b1b; }
.sbadge-nomx     { background: #f1f5f9; color: #475569; }
.sbadge-unknown  { background: #f1f5f9; color: #6b7280; }
.sbadge-catchall { background: #f3e8ff; color: #6b21a8; }
.sbadge-role     { background: #cffafe; color: #155e75; }
.sbadge-disposable { background: #ffedd5; color: #9a3412; }

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

/* ── TAB STYLING ───────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    background: #fff;
    border-radius: 12px;
    padding: 0.5rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    border: 1px solid #e9edf2;
    margin-bottom: 1.5rem;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    padding: 0.6rem 1.2rem !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    color: #64748b !important;
    transition: all 0.2s !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: #eff6ff !important;
    color: #1e3a5f !important;
    box-shadow: 0 1px 3px rgba(37,99,235,0.15) !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #2563eb !important;
}

/* ── SINGLE EMAIL RESULT CARDS ─────────────────────────────── */
.stage-card {
    background: #fff;
    border-radius: 12px;
    border: 1px solid #e9edf2;
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    transition: border-color 0.2s;
}
.stage-card:hover {
    border-color: #d0d5dd;
}
.stage-card.stage-pass {
    border-left: 4px solid #16a34a;
}
.stage-card.stage-fail {
    border-left: 4px solid #dc2626;
}
.stage-card.stage-warn {
    border-left: 4px solid #d97706;
}
.stage-card .stage-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.4rem;
}
.stage-card .stage-name {
    font-weight: 700;
    font-size: 0.95rem;
    color: #1e3a5f;
    text-transform: capitalize;
}
.stage-card .stage-duration {
    font-size: 0.75rem;
    color: #94a3b8;
    font-weight: 500;
}
.stage-card .stage-status {
    font-size: 0.8rem;
    font-weight: 600;
}
.stage-card .stage-detail {
    font-size: 0.82rem;
    color: #475569;
    margin-top: 0.2rem;
    word-break: break-word;
}
.stage-icon {
    display: inline-block;
    width: 24px;
    text-align: center;
    margin-right: 0.4rem;
}

/* ── FILTER SIDEBAR ────────────────────────────────────────── */
.filter-section {
    margin-bottom: 0.8rem;
}
.filter-section .filter-label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #64748b;
    margin-bottom: 0.3rem;
}
.sidebar-notice {
    font-size: 0.8rem;
    padding: 0.6rem 0.8rem;
    border-radius: 8px;
    margin-bottom: 0.8rem;
}

/* ── EXTENDED METRIC GRID (dense) ──────────────────────────── */
.metric-grid-dense {
    display: flex;
    gap: 0.6rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
}
.metric-card-dense {
    flex: 1 1 calc(16.66% - 0.6rem);
    min-width: 100px;
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    padding: 0.7rem 0.5rem;
    text-align: center;
    border: 1px solid #e9edf2;
}
.metric-card-dense .metric-label {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    color: #64748b;
    margin-bottom: 0.15rem;
}
.metric-card-dense .metric-value {
    font-size: clamp(1rem, 3vw, 1.4rem);
    font-weight: 800;
}
.metric-card-dense.metric-total .metric-value { color: #1e3a5f; }
.metric-card-dense.metric-verified .metric-value { color: #16a34a; }
.metric-card-dense.metric-average .metric-value { color: #2563eb; }
.metric-card-dense.metric-risky .metric-value { color: #d97706; }
.metric-card-dense.metric-invalid .metric-value { color: #dc2626; }
.metric-card-dense.metric-unknown .metric-value { color: #6b7280; }
.metric-card-dense.metric-disposable .metric-value { color: #ea580c; }
.metric-card-dense.metric-catchall .metric-value { color: #7c3aed; }
.metric-card-dense.metric-role .metric-value { color: #0891b2; }

/* ── status indicator dots ─────────────────────────────────── */
.status-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 0.4rem;
}
.status-dot-pass { background: #16a34a; }
.status-dot-fail { background: #dc2626; }
.status-dot-warn { background: #d97706; }

/* ════════════════════════════════════════════════════════════════
   RESPONSIVE BREAKPOINTS
   ════════════════════════════════════════════════════════════════ */

/* ── tablets & small laptops (≤1024px) ─────────────────────── */
@media (max-width: 1024px) {
    .white-card { padding: 1.5rem; }
    .metric-card { flex: 1 1 calc(50% - 1rem); }
    .metric-card-dense { flex: 1 1 calc(33.33% - 0.6rem); }
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
    .metric-card-dense { flex: 1 1 calc(50% - 0.6rem); }
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
    .metric-card-dense { flex: 1 1 100%; }
    .results-table { min-width: 420px; font-size: 0.7rem; }
    .results-table th,
    .results-table td { padding: 0.4rem 0.5rem; }
    .sbadge { font-size: 0.6rem; padding: 0.15rem 0.45rem; }
    .stTabs [data-baseweb="tab"] { padding: 0.4rem 0.8rem !important; font-size: 0.8rem !important; }
    .dl-wrap .stDownloadButton > button { padding: 0.55rem 1rem !important; font-size: 0.8rem !important; }
    .empty-state { padding: 2rem 0.5rem 1rem; }
    .stage-card { padding: 0.7rem 0.8rem; }
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
if "cancelled" not in st.session_state:
    st.session_state.cancelled = False
if "single_result" not in st.session_state:
    st.session_state.single_result = None
if "config" not in st.session_state:
    st.session_state.config = VerifierConfig()


# ── Column display mapping ─────────────────────────────────────────────
DISPLAY_COLUMN_MAP: Dict[str, str] = {
    "original_email": "Email",
    "normalized_email": "Normalized Email",
    "local_part": "Local Part",
    "domain": "Domain",
    "verification_status": "Verification Status",
    "verification_score": "Score",
    "confidence_level": "Confidence",
    "risk_level": "Risk",
    "mx_status": "MX Status",
    "mx_provider": "Provider",
    "domain_active": "Domain Active",
    "website_status": "Website",
    "disposable": "Disposable",
    "free_public_email": "Free/Public",
    "role_based": "Role-Based",
    "catch_all": "Catch-All",
    "company_domain_match": "Company Match",
    "smtp_status": "SMTP Status",
    "is_duplicate": "Duplicate",
    "duplicate_of": "Duplicate Of",
    "syntax_valid": "Syntax Valid",
    "syntax_error": "Syntax Error",
    "domain_typo": "Domain Typo",
    "suggested_domain": "Suggested Domain",
    "null_mx": "Null MX",
    "primary_mx": "Primary MX",
    "mx_records": "MX Records",
    "smtp_code": "SMTP Code",
    "smtp_message": "SMTP Message",
    "processing_time_ms": "Time (ms)",
    "notes": "Notes",
    "score_reasons": "Score Reasons",
}

DISPLAY_COLUMN_ORDER: List[str] = [
    "Email", "Domain", "Verification Status", "Score",
    "Confidence", "Risk", "MX Status", "Provider",
    "Disposable", "Free/Public", "Role-Based", "Catch-All",
    "Company Match", "SMTP Status", "Domain Active",
    "Duplicate", "Notes",
]


# ── Logo helpers ───────────────────────────────────────────────────────
def _find_logo():
    candidates = [
        "LinkedIn Banner Resize (1586×390).jpg",
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


# ── Status badge HTML (extended) ───────────────────────────────────────
def badge(status: str) -> str:
    mapping = {
        "Valid":                ("sbadge-verified", "Valid"),
        "Verified":             ("sbadge-verified", "Verified"),
        "Likely Valid":         ("sbadge-average", "Likely"),
        "Average":              ("sbadge-average", "Average"),
        "Risky":                ("sbadge-risky", "Risky"),
        "Invalid":              ("sbadge-invalid", "Invalid"),
        "Unknown":              ("sbadge-unknown", "Unknown"),
        "No Mail Server":       ("sbadge-nomx", "No Mail"),
        "No MX Found":          ("sbadge-nomx", "No MX"),
        "Syntax Error":         ("sbadge-invalid", "Syntax"),
        "Catch-All":            ("sbadge-catchall", "Catch-All"),
        "Temporary Failure":    ("sbadge-nomx", "Temp Fail"),
        "Disposable":           ("sbadge-disposable", "Disposable"),
        "Public Email":         ("sbadge-risky", "Public"),
        "Company Domain Mismatch": ("sbadge-risky", "Mismatch"),
        "Role-Based":           ("sbadge-role", "Role"),
    }
    cls, label = mapping.get(status, ("sbadge-unknown", status))
    return f'<span class="sbadge {cls}">{label}</span>'


def stage_icon(success: bool, stage_name: str) -> str:
    if success:
        return '<span class="status-dot status-dot-pass"></span>'
    if stage_name in ("company_match", "free_provider"):
        return '<span class="status-dot status-dot-warn"></span>'
    return '<span class="status-dot status-dot-fail"></span>'


# ── Helpers ────────────────────────────────────────────────────────────
def _guess_email_col(cols):
    lower = [c.strip().lower() for c in cols]
    for kw in ("email", "e-mail", "mail", "email address"):
        if kw in lower:
            return lower.index(kw)
    return 0


def _prepare_display_df(df: pd.DataFrame) -> pd.DataFrame:
    available = {k: v for k, v in DISPLAY_COLUMN_MAP.items() if k in df.columns}
    display = df[list(available.keys())].copy()
    display.rename(columns=available, inplace=True)
    cols_in_order = [c for c in DISPLAY_COLUMN_ORDER if c in display.columns]
    extra = [c for c in display.columns if c not in cols_in_order]
    return display[cols_in_order + extra]


def _get_export_df(df: pd.DataFrame) -> pd.DataFrame:
    export_cols = [
        "original_email", "normalized_email", "domain",
        "verification_status", "verification_score", "confidence_level",
        "risk_level", "mx_status", "mx_provider", "domain_active",
        "website_status", "disposable", "free_public_email",
        "role_based", "catch_all", "company_domain_match",
        "smtp_status", "is_duplicate", "duplicate_of", "notes",
    ]
    available = [c for c in export_cols if c in df.columns]
    return df[available].copy()


# ── Main app ───────────────────────────────────────────────────────────
def main():
    with st.sidebar:
        render_sidebar()

    render_logo()
    tab1, tab2, tab3 = st.tabs(["📊 Bulk Verification", "📧 Single Email", "🔍 Email Intelligence"])

    with tab1:
        render_bulk_verification()

    with tab2:
        render_single_verification()

    with tab3:
        render_email_intelligence()


# ── Sidebar ────────────────────────────────────────────────────────────
def render_sidebar():
    st.markdown("### ⚙️ Configuration")

    _render_smtp_config()

    # ── Cancel button during processing ──
    if st.session_state.processing:
        st.markdown("---")
        if st.button("⏹️ Cancel Processing", type="secondary", use_container_width=True):
            st.session_state.cancelled = True
            st.rerun()

    # ── SMTP availability notice ──
    if st.session_state.results_df is not None:
        rdf = st.session_state.results_df
        if "smtp_status" in rdf.columns:
            blocked = rdf[rdf["smtp_status"].isin(["connection_blocked", "smtp_disabled"])]
            if not blocked.empty:
                st.warning(
                    f"⚠️ SMTP connection was blocked for {len(blocked)} email(s). "
                    "SMTP verification may not be available from this network.",
                )

    # ── Filters when results available ──
    if st.session_state.results_df is not None and not st.session_state.processing:
        st.markdown("---")
        st.markdown("### 🔍 Filters")
        render_filters()

    # ── Privacy notice ──
    st.markdown("---")
    st.markdown("### 🔒 Privacy")
    st.caption(
        "Your data is processed entirely in-memory. "
        "No email addresses are stored, logged, or shared with third parties. "
        "All results are cleared when you close or refresh this page."
    )


def _render_smtp_config():
    with st.expander("📧 SMTP Configuration", expanded=True):
        config = st.session_state.config

        mode = st.radio(
            "Verification Mode",
            options=["disabled", "test", "real"],
            index=["disabled", "test", "real"].index(config.smtp_verification_mode),
            horizontal=True,
            help="disabled = no SMTP checks | test = Mailpit/local server | real = recipient MX probing",
            key="smtp_mode_radio",
        )
        config.smtp_verification_mode = mode

        if mode == "disabled":
            config.enable_smtp_check = False
            config.smtp_test_mode = False
            st.info("SMTP checks are disabled. Only syntax, DNS, MX, and classification checks run.")

        elif mode == "test":
            config.enable_smtp_check = True
            config.smtp_test_mode = True
            st.success("Test mode: connects to local Mailpit or test SMTP server.")

            with st.container():
                config.test_smtp_host = st.text_input(
                    "Test SMTP Host",
                    value=config.test_smtp_host,
                    key="test_smtp_host",
                )
                config.test_smtp_port = st.number_input(
                    "Test SMTP Port",
                    min_value=1, max_value=65535,
                    value=config.test_smtp_port,
                    key="test_smtp_port",
                )
                config.test_smtp_use_tls = st.toggle(
                    "Use TLS",
                    value=config.test_smtp_use_tls,
                    key="test_smtp_tls",
                )

            st.caption("Mailpit web inbox: http://localhost:8025")

            if st.button("🔌 Test SMTP Connection", use_container_width=True, key="btn_test_conn"):
                _run_smtp_connection_test(config.test_smtp_host, config.test_smtp_port)

        elif mode == "real":
            config.enable_smtp_check = True
            config.smtp_test_mode = False

            st.warning("Real SMTP: connects to recipient MX servers on port 25. May be blocked.")

            config.verifier_email = st.text_input(
                "Verifier Email",
                value=config.verifier_email,
                placeholder="verifier@yourdomain.com",
                help="MAIL FROM address for SMTP conversation",
                key="v_email",
            )
            config.verifier_domain = st.text_input(
                "Verifier Domain",
                value=config.verifier_domain,
                placeholder="yourdomain.com",
                key="v_domain",
            )

            col1, col2 = st.columns(2)
            with col1:
                config.smtp_port = st.number_input(
                    "SMTP Port", min_value=1, max_value=65535,
                    value=config.smtp_port, key="smtp_port",
                )
            with col2:
                config.smtp_connection_timeout = st.number_input(
                    "Timeout (s)", min_value=1, max_value=60,
                    value=config.smtp_connection_timeout, key="smtp_timeout",
                )

            # Port 25 status
            port25_ok = check_port_25_available("gmail.com", timeout=3)
            if port25_ok:
                st.success("Port 25 is available on this network.")
            else:
                st.error("Port 25 is blocked. Real SMTP verification will not work.")

            if st.button("🔌 Test SMTP Connection", use_container_width=True, key="btn_real_conn"):
                if not config.verifier_email or not config.verifier_domain:
                    st.error("Configure verifier email and domain first.")
                else:
                    _run_smtp_connection_test("aspmx.l.google.com", config.smtp_port)

        # ── Status summary ──
        st.markdown("---")
        _render_smtp_status(config)

    st.markdown("---")
    with st.expander("🔍 Enrichment", expanded=False):
        enrichment_enabled = st.toggle(
            "Enable Email Enrichment",
            value=st.session_state.get("enrichment_enabled", False),
            help="Search public sources for person and company info during bulk verification",
            key="enrichment_toggle",
        )
        st.session_state.enrichment_enabled = enrichment_enabled
        if enrichment_enabled:
            st.info("Enrichment adds public profile data to verification results. Processing may be slower.")
        else:
            st.caption("Enrichment disabled. Enable to add person/company data during bulk verification.")


def _run_smtp_connection_test(host: str, port: int):
    with st.spinner(f"Testing connection to {host}:{port}..."):
        try:
            from verifier.smtp_validator import test_smtp_connection as _test_conn
            result = _test_conn(host, port, False, timeout=5)
            if result["connected"]:
                st.success(f"Connected to {host}:{port} in {result['response_time_ms']:.0f}ms")
                with st.expander("Connection Details"):
                    st.json(result)
            else:
                st.error(f"Failed: {result.get('error', 'Unknown error')}")
        except Exception as e:
            st.error(f"Connection test failed: {e}")


def _render_smtp_status(config):
    st.markdown("**Status**")
    status_items = [
        ("SMTP Verification", "Enabled" if config.enable_smtp_check else "Disabled"),
        ("Test Mode", "Enabled" if config.smtp_test_mode else "Disabled"),
    ]
    if config.smtp_test_mode:
        status_items.append(("Test Host", f"{config.test_smtp_host}:{config.test_smtp_port}"))
    if config.enable_smtp_check and not config.smtp_test_mode:
        status_items.append(("Verifier Domain", config.verifier_domain or "Not configured"))
        email_display = config.verifier_email
        if email_display and "@" in email_display:
            local, domain = email_display.split("@", 1)
            email_display = local[:2] + "***@" + domain
        status_items.append(("Verifier Email", email_display or "Not configured"))
    for label, value in status_items:
        st.caption(f"{label}: **{value}**")


# ── Filters ────────────────────────────────────────────────────────────
def render_filters():
    rdf = st.session_state.results_df
    if rdf is None or rdf.empty:
        return

    filters = SummaryService.get_filter_options(rdf)

    # 1. Final Status
    statuses = filters.get("status", [])
    if statuses:
        selected_statuses = st.multiselect(
            "Final Status", options=statuses,
            default=None, key="filter_status",
        )
    else:
        selected_statuses = None

    # 2. Score range
    score_min = int(rdf["verification_score"].min()) if "verification_score" in rdf.columns else 0
    score_max = int(rdf["verification_score"].max()) if "verification_score" in rdf.columns else 100
    score_range = st.slider(
        "Score Range", min_value=0, max_value=100,
        value=(score_min, score_max), key="filter_score",
    )

    # 3. Domain
    domains = filters.get("domain", [])
    selected_domains = st.multiselect(
        "Domain", options=domains, default=None, key="filter_domain",
    ) if domains else st.text_input("Domain filter (comma-separated)")

    # 4. Provider
    providers = filters.get("provider", [])
    selected_providers = st.multiselect(
        "Provider", options=providers, default=None, key="filter_provider",
    ) if providers else None

    # 5. Disposable
    if "disposable" in rdf.columns:
        disp_filter = st.radio(
            "Disposable", options=["All", "Yes", "No"], index=0,
            horizontal=True, key="filter_disposable",
        )
        disp_filter_val = None if disp_filter == "All" else (disp_filter == "Yes")
    else:
        disp_filter_val = None

    # 6. Free/Public
    if "free_public_email" in rdf.columns:
        free_filter = st.radio(
            "Free/Public", options=["All", "Yes", "No"], index=0,
            horizontal=True, key="filter_free",
        )
        free_filter_val = None if free_filter == "All" else (free_filter == "Yes")
    else:
        free_filter_val = None

    # 7. Role-based
    if "role_based" in rdf.columns:
        role_filter = st.radio(
            "Role-Based", options=["All", "Yes", "No"], index=0,
            horizontal=True, key="filter_role",
        )
        role_filter_val = None if role_filter == "All" else (role_filter == "Yes")
    else:
        role_filter_val = None

    # 8. Catch-All
    if "catch_all" in rdf.columns:
        catch_filter = st.radio(
            "Catch-All", options=["All", "Yes", "No"], index=0,
            horizontal=True, key="filter_catch",
        )
        if catch_filter == "All":
            catch_filter_val = None
        else:
            catch_filter_val = (catch_filter == "Yes")
    else:
        catch_filter_val = None

    # 9. Company match
    if "company_domain_match" in rdf.columns:
        cmp_filter = st.radio(
            "Company Match", options=["All", "Matched", "Not Matched"], index=0,
            horizontal=True, key="filter_company",
        )
        if cmp_filter == "All":
            cmp_filter_val = None
        elif cmp_filter == "Matched":
            cmp_filter_val = True
        else:
            cmp_filter_val = False
    else:
        cmp_filter_val = None

    # 10. SMTP status
    if "smtp_status" in rdf.columns:
        smtp_opts = sorted(rdf["smtp_status"].dropna().unique().tolist())
        smtp_filter = st.multiselect(
            "SMTP Status", options=smtp_opts, default=None, key="filter_smtp",
        ) if smtp_opts else None
    else:
        smtp_filter = None

    # 11. Duplicate
    if "is_duplicate" in rdf.columns:
        dup_filter = st.radio(
            "Duplicate", options=["All", "Yes", "No"], index=0,
            horizontal=True, key="filter_duplicate",
        )
        dup_filter_val = None if dup_filter == "All" else (dup_filter == "Yes")
    else:
        dup_filter_val = None

    # Apply filters
    filtered = SummaryService.apply_filters(
        rdf,
        status_filter=selected_statuses if selected_statuses else None,
        score_range=score_range if score_range != (0, 100) else None,
        domain_filter=selected_domains if selected_domains else None,
        provider_filter=selected_providers if selected_providers else None,
        disposable_filter=disp_filter_val,
        free_filter=free_filter_val,
        role_filter=role_filter_val,
        catch_all_filter=catch_filter_val,
        company_match_filter=cmp_filter_val,
        smtp_filter=smtp_filter if smtp_filter else None,
        duplicate_filter=dup_filter_val,
    )

    if len(filtered) < len(rdf):
        st.caption(f"Showing {len(filtered)} of {len(rdf)} results")
        st.session_state.filtered_df = filtered
    else:
        st.session_state.filtered_df = rdf


# ── Bulk Verification ──────────────────────────────────────────────────
def render_bulk_verification():
    uploaded_file = st.file_uploader(
        "Upload CSV, XLSX, XLS, or TXT",
        type=["csv", "xlsx", "xls", "txt"],
        label_visibility="collapsed",
    )

    if uploaded_file is not None:
        try:
            parsed = parse_upload(uploaded_file, uploaded_file.name, max_rows=VerifierConfig.from_env().max_rows)
            df = parsed.dataframe
            for warning in parsed.warnings or []:
                st.warning(warning)
        except Exception as e:
            st.error(f"Could not read file: {e}")
            return

        if df.empty:
            st.warning("The uploaded file is empty.")
            return

        st.markdown('<div class="white-card">', unsafe_allow_html=True)
        st.markdown("<h3>⚙️ Configure Columns</h3>", unsafe_allow_html=True)

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

        verify_clicked = st.button("Verify Emails", type="primary", use_container_width=True)

        if verify_clicked:
            st.session_state["_bulk_df"] = df
            st.session_state["_email_col"] = email_col
            st.session_state["_company_col"] = company_col
            st.session_state.processing = True
            st.session_state.cancelled = False
            st.session_state.results_df = None
            st.session_state.filtered_df = None
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.processing:
        with st.spinner("Processing..."):
            _run_bulk_verification()

    if st.session_state.results_df is not None and not st.session_state.processing:
        rdf = _get_filtered_or_full()
        _display_bulk_results(rdf)

    if uploaded_file is None and not st.session_state.processing and st.session_state.results_df is None:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">📧</div>
            <h2>Ready to verify emails</h2>
            <p>Upload a CSV or XLSX file containing email addresses to begin.</p>
        </div>
        """, unsafe_allow_html=True)


def _run_bulk_verification():
    if st.session_state.get("_bulk_df") is None:
        st.error("No data to process. Please upload a file first.")
        st.session_state.processing = False
        return

    df = st.session_state["_bulk_df"]
    email_col = st.session_state.get("_email_col", "")
    company_col = st.session_state.get("_company_col", None)

    if not email_col or email_col not in df.columns:
        st.error("Email column not configured. Please re-upload and select a column.")
        st.session_state.processing = False
        return

    progress_bar = st.progress(0, text="Starting verification...")
    status_text = st.empty()

    def progress_callback(processed: int, total: int, extra: dict):
        try:
            if st.session_state.get("cancelled"):
                return
            pct = processed / total if total > 0 else 0
            progress_bar.progress(min(pct, 1.0), text=f"Verified {processed} of {total} emails ({processed/total*100:.0f}%)")
        except Exception:
            pass

    config = st.session_state.config
    enrichment_enabled = st.session_state.get("enrichment_enabled", False)
    processor = BulkProcessor(config=config, progress_callback=progress_callback, enrichment_enabled=enrichment_enabled)

    try:
        result_df = processor.process(df, email_col, company_col)
        st.session_state.results_df = result_df
        st.session_state.filtered_df = result_df
        progress_bar.progress(1.0, text="Done!")
    except Exception as e:
        st.error(f"Processing error: {e}")
        st.error(traceback.format_exc())
    finally:
        progress_bar.empty()
        status_text.empty()
        st.session_state.processing = False
        st.session_state.cancelled = False
        st.rerun()


def _get_filtered_or_full() -> pd.DataFrame:
    if "filtered_df" in st.session_state and st.session_state.filtered_df is not None:
        return st.session_state.filtered_df
    if st.session_state.results_df is not None:
        return st.session_state.results_df
    return pd.DataFrame()


def _display_bulk_results(rdf: pd.DataFrame):
    # ── Dashboard metrics ──
    summary = SummaryService.compute_summary(rdf)

    st.markdown('<div class="white-card">', unsafe_allow_html=True)
    st.markdown("<h3>📊 Dashboard</h3>", unsafe_allow_html=True)

    metrics = [
        ("metric-total", "Total Uploaded", summary["total_uploaded"]),
        ("metric-unique", "Unique", summary["total_unique"]),
        ("metric-verified", "Valid", summary["valid_count"]),
        ("metric-average", "Likely Valid", summary["likely_valid_count"]),
        ("metric-risky", "Risky", summary["risky_count"]),
        ("metric-invalid", "Invalid", summary["invalid_count"]),
        ("metric-unknown", "Unknown", summary["unknown_count"]),
        ("metric-disposable", "Disposable", summary["disposable_count"]),
        ("metric-catchall", "Catch-All", summary["catch_all_count"]),
        ("metric-role", "Role-Based", summary["role_based_count"]),
        ("metric-duplicate", "Duplicates", summary["duplicate_count"]),
        ("metric-nomx", "No MX", summary["no_mx_count"]),
        ("metric-smtp-blocked", "SMTP Blocked", summary["smtp_blocked_count"]),
        ("metric-score", "Avg Score", summary["average_verification_score"]),
    ]

    st.markdown('<div class="metric-grid-dense">', unsafe_allow_html=True)
    for cls, label, value in metrics:
        st.markdown(
            f'<div class="metric-card-dense {cls}">'
            f'<div class="metric-label">{label}</div>'
            f'<div class="metric-value">{value}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Results table ──
    st.markdown('<div class="white-card">', unsafe_allow_html=True)
    st.markdown("<h3>✅ Results</h3>", unsafe_allow_html=True)

    display_df = _prepare_display_df(rdf)
    display_cols = [c for c in DISPLAY_COLUMN_ORDER if c in display_df.columns]
    display_html = display_df[display_cols].copy()

    if "Verification Status" in display_html.columns:
        display_html["Verification Status"] = display_html["Verification Status"].apply(badge)

    html = display_html.to_html(
        classes="results-table",
        escape=False,
        index=False,
        table_id="tbl",
    )
    st.markdown(f'<div class="table-wrap">{html}</div>', unsafe_allow_html=True)
    st.caption(f"Showing {len(rdf)} result(s)")

    # ── Download buttons ──
    st.markdown("<h3>📥 Download</h3>", unsafe_allow_html=True)
    export_df = _get_export_df(rdf)

    dl_cols = st.columns(5)
    download_options = [
        ("Complete CSV", ExportService.to_csv(export_df), "text/csv", ".csv"),
        ("Complete XLSX", ExportService.to_excel(rdf), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
        ("Valid Only", ExportService.to_filtered_csv(rdf, "Valid"), "text/csv", "_valid.csv"),
        ("Risky Only", ExportService.to_filtered_csv(rdf, "Risky"), "text/csv", "_risky.csv"),
        ("Invalid Only", ExportService.to_filtered_csv(rdf, "Invalid"), "text/csv", "_invalid.csv"),
    ]
    for i, (label, data, mime, suffix) in enumerate(download_options):
        with dl_cols[i]:
            fname = f"email_verification_{suffix.lstrip('.')}" if suffix.startswith(".") else f"email_verification_{suffix}"
            st.download_button(
                label,
                data=data,
                file_name=fname,
                mime=mime,
                use_container_width=True,
            )

    dl_cols2 = st.columns(4)
    extra_downloads = [
        ("Unknown Only", ExportService.to_filtered_csv(rdf, "Unknown"), "_unknown.csv"),
        ("Disposable Only", ExportService.to_filtered_csv(rdf[ rdf["disposable"] == True ] if "disposable" in rdf.columns else rdf, None), "_disposable.csv"),
        ("Duplicate Only", ExportService.to_csv(rdf[rdf["is_duplicate"] == True] if "is_duplicate" in rdf.columns and rdf["is_duplicate"].any() else rdf.head(0)), "_duplicates.csv"),
        ("Summary Report", ExportService.to_excel(rdf), "_summary.xlsx"),
    ]
    for i, (label, data, suffix) in enumerate(extra_downloads):
        with dl_cols2[i]:
            st.download_button(
                label,
                data=data,
                file_name=f"email_verification_{suffix}",
                mime="text/csv" if suffix.endswith(".csv") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)


# ── Single Email Verification ──────────────────────────────────────────
def render_single_verification():
    st.markdown('<div class="white-card">', unsafe_allow_html=True)
    st.markdown("<h3>📧 Verify a Single Email</h3>", unsafe_allow_html=True)

    email_input = st.text_input(
        "Email Address",
        placeholder="user@example.com",
        label_visibility="visible",
        help="Enter a single email address to verify",
    )

    company_domain = st.text_input(
        "Company Domain (optional)",
        placeholder="example.com",
        label_visibility="visible",
        help="Optional company domain to check for domain match",
    )

    verify_col1, verify_col2 = st.columns([3, 1])
    with verify_col1:
        clicked = st.button("Verify Email", type="primary", use_container_width=True)

    if clicked:
        if not email_input or not email_input.strip():
            st.warning("Please enter an email address.")
            return

        with st.spinner("Running verification pipeline..."):
            try:
                config = st.session_state.config
                pipeline = VerificationPipeline(config=config)
                result = pipeline.verify(email_input.strip(), company_domain=company_domain.strip() if company_domain.strip() else None)
                st.session_state.single_result = result
            except Exception as e:
                st.error(f"Verification error: {e}")
                st.error(traceback.format_exc())
                return

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Display single result ──
    if st.session_state.single_result is not None:
        result = st.session_state.single_result
        _display_single_result(result)


# ── Email Intelligence Tab ────────────────────────────────────────────
def render_email_intelligence():
    st.markdown('<div class="white-card">', unsafe_allow_html=True)
    st.markdown("<h3>🔍 Email Intelligence</h3>", unsafe_allow_html=True)
    st.caption("Search publicly available information to enrich email addresses. No private data is accessed.")

    email_input = st.text_input(
        "Email Address",
        placeholder="vaibhav@safebooksglobal.com",
        key="intel_email",
        help="Enter an email address to search for publicly available information",
    )

    if st.button("🔍 Look Up Email", type="primary", use_container_width=True, key="btn_intel"):
        if not email_input or not email_input.strip():
            st.warning("Please enter an email address.")
            return

        with st.spinner("Searching public sources..."):
            try:
                result = _run_enrichment(email_input.strip())
                st.session_state.intel_result = result
            except Exception as e:
                st.error(f"Enrichment error: {e}")
                st.error(traceback.format_exc())
                return

    st.markdown("</div>", unsafe_allow_html=True)

    if "intel_result" in st.session_state and st.session_state.intel_result is not None:
        _display_intel_result(st.session_state.intel_result)


def _run_enrichment(email: str) -> EnrichmentResult:
    """Run the full enrichment pipeline for a single email."""
    import time
    start = time.monotonic()
    result = EnrichmentResult(email=email)

    local_part = email.split("@")[0] if "@" in email else ""
    domain = email.split("@")[1] if "@" in email else ""

    # Step 1: Extract name from email
    from enrichment.search_engine import extract_name_from_email
    first_name, last_name = extract_name_from_email(local_part)

    # Step 2: Look up company
    company = None
    if domain:
        try:
            company = lookup_company(domain)
        except Exception as e:
            st.warning(f"Company lookup error: {e}")

    # Step 3: Look up person
    person = None
    try:
        person = lookup_person(email, company_profile=company)
    except Exception as e:
        st.warning(f"Person lookup error: {e}")

    # Step 4: Generate summary
    ai_summary = ""
    try:
        ai_summary = generate_enrichment_summary(person, company)
    except Exception:
        pass

    result.person = person
    result.company = company
    result.ai_summary = ai_summary
    result.enriched = bool(person or company)
    result.processing_time_ms = round((time.monotonic() - start) * 1000, 2)

    return result


def _display_intel_result(result: EnrichmentResult):
    """Display enrichment results in the Streamlit UI."""
    st.markdown('<div class="white-card">', unsafe_allow_html=True)
    st.markdown("<h3>📋 Intelligence Results</h3>", unsafe_allow_html=True)

    # ── Step 1: Email Parsing ──
    local_part = result.email.split("@")[0] if "@" in result.email else ""
    domain = result.email.split("@")[1] if "@" in result.email else ""
    st.markdown("**Email Parsing:**")
    parse_html = f"""
    <table class="results-table">
    <tr><td><strong>Email</strong></td><td>{result.email}</td></tr>
    <tr><td><strong>Local Part</strong></td><td>{local_part}</td></tr>
    <tr><td><strong>Domain</strong></td><td>{domain}</td></tr>
    </table>
    """
    st.markdown(f'<div class="table-wrap">{parse_html}</div>', unsafe_allow_html=True)

    # ── Person Profile ──
    if result.person:
        p = result.person
        conf_color = {"High": "#16a34a", "Medium": "#2563eb", "Low": "#d97706", "Unknown": "#6b7280"}
        color = conf_color.get(p.confidence_level, "#6b7280")

        st.markdown(f"**Person Profile** — <span style='color:{color};font-weight:700'>{p.confidence_level} Confidence ({p.confidence:.0f}%)</span>", unsafe_allow_html=True)

        person_rows = []
        if p.full_name:
            person_rows.append(("Full Name", p.full_name))
        if p.first_name:
            person_rows.append(("First Name", p.first_name))
        if p.last_name:
            person_rows.append(("Last Name", p.last_name))
        if p.job_title:
            person_rows.append(("Job Title", p.job_title))
        if p.department:
            person_rows.append(("Department", p.department))
        if p.company_name:
            person_rows.append(("Company", p.company_name))
        if p.phone:
            person_rows.append(("Phone", p.phone))
        if p.country:
            person_rows.append(("Country", p.country))
        if p.city:
            person_rows.append(("City", p.city))

        social_rows = []
        if p.linkedin_url:
            social_rows.append(("LinkedIn", f'<a href="{p.linkedin_url}" target="_blank">{p.linkedin_url}</a>'))
        if p.github_url:
            social_rows.append(("GitHub", f'<a href="{p.github_url}" target="_blank">{p.github_url}</a>'))
        if p.twitter_url:
            social_rows.append(("Twitter/X", f'<a href="{p.twitter_url}" target="_blank">{p.twitter_url}</a>'))
        if p.facebook_url:
            social_rows.append(("Facebook", f'<a href="{p.facebook_url}" target="_blank">{p.facebook_url}</a>'))
        if p.instagram_url:
            social_rows.append(("Instagram", f'<a href="{p.instagram_url}" target="_blank">{p.instagram_url}</a>'))

        if person_rows or social_rows:
            html = '<table class="results-table"><thead><tr><th>Property</th><th>Value</th></tr></thead><tbody>'
            for label, value in person_rows:
                html += f"<tr><td><strong>{label}</strong></td><td>{value}</td></tr>"
            for label, value in social_rows:
                html += f"<tr><td><strong>{label}</strong></td><td>{value}</td></tr>"
            html += "</tbody></table>"
            st.markdown(f'<div class="table-wrap">{html}</div>', unsafe_allow_html=True)

        if p.sources:
            st.caption(f"Sources: {', '.join(p.sources[:10])}")

    # ── Company Profile ──
    if result.company:
        c = result.company
        st.markdown("**Company Profile:**")

        company_rows = []
        if c.name:
            company_rows.append(("Company Name", c.name))
        if c.domain:
            company_rows.append(("Domain", c.domain))
        if c.description:
            company_rows.append(("Description", c.description[:300]))
        if c.linkedin_url:
            company_rows.append(("LinkedIn", f'<a href="{c.linkedin_url}" target="_blank">{c.linkedin_url}</a>'))
        if c.crunchbase_url:
            company_rows.append(("Crunchbase", f'<a href="{c.crunchbase_url}" target="_blank">{c.crunchbase_url}</a>'))
        if c.country:
            company_rows.append(("Country", c.country))
        if c.city:
            company_rows.append(("City", c.city))
        if c.phone:
            company_rows.append(("Phone", c.phone))
        if c.email:
            company_rows.append(("Email", c.email))
        if c.domain_age:
            company_rows.append(("Domain Age", c.domain_age))
        if c.domain_registrar:
            company_rows.append(("Registrar", c.domain_registrar))
        if c.logo_url:
            company_rows.append(("Logo", f'<img src="{c.logo_url}" height="40" />'))
        if c.employees:
            company_rows.append(("Employees Found", ", ".join(c.employees[:10])))

        if company_rows:
            html = '<table class="results-table"><thead><tr><th>Property</th><th>Value</th></tr></thead><tbody>'
            for label, value in company_rows:
                html += f"<tr><td><strong>{label}</strong></td><td>{value}</td></tr>"
            html += "</tbody></table>"
            st.markdown(f'<div class="table-wrap">{html}</div>', unsafe_allow_html=True)

    # ── AI Summary ──
    if result.ai_summary:
        st.markdown('<div class="white-card white-card-sm">', unsafe_allow_html=True)
        st.markdown("<h3>📝 AI Summary</h3>", unsafe_allow_html=True)
        st.markdown(f"<p>{result.ai_summary}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Meta ──
    st.caption(f"Processing time: {result.processing_time_ms:.0f}ms | Enriched: {'Yes' if result.enriched else 'No'}")
    st.markdown("</div>", unsafe_allow_html=True)


def _display_single_result(result: VerificationResult):
    st.markdown('<div class="white-card">', unsafe_allow_html=True)
    st.markdown("<h3>📋 Verification Result</h3>", unsafe_allow_html=True)

    # Overview
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f'<div class="metric-card {_metric_class(result.verification_status)}">'
            f'<div class="metric-label">Status</div>'
            f'<div class="metric-value">{badge(result.verification_status)}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div class="metric-card metric-score">'
            f'<div class="metric-label">Score</div>'
            f'<div class="metric-value">{result.verification_score}/100</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f'<div class="metric-card {_conf_class(result.confidence_level)}">'
            f'<div class="metric-label">Confidence</div>'
            f'<div class="metric-value">{result.confidence_level}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f'<div class="metric-card {_risk_class(result.risk_level)}">'
            f'<div class="metric-label">Risk</div>'
            f'<div class="metric-value">{result.risk_level}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

    # Email info
    info_rows = [
        ("Original Email", result.original_email),
        ("Normalized Email", result.normalized_email or "—"),
        ("Domain", result.domain or "—"),
        ("Provider", result.mx_provider or "Unknown"),
        ("Processing Time", f"{result.processing_time_ms} ms"),
    ]
    if result.suggested_domain:
        info_rows.append(("Suggested Domain", result.suggested_domain))

    info_html = '<table class="results-table" style="margin-top: 1rem;">'
    info_html += "<thead><tr><th>Property</th><th>Value</th></tr></thead><tbody>"
    for label, value in info_rows:
        info_html += f"<tr><td><strong>{label}</strong></td><td>{value}</td></tr>"
    info_html += "</tbody></table>"
    st.markdown(f'<div class="table-wrap">{info_html}</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Stage-by-stage detailed results ──
    if result.stage_results:
        st.markdown('<div class="white-card">', unsafe_allow_html=True)
        st.markdown("<h3>🔬 Stage-by-Stage Analysis</h3>", unsafe_allow_html=True)

        for stage in result.stage_results:
            _render_stage_card(stage, result)

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Score breakdown ──
    if result.score_reasons:
        st.markdown('<div class="white-card white-card-sm">', unsafe_allow_html=True)
        st.markdown("<h3>📊 Score Breakdown</h3>", unsafe_allow_html=True)
        for reason in result.score_reasons:
            prefix = "+" if reason.startswith("+") else reason[:1]
            if prefix == "+":
                st.markdown(f'<p style="color:#16a34a;margin:0.2rem 0;">✅ {reason}</p>', unsafe_allow_html=True)
            elif prefix == "-":
                st.markdown(f'<p style="color:#dc2626;margin:0.2rem 0;">❌ {reason}</p>', unsafe_allow_html=True)
            else:
                st.markdown(f'<p style="color:#64748b;margin:0.2rem 0;">{reason}</p>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Notes ──
    if result.notes:
        st.markdown(f'<div class="white-card white-card-sm"><p><strong>Notes:</strong> {result.notes}</p></div>', unsafe_allow_html=True)

    # ── New verification button ──
    if st.button("🔄 Verify Another Email", use_container_width=True):
        st.session_state.single_result = None
        st.rerun()


def _render_stage_card(stage: PipelineStage, result: VerificationResult):
    stage_name = stage.name.replace("_", " ").title()
    is_success = stage.success
    duration = stage.duration_ms

    if is_success:
        border_cls = "stage-pass"
        status_icon = "✅"
        status_label = "Pass"
    elif stage_name.lower() in ("company match", "free provider", "provider"):
        border_cls = "stage-warn"
        status_icon = "⚠️"
        status_label = "Skipped"
    else:
        border_cls = "stage-fail"
        status_icon = "❌"
        status_label = "Fail"

    stage_class = f"stage-card {border_cls}"

    # Build detail lines based on stage
    details = []
    if stage.error:
        details.append(("Error", stage.error))

    data = stage.data or {}
    if stage.name == "normalize":
        if data.get("normalized_email"):
            details.append(("Normalized", data["normalized_email"]))
    elif stage.name == "syntax":
        details.append(("Valid", "Yes" if data.get("is_valid") else "No"))
        if data.get("error"):
            details.append(("Error", data["error"]))
    elif stage.name == "typo":
        details.append(("Typo Detected", "Yes" if data.get("is_typo") else "No"))
        if data.get("suggested"):
            details.append(("Suggested", data["suggested"]))
    elif stage.name == "dns":
        details.append(("Status", result.dns_status))
        details.append(("MX Count", data.get("mx_count", 0)))
        if data.get("null_mx"):
            details.append(("Null MX", "Yes"))
    elif stage.name == "provider":
        details.append(("Provider", data.get("provider", "Unknown")))
    elif stage.name == "disposable":
        details.append(("Disposable", "Yes" if data.get("disposable") else "No"))
    elif stage.name == "free_provider":
        details.append(("Free/Public", "Yes" if data.get("free_public") else "No"))
    elif stage.name == "role":
        details.append(("Role-Based", "Yes" if data.get("is_role") else "No"))
        if data.get("category"):
            details.append(("Category", data["category"]))
    elif stage.name == "smtp":
        details.append(("Status", result.smtp_status))
        if result.smtp_code:
            details.append(("Code", str(result.smtp_code)))
        if result.smtp_message:
            details.append(("Message", result.smtp_message))
    elif stage.name == "catch_all":
        details.append(("Status", data.get("status", "Not Tested")))
        details.append(("Confidence", f'{data.get("confidence", 0)*100:.0f}%' if data.get("confidence") else "—"))
    elif stage.name == "website":
        details.append(("Reachable", "Yes" if data.get("reachable") else "No"))
        if data.get("status"):
            details.append(("Status", data["status"]))
    elif stage.name == "company_match":
        match_val = data.get("match")
        if match_val is None:
            details.append(("Match", "Not Checked"))
        elif match_val is True:
            details.append(("Match", "✅ Matched"))
        else:
            details.append(("Match", "❌ Mismatch"))
    elif stage.name == "scoring":
        details.append(("Score", str(data.get("score", 0))))
        details.append(("Status", data.get("status", "Unknown")))

    detail_html = "".join(
        f'<div class="stage-detail"><strong>{k}:</strong> {v}</div>'
        for k, v in details
    )

    st.markdown(
        f'<div class="{stage_class}">'
        f'<div class="stage-header">'
        f'<div><span class="stage-icon">{status_icon}</span>'
        f'<span class="stage-name">{stage_name}</span></div>'
        f'<div><span class="stage-status">{status_label}</span>'
        f'<span class="stage-duration"> &middot; {duration:.1f}ms</span></div>'
        f"</div>"
        f"{detail_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


def _metric_class(status: str) -> str:
    m = {
        "Valid": "metric-verified",
        "Likely Valid": "metric-average",
        "Risky": "metric-risky",
        "Invalid": "metric-invalid",
        "Unknown": "metric-unknown",
    }
    return m.get(status, "metric-total")


def _conf_class(level: str) -> str:
    m = {"High": "metric-verified", "Medium": "metric-average", "Low": "metric-risky", "Very Low": "metric-invalid"}
    return m.get(level, "metric-unknown")


def _risk_class(level: str) -> str:
    m = {"Low": "metric-verified", "Medium": "metric-average", "High": "metric-risky", "Critical": "metric-invalid"}
    return m.get(level, "metric-unknown")





# ── Entry point ────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
