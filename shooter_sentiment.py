"""
Shooter Market Intelligence — SEGA-branded Streamlit App
=========================================================
Run with:  streamlit run shooter_intel.py

Required:  pip install streamlit requests pandas plotly anthropic reportlab markdown
"""

import time
import re
import io
import json
from datetime import datetime, timedelta
from collections import Counter
from pathlib import Path
import os

import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    import markdown as _md_lib
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors as _rl_colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Preformatted
    import io as _rl_io
    _REPORTLAB_AVAILABLE = True
except ImportError:
    _REPORTLAB_AVAILABLE = False

try:
    import anthropic as _anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="SEGA Shooter Intel",
    page_icon=":material/target:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# SEGA BRAND STYLES
# ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;700;800;900&family=Poppins:wght@300;400;500;600&display=swap');

:root,
html[data-theme="light"],
html[data-theme="dark"],
[data-theme="light"],
[data-theme="dark"] {
    color-scheme: dark !important;
    --bg:           #0a0c1a;
    --surface:      #0f1120;
    --surface2:     #141728;
    --surface3:     #1a1e30;
    --border:       #232640;
    --border-hi:    #323760;
    --blue:         #4080ff;
    --blue-lo:      #1a3acc;
    --blue-glow:    rgba(64,128,255,0.16);
    --blue-glow-hi: rgba(64,128,255,0.32);
    --text:         #eef0fa;
    --text-dim:     #b8bcd4;
    --muted:        #5a5f82;
    --pos:          #20c65a;
    --pos-dim:      rgba(32,198,90,0.14);
    --neg:          #ff3d52;
    --neg-dim:      rgba(255,61,82,0.14);
    --amber:        #ffb938;
    --amber-dim:    rgba(255,185,56,0.14);
    --purple:       #a855f7;
    --purple-dim:   rgba(168,85,247,0.14);
}

html, body {
    background: var(--bg) !important;
    color: var(--text) !important;
    color-scheme: dark !important;
}
.stApp,
.stApp > div,
section[data-testid="stAppViewContainer"],
section[data-testid="stAppViewContainer"] > div,
div[data-testid="stMain"],
div[data-testid="stVerticalBlock"],
div[data-testid="stHorizontalBlock"],
.main .block-container,
.block-container {
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

*, *::before, *::after { font-family: 'Poppins', sans-serif; box-sizing: border-box; }

p, span, div, li, td, th, label,
h1, h2, h3, h4, h5, h6,
.stMarkdown, .stMarkdown p, .stMarkdown span,
[data-testid="stText"],
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] strong,
[data-testid="stMarkdownContainer"] em,
[class*="css"] { color: var(--text) !important; }

.stCaption, [data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p { color: var(--muted) !important; }

code { background: var(--surface3) !important; color: var(--blue) !important; padding: 0.1em 0.4em; border-radius: 3px; }

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 2.5rem 4rem !important; max-width: 1440px !important; }

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-hi); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--muted); }

/* ══ TOP NAV ══ */
.topbar {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 0.8rem 2.5rem;
    margin: 0 -2.5rem 1.75rem;
    display: flex;
    align-items: center;
    gap: 1.25rem;
    position: relative;
}
.topbar::after {
    content: '';
    position: absolute;
    bottom: -1px; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, var(--blue) 0%, rgba(64,128,255,0) 55%);
}
.topbar-logo { font-family: 'Inter Tight', sans-serif; font-size: 0.95rem; font-weight: 900; color: var(--text) !important; letter-spacing: 0.12em; text-transform: uppercase; }
.topbar-logo .seg { color: var(--blue); }
.topbar-divider { width: 1px; height: 18px; background: var(--border-hi); flex-shrink: 0; }
.topbar-label { font-size: 0.6rem; font-weight: 600; color: var(--muted) !important; letter-spacing: 0.2em; text-transform: uppercase; }
.topbar-pill { margin-left: auto; background: var(--blue-glow); border: 1px solid rgba(64,128,255,0.28); border-radius: 20px; padding: 0.18rem 0.7rem; font-size: 0.58rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--blue) !important; }

/* ══ HERO ══ */
.hero { padding: 1.5rem 0 0.75rem; }
.hero-title { font-family: 'Inter Tight', sans-serif; font-size: 2.4rem; font-weight: 900; line-height: 1.05; color: var(--text) !important; letter-spacing: -0.03em; margin-bottom: 0.5rem; }
.hero-title .accent { color: var(--blue); }
.hero-sub { font-size: 0.87rem; font-weight: 300; color: var(--muted) !important; max-width: 580px; line-height: 1.65; }

/* ══ QUERY BLOCK ══ */
.query-block {
    background: var(--surface);
    border: 1px solid var(--border);
    border-top: 2px solid var(--blue);
    border-radius: 0 0 10px 10px;
    padding: 1.4rem 1.75rem 1.25rem;
    margin: 1.25rem 0 0;
}
.field-label { font-size: 0.58rem; font-weight: 700; letter-spacing: 0.22em; text-transform: uppercase; color: var(--muted) !important; margin-bottom: 0.3rem; }

/* ══ FORM CONTROLS ══ */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    color: var(--text) !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.88rem !important;
    caret-color: var(--blue) !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 3px var(--blue-glow) !important;
}
input::placeholder, textarea::placeholder { color: var(--muted) !important; opacity: 0.6 !important; }

div[data-baseweb="select"] > div,
div[data-baseweb="select"] > div > div {
    background: var(--bg) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
}
div[data-baseweb="select"] svg { fill: var(--muted) !important; }
div[data-baseweb="select"] span,
div[data-baseweb="select"] input { color: var(--text) !important; }
div[data-baseweb="menu"],
div[data-baseweb="popover"] {
    background: var(--surface2) !important;
    border: 1px solid var(--border-hi) !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5) !important;
}
div[data-baseweb="menu"] li,
div[data-baseweb="menu"] [role="option"] { color: var(--text) !important; background: transparent !important; }
div[data-baseweb="menu"] li:hover,
div[data-baseweb="menu"] [aria-selected="true"] { background: var(--surface3) !important; color: var(--text) !important; }

.stCheckbox > label,
.stCheckbox > label > span,
.stCheckbox label p,
[data-testid="stCheckbox"] span,
[data-testid="stCheckbox"] p { color: var(--text) !important; font-size: 0.84rem !important; }

/* ══ BUTTONS ══ */
.stButton > button {
    background: var(--blue) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'Inter Tight', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    padding: 0.5rem 1.5rem !important;
    transition: background 0.15s, box-shadow 0.15s, transform 0.1s !important;
    box-shadow: 0 2px 10px rgba(64,128,255,0.3) !important;
}
.stButton > button:hover {
    background: #2d6aee !important;
    box-shadow: 0 4px 18px rgba(64,128,255,0.45) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active { transform: translateY(0px) !important; }

.stDownloadButton > button {
    background: transparent !important;
    color: var(--blue) !important;
    border: 1px solid rgba(64,128,255,0.35) !important;
    border-radius: 6px !important;
    font-family: 'Inter Tight', sans-serif !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    transition: all 0.15s !important;
    box-shadow: none !important;
}
.stDownloadButton > button:hover {
    background: var(--blue-glow) !important;
    border-color: var(--blue) !important;
    transform: none !important;
}

/* ══ METRIC CARDS ══ */
.metric-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.2rem 1.4rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s, box-shadow 0.2s;
    height: 100%;
}
.metric-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 80px;
    background: linear-gradient(180deg, rgba(64,128,255,0.04) 0%, transparent 100%);
    pointer-events: none;
}
.metric-card.blue-top  { border-top: 2px solid var(--blue); }
.metric-card.pos-top   { border-top: 2px solid var(--pos); }
.metric-card.amber-top { border-top: 2px solid var(--amber); }
.metric-card.purple-top{ border-top: 2px solid var(--purple); }
.metric-card:hover { border-color: var(--border-hi); box-shadow: 0 4px 24px rgba(0,0,0,0.3); }
.metric-label { font-size: 0.58rem; font-weight: 700; letter-spacing: 0.22em; text-transform: uppercase; color: var(--muted) !important; margin-bottom: 0.45rem; }
.metric-value { font-family: 'Inter Tight', sans-serif; font-size: 2.1rem; font-weight: 900; color: var(--text) !important; line-height: 1; margin-bottom: 0.25rem; letter-spacing: -0.025em; }
.metric-sub { font-size: 0.69rem; color: var(--muted) !important; font-weight: 300; }

/* ══ SECTION HEADER ══ */
.section-header {
    font-family: 'Inter Tight', sans-serif;
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: var(--text-dim) !important;
    margin: 1.75rem 0 0.9rem;
    padding-bottom: 0.55rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 0.55rem;
}
.section-header .dot { width: 5px; height: 5px; background: var(--blue); border-radius: 1px; display: inline-block; flex-shrink: 0; box-shadow: 0 0 5px var(--blue); }

/* ══ PROGRESS BARS ══ */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, var(--blue) 0%, #7ab0ff 100%) !important;
    border-radius: 4px !important;
}

/* ══ TABS ══ */
.stTabs [data-baseweb="tab-list"] {
    gap: 0 !important;
    border-bottom: 1px solid var(--border) !important;
    background: transparent !important;
    margin-bottom: 0.25rem !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--muted) !important;
    font-family: 'Inter Tight', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.68rem !important;
    letter-spacing: 0.16em !important;
    text-transform: uppercase !important;
    padding: 0.6rem 1.1rem !important;
    border-bottom: 2px solid transparent !important;
    transition: color 0.15s !important;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--text-dim) !important; }
.stTabs [aria-selected="true"] { color: var(--text) !important; border-bottom-color: var(--blue) !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 0.5rem !important; }

/* ══ EXPANDERS ══ */
[data-testid="stExpander"],
details[data-testid="stExpander"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    overflow: hidden;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary div { color: var(--text) !important; background: var(--surface) !important; }
[data-testid="stExpanderDetails"],
[data-testid="stExpanderDetails"] > div { background: var(--surface) !important; color: var(--text) !important; }

/* ══ DATA TABLE ══ */
[data-testid="stDataFrame"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    overflow: hidden;
}

/* ══ ALERTS ══ */
[data-testid="stAlert"],
div[data-baseweb="notification"] {
    background: var(--surface2) !important;
    border: 1px solid var(--border-hi) !important;
    border-radius: 6px !important;
    color: var(--text) !important;
}
[data-testid="stAlert"] p,
[data-testid="stAlert"] span { color: var(--text) !important; }

/* ══ SPINNER ══ */
[data-testid="stSpinner"] p { color: var(--text) !important; }

/* ══ INSIGHT CARD (query preset) ══ */
.insight-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--blue);
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
    cursor: pointer;
    transition: border-color 0.15s, box-shadow 0.15s;
}
.insight-card:hover { border-left-color: #7ab0ff; box-shadow: 0 4px 20px rgba(64,128,255,0.15); }
.insight-card-title { font-family: 'Inter Tight', sans-serif; font-weight: 800; font-size: 0.82rem; color: var(--text) !important; letter-spacing: 0.04em; margin-bottom: 0.3rem; }
.insight-card-desc { font-size: 0.74rem; color: var(--muted) !important; line-height: 1.55; }

/* ══ TAG BADGE ══ */
.tag { display: inline-block; background: var(--blue-glow); border: 1px solid rgba(64,128,255,0.28); border-radius: 4px; padding: 0.1rem 0.5rem; font-size: 0.6rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--blue) !important; margin-right: 0.35rem; }
.tag.amber { background: var(--amber-dim); border-color: rgba(255,185,56,0.28); color: var(--amber) !important; }
.tag.pos   { background: var(--pos-dim);   border-color: rgba(32,198,90,0.28);  color: var(--pos)   !important; }
.tag.purple{ background: var(--purple-dim);border-color: rgba(168,85,247,0.28); color: var(--purple)!important; }

/* ══ EMPTY STATE ══ */
.empty-state {
    margin-top: 3.5rem;
    text-align: center;
    padding: 4rem 2rem;
    border: 1px dashed var(--border-hi);
    border-radius: 12px;
    background: radial-gradient(ellipse at 50% 0%, rgba(64,128,255,0.05) 0%, transparent 65%);
}
.empty-title { font-family: 'Inter Tight', sans-serif; font-size: 2rem; font-weight: 900; color: var(--border-hi) !important; letter-spacing: -0.02em; margin-bottom: 0.7rem; }
.empty-sub { font-size: 0.86rem; color: var(--muted) !important; max-width: 380px; margin: 0 auto; line-height: 1.75; }

/* ══ FOOTER ══ */
.footer {
    margin-top: 4rem;
    padding-top: 1.25rem;
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.footer-brand { font-family: 'Inter Tight', sans-serif; font-weight: 900; font-size: 0.7rem; color: var(--border-hi) !important; letter-spacing: 0.14em; text-transform: uppercase; }
.footer-note { font-size: 0.63rem; color: var(--muted) !important; }

/* ══ CHAT ══ */
[data-testid="stChatMessage"] { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; }
[data-testid="stChatInput"] > div { background: var(--surface2) !important; border-color: var(--border-hi) !important; }
[data-testid="stChatInput"] textarea { color: var(--text) !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# CONSTANTS & DATA
# ─────────────────────────────────────────────────────────────

PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Poppins, sans-serif", color="#eef0fa"),
    margin=dict(l=10, r=10, t=30, b=10),
)

# Top 10 shooters on Steam (source: SteamDB live charts, March 2026)
SHOOTER_ROSTER = [
    {"app_id": 730,     "name": "Counter-Strike 2",    "sub": "Tactical / Competitive", "publisher": "Valve",            "f2p": True},
    {"app_id": 578080,  "name": "PUBG: Battlegrounds", "sub": "Battle Royale",          "publisher": "Krafton",          "f2p": True},
    {"app_id": 1808500, "name": "ARC Raiders",         "sub": "Extraction Shooter",     "publisher": "Embark Studios",   "f2p": False},
    {"app_id": 252490,  "name": "Rust",                "sub": "Open World / PvP",       "publisher": "Facepunch",        "f2p": False},
    {"app_id": 2767030, "name": "Marvel Rivals",       "sub": "Hero Shooter",           "publisher": "NetEase Games",    "f2p": True},
    {"app_id": 271590,  "name": "Grand Theft Auto V",  "sub": "Open World / Action",    "publisher": "Rockstar Games",   "f2p": False},
    {"app_id": 236390,  "name": "War Thunder",         "sub": "Vehicle Combat / MMO",   "publisher": "Gaijin",           "f2p": True},
    {"app_id": 1172470, "name": "Apex Legends",        "sub": "Battle Royale / Hero",   "publisher": "EA / Respawn",     "f2p": True},
    {"app_id": 230410,  "name": "Warframe",            "sub": "Looter Shooter / Co-op", "publisher": "Digital Extremes", "f2p": True},
    {"app_id": 3240220, "name": "GTA V Enhanced",      "sub": "Open World / Action",    "publisher": "Rockstar Games",   "f2p": False},
]

# Folder containing SteamDB CSVs, named steamdb_chart_{appid}.csv
# Resolve DATA_DIR: check next to script first, then cwd/data, then cwd
def _resolve_data_dir() -> Path:
    candidates = [
        Path(__file__).parent / "data",
        Path.cwd() / "data",
        Path.cwd(),
    ]
    for p in candidates:
        if p.exists() and list(p.glob("steamdb_chart_*.csv")):
            return p
    return Path(__file__).parent / "data"

DATA_DIR = _resolve_data_dir()

# Steam CCU endpoint
CCU_URL = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"

# ─────────────────────────────────────────────────────────────
# STEAMDB HISTORICAL CSV LOADER
# ─────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_all_historical() -> dict[int, pd.DataFrame]:
    """
    Loads all SteamDB CSVs from the /data folder at startup.
    Files must be named steamdb_chart_{appid}.csv
    Returns a dict of {app_id: monthly_df} where monthly_df has columns:
        month (Period), peak_ccu, avg_ccu
    """
    historical: dict[int, pd.DataFrame] = {}
    if not DATA_DIR.exists():
        return historical

    for csv_path in sorted(DATA_DIR.glob("steamdb_chart_*.csv")):
        try:
            app_id = int(csv_path.stem.replace("steamdb_chart_", ""))
        except ValueError:
            continue
        try:
            df = pd.read_csv(csv_path, encoding="utf-8-sig")
            df.columns = [c.strip().strip('"') for c in df.columns]
            df["DateTime"] = pd.to_datetime(df["DateTime"], errors="coerce")
            df = df.dropna(subset=["DateTime"])
            df["Players"] = pd.to_numeric(df["Players"], errors="coerce")
            df["Average Players"] = pd.to_numeric(df["Average Players"], errors="coerce")
            df["month"] = df["DateTime"].dt.to_period("M")

            monthly = (
                df.groupby("month")
                .agg(peak_ccu=("Players", "max"), avg_ccu=("Average Players", "mean"))
                .reset_index()
            )
            monthly = monthly.sort_values("month")
            historical[app_id] = monthly
        except Exception as e:
            pass  # Skip malformed CSVs silently

    return historical


def compute_yoy(monthly_df: pd.DataFrame) -> tuple[str, float]:
    """
    Compute YoY change in average CCU: compare most recent complete month
    to the same month one year prior. Returns (display_str, pct_float).
    """
    if monthly_df is None or len(monthly_df) < 2:
        return "N/A", 0.0

    now = pd.Period.now("M")
    # Use last complete month (not current partial month)
    last_complete = now - 1
    year_ago = last_complete - 12

    row_now  = monthly_df[monthly_df["month"] == last_complete]
    row_prev = monthly_df[monthly_df["month"] == year_ago]

    if row_now.empty or row_prev.empty:
        # Fall back to most recent vs same-month last year using available data
        latest = monthly_df.iloc[-1]
        target_month = latest["month"] - 12
        row_prev2 = monthly_df[monthly_df["month"] == target_month]
        if row_prev2.empty:
            return "N/A", 0.0
        val_now  = latest["avg_ccu"] if not pd.isna(latest["avg_ccu"]) else latest["peak_ccu"]
        val_prev = row_prev2.iloc[0]["avg_ccu"]
        if pd.isna(val_prev) or val_prev == 0:
            val_prev = row_prev2.iloc[0]["peak_ccu"]
    else:
        val_now  = row_now.iloc[0]["avg_ccu"]
        val_prev = row_prev.iloc[0]["avg_ccu"]
        if pd.isna(val_now):  val_now  = row_now.iloc[0]["peak_ccu"]
        if pd.isna(val_prev): val_prev = row_prev.iloc[0]["peak_ccu"]

    if pd.isna(val_now) or pd.isna(val_prev) or val_prev == 0:
        return "N/A", 0.0

    pct = (val_now - val_prev) / val_prev * 100
    pct_capped = max(-999.0, min(999.0, pct))
    sign = "+" if pct_capped >= 0 else ""
    return f"{sign}{pct_capped:.1f}%", pct_capped


def get_historical_summary(monthly_df: pd.DataFrame) -> dict:
    """Return a summary dict for the AI prompt from historical data."""
    if monthly_df is None or monthly_df.empty:
        return {}
    last_12 = monthly_df.tail(12)
    peak_ever = monthly_df["peak_ccu"].max()
    peak_12m  = last_12["peak_ccu"].max()
    avg_12m   = last_12["avg_ccu"].mean()
    # Month-over-month trend (slope sign over last 3 months)
    last_3 = monthly_df.tail(3)
    if len(last_3) >= 2:
        vals = last_3["avg_ccu"].fillna(last_3["peak_ccu"]).dropna().tolist()
        mom_trend = "↑" if len(vals) >= 2 and vals[-1] > vals[0] else "↓"
    else:
        mom_trend = "—"
    return {
        "peak_ever":  int(peak_ever) if not pd.isna(peak_ever) else None,
        "peak_12m":   int(peak_12m)  if not pd.isna(peak_12m)  else None,
        "avg_12m":    int(avg_12m)   if not pd.isna(avg_12m)   else None,
        "mom_trend":  mom_trend,
        "months_data": len(monthly_df),
    }

PRESET_QUERIES = [
    {
        "id": "ccu_mecha",
        "label": "CCU Trends & Mecha-Shooter Demand",
        "tag": "Market",
        "tag_class": "tag",
        "desc": "Analyze the top 10 shooters on Steam and compare CCU trends to last year. What does this say about current demand for mecha-shooters?",
        "prompt_key": "ccu_mecha",
    },
    {
        "id": "table_stakes",
        "label": "2026 Netcode & Server Table Stakes",
        "tag": "Tech",
        "tag_class": "tag amber",
        "desc": "What are the non-negotiable 'table stakes' for a competitive shooter in 2026 regarding netcode and server architecture to satisfy Western competitive integrity standards?",
        "prompt_key": "table_stakes",
    },
    {
        "id": "social_metrics",
        "label": "Social Media Metrics for Day-1 Success",
        "tag": "Social",
        "tag_class": "tag pos",
        "desc": "Based on recent investor reports and market data, what are the primary social media metrics to track to predict a new shooter's Day 1 success?",
        "prompt_key": "social_metrics",
    },
    {
        "id": "weekly_report",
        "label": "Weekly Retention & Engagement Report Template",
        "tag": "Report",
        "tag_class": "tag purple",
        "desc": "Create a template for a weekly market report that tracks retention and engagement KPIs across the top 100 shooters, highlighting any 'breakout' indie titles.",
        "prompt_key": "weekly_report",
    },
]

# ─────────────────────────────────────────────────────────────
# STEAM LIVE CCU FETCH
# ─────────────────────────────────────────────────────────────

STEAMSPY_URL = "https://steamspy.com/api.php"

@st.cache_data(ttl=300, show_spinner=False)
def fetch_ccu(app_id: int) -> int | None:
    """Fetch live concurrent player count from the Steam public API."""
    try:
        r = requests.get(CCU_URL, params={"appid": app_id}, timeout=8)
        if r.ok:
            return r.json().get("response", {}).get("player_count")
    except Exception:
        pass
    return None

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_steamspy(app_id: int) -> dict:
    """
    Fetch game data from SteamSpy (no API key required, updates daily).
    Returns fields including:
      - average_forever: avg playtime (mins) all-time
      - average_2weeks:  avg playtime (mins) past 2 weeks
      - owners:          estimated owner band e.g. '1,000,000 .. 2,000,000'
      - positive / negative: review counts
    """
    try:
        r = requests.get(
            STEAMSPY_URL,
            params={"request": "appdetails", "appid": app_id},
            timeout=12,
        )
        if r.ok:
            return r.json()
    except Exception:
        pass
    return {}

def parse_yoy_from_steamspy(ss: dict) -> tuple[str, int]:
    """
    Derive a YoY proxy from SteamSpy's playtime data.
    Compares average_2weeks (recent engagement) to average_forever (all-time baseline).
    A ratio > 1 implies the game is played MORE than its historical average → growing.
    A ratio < 1 implies declining engagement.
    Returns (display_str, numeric_pct).
    """
    avg_all  = ss.get("average_forever", 0) or 0
    avg_2w   = ss.get("average_2weeks",  0) or 0

    if avg_all == 0:
        return "N/A", 0

    # Normalise: if 2-week avg is X% of all-time avg, that's the engagement index
    ratio = avg_2w / avg_all
    # Map to a YoY-style percentage: ratio 1.0 = flat (0%), 1.5 = +50%, 0.5 = -50%
    pct = round((ratio - 1.0) * 100)
    # Cap display at ±99% to avoid misleading outliers
    pct = max(-99, min(99, pct))
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct}%", pct

# ─────────────────────────────────────────────────────────────
# REPORT HELPERS (HTML + PDF)
# ─────────────────────────────────────────────────────────────

def report_to_html(md_text: str) -> str:
    body = _md_lib.markdown(md_text, extensions=["tables", "fenced_code"]) if MARKDOWN_AVAILABLE else md_text.replace("\n", "<br>")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>SEGA Shooter Intel — Report</title>
<style>
body{{background:#0a0c1a;color:#eef0fa;font-family:'Segoe UI',sans-serif;max-width:860px;margin:40px auto;padding:0 24px;line-height:1.7}}
h1,h2,h3{{font-weight:900;letter-spacing:-.02em;color:#fff}}
h1{{font-size:2rem;border-bottom:2px solid #4080ff;padding-bottom:.4rem}}
h2{{font-size:1.4rem;color:#7ab0ff;margin-top:2rem}}
h3{{font-size:1.1rem;color:#b8bcd4}}
code,pre{{background:#141728;border:1px solid #232640;border-radius:4px;padding:.15em .4em;font-size:.88em;color:#4080ff}}
pre code{{padding:0}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #232640;padding:.5rem .8rem;text-align:left}}
th{{background:#141728;color:#7ab0ff;font-size:.78rem;letter-spacing:.1em;text-transform:uppercase}}
hr{{border:none;border-top:1px solid #232640;margin:1.5rem 0}}
.footer{{margin-top:3rem;padding-top:.8rem;border-top:1px solid #232640;font-size:.72rem;color:#5a5f82}}
</style>
</head>
<body>
{body}
<div class="footer">SEGA Shooter Intelligence — Internal analytics use only</div>
</body>
</html>"""

def report_to_pdf(md_text: str) -> bytes | None:
    if not _REPORTLAB_AVAILABLE:
        return None
    buf = _rl_io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    _h1 = ParagraphStyle("h1", parent=styles["Heading1"],
                         fontSize=18, textColor=_rl_colors.HexColor("#0f3460"),
                         spaceAfter=8, spaceBefore=14)
    _h2 = ParagraphStyle("h2", parent=styles["Heading2"],
                         fontSize=14, textColor=_rl_colors.HexColor("#0f3460"),
                         spaceAfter=6, spaceBefore=10)
    _h3 = ParagraphStyle("h3", parent=styles["Heading3"],
                         fontSize=12, textColor=_rl_colors.HexColor("#1a1a2e"),
                         spaceAfter=4, spaceBefore=8)
    _body = ParagraphStyle("body", parent=styles["Normal"],
                           fontSize=10, leading=15, spaceAfter=6)
    _bullet = ParagraphStyle("bullet", parent=_body,
                             leftIndent=16, bulletIndent=6, spaceAfter=3)
    _code = ParagraphStyle("code", parent=styles["Code"],
                           fontSize=8, leading=12,
                           backColor=_rl_colors.HexColor("#f0f0f8"),
                           leftIndent=12, rightIndent=12, spaceAfter=6)
    story = []
    in_code, code_lines = False, []
    for line in md_text.split("\n"):
        if line.startswith("```"):
            if in_code:
                story.append(Preformatted("\n".join(code_lines), _code))
                story.append(Spacer(1, 4))
                code_lines = []; in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line); continue
        if line.startswith("### "):
            story.append(Paragraph(line[4:], _h3))
        elif line.startswith("## "):
            story.append(HRFlowable(width="100%", thickness=0.5,
                         color=_rl_colors.HexColor("#c0c0d8"), spaceAfter=2))
            story.append(Paragraph(line[3:], _h2))
        elif line.startswith("# "):
            story.append(Paragraph(line[2:], _h1))
        elif line.startswith("- ") or line.startswith("* "):
            t = line[2:].replace("**", "<b>", 1).replace("**", "</b>", 1)
            story.append(Paragraph(f"• {t}", _bullet))
        elif line.strip() in ("---", "***", "___"):
            story.append(HRFlowable(width="100%", thickness=0.5,
                         color=_rl_colors.HexColor("#c0c0d8")))
            story.append(Spacer(1, 4))
        elif line.strip() == "":
            story.append(Spacer(1, 6))
        else:
            import re as _re
            t = _re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
            t = _re.sub(r"\*(.+?)\*",   r"<i>\1</i>", t)
            t = _re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", t)
            story.append(Paragraph(t, _body))
    doc.build(story)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────
# CLAUDE PROMPTS
# ─────────────────────────────────────────────────────────────

def build_system_prompt() -> str:
    return (
        "You are a senior games market analyst at SEGA's internal strategy team. "
        "You specialise in the competitive shooter genre across Steam, console, and mobile. "
        "Your analysis is data-driven, commercially sharp, and directly actionable for a publishing team. "
        "Use markdown for all output. Use headers, bullet points, tables, and bold highlights where appropriate. "
        "Be specific — cite titles, numbers, dates, and named competitors whenever possible. "
        "Avoid vague generalisations. Outputs will be read by product leads and senior management."
    )

def build_ccu_mecha_prompt(ccu_data: list[dict]) -> str:
    rows = []
    for r in ccu_data:
        hs = r.get("hist_summary", {})
        src = "SteamDB CSV" if r.get("has_hist") else "SteamSpy proxy"
        row = (
            f"- **{r['name']}** ({r['sub']}): {r['ccu']:,} live CCU | "
            f"YoY {r.get('yoy','N/A')} [{src}] | "
            f"Peak ever {hs.get('peak_ever', '?'):,} | " if hs.get('peak_ever') else
            f"- **{r['name']}** ({r['sub']}): {r['ccu']:,} live CCU | "
            f"YoY {r.get('yoy','N/A')} [{src}] | "
        )
        if hs:
            row += (
                f"Peak 12m {hs.get('peak_12m','?'):,} | "
                f"Avg CCU 12m {hs.get('avg_12m','?'):,} | "
                f"MoM {hs.get('mom_trend','—')} | "
                f"{hs.get('months_data',0)} months of data"
            )
        row += f" | Review score {r.get('review_pct','?')}% | Est. owners {r.get('owners','Unknown')}"
        rows.append(row)
    rows_str = "\n".join(rows)
    return f"""## Task: CCU Trend Analysis — Top Shooters on Steam

You have been provided with **live Steam CCU data** and **real historical SteamDB data** (where available) for the top shooter titles as of today. YoY comparisons marked [SteamDB CSV] are genuine same-month comparisons from raw data; those marked [SteamSpy proxy] are engagement-based estimates.

### Live CCU Snapshot + Historical Context
{rows_str}

### Questions to answer (structure your report with these sections):

1. **CCU Overview** — Rank the titles. Which are growing YoY? Which are declining? Identify clear winners and losers.
2. **Genre Health** — What do these numbers collectively say about shooter genre health on Steam in 2026?
3. **Mecha-Shooter Demand** — Focus specifically on titles with mech/robot/exosuit themes (e.g. Armored Core VI, Titanfall 2). What does the data say about current demand for mecha-shooters? Is the sub-genre growing or niche?
4. **Strategic Implications** — If SEGA were to greenlight a new mecha-shooter today, what CCU targets are realistic for Year 1? What player acquisition strategies are implied by the data?
5. **Recommended Watch List** — List 3 titles to monitor closely over the next 90 days and why.

Be quantitative. Use tables where useful."""

def build_table_stakes_prompt() -> str:
    return """## Task: 2026 Technical Table Stakes — Competitive Shooters

Western PC/console players in 2026 have extremely high expectations for competitive integrity. This analysis is for SEGA's internal game design and engineering teams evaluating a potential new competitive shooter.

### Provide a comprehensive analysis covering:

1. **Netcode Fundamentals**
   - What server tick rates are now considered minimum vs. best-in-class? (Reference CS2, Valorant, Apex, R6 Siege)
   - Client-side prediction vs. server reconciliation — what is the acceptable latency ceiling for Western esports audiences?
   - Rollback netcode vs. delay-based: which is relevant for shooters and why?

2. **Server Infrastructure**
   - Regional server coverage expectations (NA, EU, APAC minimums)
   - Server ownership vs. peer-to-peer: what is the current industry standard?
   - DDoS protection requirements for ranked/competitive modes

3. **Anti-Cheat**
   - Which anti-cheat solutions are now considered table stakes vs. competitive differentiators?
   - Kernel-level vs. user-level: player sentiment trade-offs
   - Replay validation and server-side hit detection requirements

4. **Competitive Integrity Features**
   - Ranked system design standards (MMR transparency, placement matches, ranked resets)
   - In-game reporting and review workflows
   - Tournament/LAN mode requirements for esports potential

5. **Post-Launch Patch Standards**
   - Acceptable cadence for balance patches and hotfixes
   - Communication standards players expect (patch notes format, dev blogs)

6. **Cost Estimates** — Rough infrastructure budget ranges (low/mid/high tier) for a title targeting 10K, 100K, and 1M peak CCU.

Format as a structured technical brief with a clear PASS/FAIL checklist at the end."""

def build_social_metrics_prompt() -> str:
    return """## Task: Social Media Predictive Metrics — Shooter Day 1 Success

This analysis synthesises findings from recent investor reports (Embracer, EA, Take-Two, Krafton, Nexon), GDC talks, and published post-mortems to identify the most reliable social media metrics for predicting a new shooter's Day 1 commercial performance.

### Analyse and structure your report as follows:

1. **Pre-Launch Predictive Signals (T-90 to T-0)**
   - Which metrics have the highest correlation with Day 1 peak CCU and revenue?
   - Provide specific benchmarks (e.g. "10K wishlist adds per week in final month = X CCU at launch")
   - Differentiate between vanity metrics and actionable leading indicators

2. **Platform-Specific Metrics**
   - **Steam**: Wishlists, review velocity, concurrent viewers on launch day
   - **Twitch/YouTube**: Hours watched, unique streamers, clip virality
   - **X/Twitter**: Hashtag impressions, sentiment ratio, influencer amplification coefficient
   - **TikTok/Shorts**: View-to-wishlist conversion rate, trend longevity
   - **Reddit/Discord**: Community growth rate, DAU/MAU ratio, organic posts vs. seeded content

3. **Red Flags — What Signals a Soft Launch**
   - Which patterns in social data predicted underperformance for recent titles?
   - Name specific failed or underperforming shooters and their pre-launch signals

4. **Green Flags — The Viral Flywheel**
   - What social conditions created outsized launches? (e.g. HELLDIVERS 2, BattleBit Remastered)
   - What was different about their pre-launch social fingerprint?

5. **Recommended KPI Dashboard**
   - Design a 10-metric social dashboard SEGA should build for any new shooter pre-launch
   - Include: metric name, platform, measurement method, target threshold, and refresh cadence

6. **Budget Implication** — Given these metrics, what social/influencer spend is required to hit minimum viable social velocity for a Western competitive shooter launch?"""

def build_weekly_report_prompt(ccu_data: list[dict]) -> str:
    rows = []
    for r in ccu_data:
        hs = r.get("hist_summary", {})
        src = "SteamDB" if r.get("has_hist") else "est."
        line = (
            f"- {r['name']} ({r['sub']}): {r['ccu']:,} CCU live | "
            f"YoY {r.get('yoy','N/A')} [{src}] | "
            f"Peak 12m {hs.get('peak_12m','?'):,} | " if hs.get('peak_12m') else
            f"- {r['name']} ({r['sub']}): {r['ccu']:,} CCU live | "
            f"YoY {r.get('yoy','N/A')} [{src}] | "
        )
        line += f"MoM {hs.get('mom_trend','—')} | Avg Hrs/2wk {r.get('avg_2w_hrs','?')} | Review {r.get('review_pct','?')}%"
        rows.append(line)
    rows_str = "\n".join(rows)
    return f"""## Task: Weekly Market Report Template — Top 100 Shooters

Create a fully populated **template** for SEGA's internal weekly shooter market report. This report is distributed every Monday to product leads, publishing managers, and the CEO's strategy briefing.

Use the following live CCU snapshot + historical data as seed data for the current week's figures:

{rows_str}

### The template must include ALL of the following sections, fully written out with example data:

---

**SECTION 1: EXECUTIVE SUMMARY** (max 200 words)
- Week-over-week market mood (Rising / Flat / Declining)
- 3 bullet headline findings
- 1 "Story of the Week"

**SECTION 2: TOP 20 CCU LEAGUE TABLE**
- Ranked table: Title | Sub-genre | Publisher | Live CCU | WoW Δ | 4-Week Trend | Status
- Highlight any title that moved ±3 positions

**SECTION 3: BREAKOUT INDIE WATCH**
- Identify any title outside the top 20 with unusual CCU or review velocity
- Include: Title | Developer | Price | CCU | Review Score | Why It Matters

**SECTION 4: RETENTION & ENGAGEMENT KPIs**
For each of the top 10 titles, estimate or track:
- 7-Day Retention (D7)
- 30-Day Retention (D30)
- Avg Session Length
- Daily Active Users (DAU) estimate
- DAU/MAU ratio estimate
- New Player Acquisition (NPA) rate this week

**SECTION 5: SUB-GENRE HEAT MAP**
- Which sub-genres are gaining/losing share? (Tactical, BR, Arena, Co-op PvE, Mecha, Hero, Extraction)

**SECTION 6: COMPETITIVE INTELLIGENCE**
- Any notable patch drops, events, or announcements from top publishers this week
- Pricing changes, free weekends, or seasonal events that moved the needle

**SECTION 7: SEGA STRATEGIC IMPLICATIONS**
- 3 bullet points specifically relevant to SEGA's potential shooter projects
- Any gap in the market that widened or narrowed this week?

**SECTION 8: DATA SOURCES & METHODOLOGY**
- Where to pull each data point, refresh cadence, and known limitations

---

The output should be a complete, copy-paste-ready template that the analytics team can fill in each Monday in under 2 hours."""

# ─────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────

defaults = {
    "claude_key": st.secrets.get("CLAUDE_KEY", os.environ.get("CLAUDE_KEY", "")),
    "ccu_data": [],
    "active_query": None,
    "ai_report": "",
    "ai_chat_history": [],
    "ai_chat_pending": False,
    "report_label": "",
    "custom_query": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────
# TOP NAV
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="topbar">
  <div class="topbar-logo"><span class="seg">SEGA</span> &nbsp;SHOOTER INTELLIGENCE</div>
  <div class="topbar-divider"></div>
  <div class="topbar-label">Market &amp; Tech Analysis</div>
  <div class="topbar-pill">🎯 Internal Use Only</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
  <div class="hero-title">SHOOTER MARKET<br><span class="accent">INTELLIGENCE</span></div>
  <div class="hero-sub">
    Live Steam CCU data · AI-powered analysis · Competitive benchmarks ·
    Weekly reporting templates — all in one tool for SEGA's publishing and strategy teams.
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SIDEBAR — API KEY
# ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="font-family:'Inter Tight',sans-serif;font-weight:900;font-size:1rem;
    letter-spacing:.1em;text-transform:uppercase;color:#4080ff;margin-bottom:1rem;">
    ⚙ Configuration</div>
    """, unsafe_allow_html=True)

    _cl_ok = bool(st.session_state.claude_key)
    if _cl_ok:
        st.success("\u2713 Anthropic API key loaded", icon="\U0001f511")
    else:
        st.error("Anthropic API key missing")
        st.markdown(
            "Add to <code>.streamlit/secrets.toml</code>:<br>"
            "<pre>CLAUDE_KEY = \"sk-ant-your-key-here\"</pre>"
            "Or set the <code>CLAUDE_KEY</code> environment variable.",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.caption("Model: claude-sonnet-4-20250514")
    st.caption("CCU: Steam public API (5 min cache)")
    st.caption("Engagement: SteamSpy API (1 hr cache)")
    st.markdown("---")
    # Show which games have historical CSV data loaded
    historical = load_all_historical()
    hist_ids = set(historical.keys())
    roster_ids = {g["app_id"] for g in SHOOTER_ROSTER}
    loaded = hist_ids & roster_ids
    missing = roster_ids - hist_ids
    st.caption(f"📁 SteamDB CSVs: {len(loaded)}/{len(roster_ids)} loaded")
    if missing:
        missing_names = [g["name"] for g in SHOOTER_ROSTER if g["app_id"] in missing]
        st.caption("⚠️ Missing: " + ", ".join(missing_names))
    st.caption("Drop steamdb_chart_{{appid}}.csv into /data to update")

# ─────────────────────────────────────────────────────────────
# QUERY BLOCK
# ─────────────────────────────────────────────────────────────

st.markdown('<div class="query-block">', unsafe_allow_html=True)

st.markdown("""
<div class="section-header" style="margin-top:0">
  <span class="dot"></span>SELECT ANALYSIS TYPE
</div>
""", unsafe_allow_html=True)

# Preset cards
col1, col2 = st.columns(2)
for i, preset in enumerate(PRESET_QUERIES):
    col = col1 if i % 2 == 0 else col2
    with col:
        st.markdown(f"""
        <div class="insight-card">
          <div class="insight-card-title">
            <span class="{preset['tag_class']}">{preset['tag']}</span>
            {preset['label']}
          </div>
          <div class="insight-card-desc">{preset['desc']}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"Run Analysis", key=f"preset_{preset['id']}"):
            st.session_state.active_query = preset["prompt_key"]
            st.session_state.ai_report = ""
            st.session_state.ai_chat_history = []
            st.session_state.report_label = preset["label"]

st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="field-label">Or ask a custom question</div>', unsafe_allow_html=True)
col_q, col_btn = st.columns([5, 1])
with col_q:
    custom = st.text_input(
        "Custom query",
        value=st.session_state.custom_query,
        label_visibility="collapsed",
        placeholder="e.g. Compare monetisation models across the top 5 F2P shooters on Steam…",
        key="custom_input",
    )
with col_btn:
    run_custom = st.button("Run", key="run_custom")

if run_custom and custom.strip():
    st.session_state.custom_query = custom.strip()
    st.session_state.active_query = "custom"
    st.session_state.ai_report = ""
    st.session_state.ai_chat_history = []
    st.session_state.report_label = "Custom Query"

st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# LIVE CCU PANEL
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="section-header">
  <span class="dot"></span>LIVE STEAM CCU SNAPSHOT
</div>
""", unsafe_allow_html=True)

if not st.session_state.ccu_data:
    if st.button("📡  Fetch Live CCU Data", key="fetch_ccu"):
        with st.spinner("Pulling live CCU from Steam…"):
            # Load historical SteamDB data from /data folder
            historical = load_all_historical()
            results = []
            prog = st.progress(0.0)
            status = st.empty()
            for idx, game in enumerate(SHOOTER_ROSTER):
                status.caption(f"Fetching: {game['name']}…")

                # Live CCU from Steam API
                ccu = fetch_ccu(game["app_id"])

                # Real YoY from SteamDB historical CSV (if available)
                hist_df  = historical.get(game["app_id"])
                has_hist = hist_df is not None and not hist_df.empty
                if has_hist:
                    yoy_str, yoy_pct = compute_yoy(hist_df)
                    hist_summary = get_historical_summary(hist_df)
                else:
                    # Fall back to SteamSpy proxy
                    ss = fetch_steamspy(game["app_id"])
                    yoy_str, yoy_pct = parse_yoy_from_steamspy(ss)
                    hist_summary = {}

                # SteamSpy for owner/review data (still useful supplemental)
                ss = fetch_steamspy(game["app_id"])
                owners     = ss.get("owners", "Unknown")
                avg_2w_hrs = round((ss.get("average_2weeks", 0) or 0) / 60, 1)
                pos_reviews= ss.get("positive", 0) or 0
                neg_reviews= ss.get("negative", 0) or 0
                total_rev  = pos_reviews + neg_reviews
                review_pct = round(pos_reviews / total_rev * 100, 1) if total_rev else None

                results.append({
                    **game,
                    "ccu":          ccu if ccu else 0,
                    "ccu_live":     ccu is not None,
                    "yoy":          yoy_str,
                    "yoy_val":      yoy_pct,
                    "has_hist":     has_hist,
                    "hist_summary": hist_summary,
                    "owners":       owners,
                    "avg_2w_hrs":   avg_2w_hrs,
                    "review_pct":   review_pct,
                    "pos_reviews":  pos_reviews,
                    "neg_reviews":  neg_reviews,
                })
                prog.progress((idx + 1) / len(SHOOTER_ROSTER))
                time.sleep(0.4)  # polite rate limiting for SteamSpy

            status.empty()
            results.sort(key=lambda x: x["ccu"], reverse=True)
            st.session_state.ccu_data = results
        st.rerun()
else:
    ccu_data = st.session_state.ccu_data

    # KPI row
    total_ccu = sum(r["ccu"] for r in ccu_data)
    top_title = ccu_data[0]["name"]
    top_ccu   = ccu_data[0]["ccu"]
    growing   = sum(1 for r in ccu_data if r["yoy_val"] > 0)
    f2p_share = sum(r["ccu"] for r in ccu_data if r["f2p"]) / max(total_ccu, 1) * 100

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""<div class="metric-card blue-top">
        <div class="metric-label">Total CCU (Tracked)</div>
        <div class="metric-value">{total_ccu:,}</div>
        <div class="metric-sub">Across {len(ccu_data)} shooter titles</div>
        </div>""", unsafe_allow_html=True)
    with k2:
        st.markdown(f"""<div class="metric-card pos-top">
        <div class="metric-label">Top Title</div>
        <div class="metric-value" style="font-size:1.1rem;padding-top:.3rem">{top_title[:22]}</div>
        <div class="metric-sub">{top_ccu:,} live players</div>
        </div>""", unsafe_allow_html=True)
    with k3:
        st.markdown(f"""<div class="metric-card amber-top">
        <div class="metric-label">YoY Growth (Titles)</div>
        <div class="metric-value">{growing}/{len(ccu_data)}</div>
        <div class="metric-sub">titles showing positive YoY trend</div>
        </div>""", unsafe_allow_html=True)
    with k4:
        st.markdown(f"""<div class="metric-card purple-top">
        <div class="metric-label">F2P CCU Share</div>
        <div class="metric-value">{f2p_share:.0f}%</div>
        <div class="metric-sub">of total tracked CCU is F2P titles</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # CCU Bar Chart
    top10 = ccu_data[:10]
    colors = ["#4080ff" if not r["f2p"] else "#20c65a" for r in top10]
    fig = go.Figure(go.Bar(
        x=[r["name"] for r in top10],
        y=[r["ccu"] for r in top10],
        marker_color=colors,
        text=[f"{r['ccu']:,}" for r in top10],
        textposition="outside",
        textfont=dict(size=10, color="#b8bcd4"),
        hovertemplate="<b>%{x}</b><br>CCU: %{y:,}<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_BASE,
        title=dict(text="Top 10 Shooters by Live CCU", font=dict(size=13, color="#b8bcd4"), x=0),
        xaxis=dict(showgrid=False, tickfont=dict(size=10), tickangle=-30,
                   linecolor="#232640", tickcolor="#232640"),
        yaxis=dict(showgrid=True, gridcolor="#1a1e30", tickformat=","),
        height=340,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("🔵 Paid  🟢 Free-to-Play  |  CCU = Concurrent Users  |  Live data from Steam API")

    # Full Table
    with st.expander("Full Data Table — All Tracked Titles"):
        df = pd.DataFrame([{
            "Title":          r["name"],
            "Sub-genre":      r["sub"],
            "Publisher":      r["publisher"],
            "F2P":            "✓" if r["f2p"] else "—",
            "Live CCU":       r["ccu"],
            "YoY (real)":     r.get("yoy", "N/A"),
            "Data Source":    "SteamDB CSV" if r.get("has_hist") else "SteamSpy proxy",
            "Peak Ever":      f"{r['hist_summary']['peak_ever']:,}" if r.get("hist_summary", {}).get("peak_ever") else "—",
            "Peak 12m":       f"{r['hist_summary']['peak_12m']:,}" if r.get("hist_summary", {}).get("peak_12m") else "—",
            "Avg CCU 12m":    f"{r['hist_summary']['avg_12m']:,}" if r.get("hist_summary", {}).get("avg_12m") else "—",
            "MoM Trend":      r.get("hist_summary", {}).get("mom_trend", "—"),
            "Avg Hrs/2wk":    r.get("avg_2w_hrs", "—"),
            "Review Score":   f"{r['review_pct']}%" if r.get("review_pct") else "—",
            "Est. Owners":    r.get("owners", "—"),
        } for r in ccu_data])
        st.dataframe(df, use_container_width=True, hide_index=True)

        hist_count = sum(1 for r in ccu_data if r.get("has_hist"))
        st.caption(
            f"📁 {hist_count}/{len(ccu_data)} titles have SteamDB historical CSV data loaded. "
            "YoY = real same-month comparison where CSV available, SteamSpy proxy otherwise. "
            "Peak/Avg figures derived from SteamDB 10-min interval data aggregated monthly."
        )

    # Historical trend chart (for titles with CSV data)
    hist_titles = [r for r in ccu_data if r.get("has_hist")]
    if hist_titles:
        historical = load_all_historical()
        with st.expander("📈 Monthly Peak CCU History — SteamDB Data"):
            fig2 = go.Figure()
            for r in hist_titles:
                mdf = historical.get(r["app_id"])
                if mdf is not None and not mdf.empty:
                    last_24 = mdf.tail(24)
                    fig2.add_trace(go.Scatter(
                        x=[str(p) for p in last_24["month"]],
                        y=last_24["peak_ccu"],
                        mode="lines",
                        name=r["name"],
                        hovertemplate=f"<b>{r['name']}</b><br>%{{x}}<br>Peak CCU: %{{y:,}}<extra></extra>",
                        line=dict(width=2),
                    ))
            fig2.update_layout(
                **PLOTLY_BASE,
                title=dict(text="Monthly Peak CCU — Last 24 Months (SteamDB)", font=dict(size=13, color="#b8bcd4"), x=0),
                xaxis=dict(showgrid=False, tickangle=-45, tickfont=dict(size=9)),
                yaxis=dict(showgrid=True, gridcolor="#1a1e30", tickformat=","),
                height=380,
                legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("Source: SteamDB 10-minute interval CSVs, aggregated to monthly peak. Drop updated CSVs into /data to refresh.")

    if st.button("🔄 Refresh CCU Data", key="refresh_ccu"):
        st.cache_data.clear()
        st.session_state.ccu_data = []
        st.rerun()

# ─────────────────────────────────────────────────────────────
# AI ANALYSIS ENGINE
# ─────────────────────────────────────────────────────────────

if st.session_state.active_query:
    st.markdown(f"""
    <div class="section-header">
      <span class="dot"></span>AI ANALYSIS — {st.session_state.report_label.upper()}
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.claude_key:
        st.warning("Enter your Claude API key in the sidebar to run AI analysis.", icon="🔑")
    elif not ANTHROPIC_AVAILABLE:
        st.error("Install the `anthropic` package: `pip install anthropic`")
    elif not st.session_state.ai_report:
        # Build prompt
        ccu_data = st.session_state.ccu_data or []
        aq = st.session_state.active_query
        if aq == "ccu_mecha":
            if not ccu_data:
                st.warning("Please fetch live CCU data first, then re-run this analysis.", icon="📡")
                st.stop()
            user_prompt = build_ccu_mecha_prompt(ccu_data[:10])
        elif aq == "table_stakes":
            user_prompt = build_table_stakes_prompt()
        elif aq == "social_metrics":
            user_prompt = build_social_metrics_prompt()
        elif aq == "weekly_report":
            if not ccu_data:
                st.warning("Please fetch live CCU data first, then re-run this analysis.", icon="📡")
                st.stop()
            user_prompt = build_weekly_report_prompt(ccu_data[:20])
        elif aq == "custom":
            user_prompt = st.session_state.custom_query
        else:
            user_prompt = st.session_state.custom_query

        ai_model = "claude-sonnet-4-20250514"

        with st.spinner("Claude is generating your analysis…"):
            ph = st.empty()
            report_text = ""
            try:
                client = _anthropic.Anthropic(api_key=st.session_state.claude_key)
                with client.messages.stream(
                    model=ai_model,
                    max_tokens=4096,
                    system=build_system_prompt(),
                    messages=[{"role": "user", "content": user_prompt}],
                ) as stream:
                    for delta in stream.text_stream:
                        report_text += delta
                        ph.markdown(report_text + "▌")
                ph.markdown(report_text)
                st.session_state.ai_report = report_text
            except _anthropic.AuthenticationError:
                st.error("Invalid API key. Check your key in the sidebar.")
            except _anthropic.RateLimitError:
                st.error("Rate limit hit. Wait a moment and try again.")
            except _anthropic.APIConnectionError as e:
                st.error(f"Could not reach Anthropic API: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {type(e).__name__}: {e}")

    elif st.session_state.ai_report:
        st.markdown(st.session_state.ai_report)

    # ── Download options ──
    if st.session_state.ai_report:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:.62rem;font-weight:700;letter-spacing:.18em;'
            'text-transform:uppercase;color:var(--muted);margin-bottom:.5rem;">'
            'DOWNLOAD REPORT</div>',
            unsafe_allow_html=True,
        )
        slug = re.sub(r"[^a-z0-9]+", "_", st.session_state.report_label.lower())[:40]
        fname = f"sega_shooter_intel_{slug}"

        dl1, dl2, dl3 = st.columns(3)
        with dl1:
            st.download_button(
                "⬇ Markdown (.md)",
                data=st.session_state.ai_report,
                file_name=f"{fname}.md",
                mime="text/markdown",
                width="stretch",
                key="dl_md",
            )
        with dl2:
            html_bytes = report_to_html(st.session_state.ai_report).encode("utf-8")
            st.download_button(
                "⬇ HTML page (.html)",
                data=html_bytes,
                file_name=f"{fname}.html",
                mime="text/html",
                width="stretch",
                key="dl_html",
            )
        with dl3:
            if _REPORTLAB_AVAILABLE:
                pdf_bytes = report_to_pdf(st.session_state.ai_report)
                if pdf_bytes:
                    st.download_button(
                        "⬇ PDF (.pdf)",
                        data=pdf_bytes,
                        file_name=f"{fname}.pdf",
                        mime="application/pdf",
                        width="stretch",
                        key="dl_pdf",
                    )
            else:
                st.caption("PDF unavailable — install `reportlab`")

        # ── Follow-up chat ──
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<div class="section-header"><span class="dot"></span>FOLLOW-UP CHAT'
            '<span style="color:var(--muted);font-size:.7rem;font-weight:400;"> '
            '— ask Claude follow-up questions about this report</span></div>',
            unsafe_allow_html=True,
        )

        def build_chat_system():
            ccu_ctx = ""
            if st.session_state.ccu_data:
                ccu_ctx = "\n\nLIVE CCU DATA:\n" + "\n".join(
                    f"- {r['name']}: {r['ccu']:,} CCU ({r['yoy']} YoY)"
                    for r in st.session_state.ccu_data[:15]
                )
            return (
                "You are a senior games market analyst at SEGA. "
                "The user has just received the following analysis report about the competitive shooter market. "
                "Answer follow-up questions concisely, accurately, and commercially. "
                "Reference the report and live data where relevant. "
                "Use markdown for formatting.\n\n"
                f"## Report\n\n{st.session_state.ai_report[:4000]}"
                + ("…[truncated]" if len(st.session_state.ai_report) > 4000 else "")
                + ccu_ctx
            )

        for msg in st.session_state.ai_chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if st.session_state.ai_chat_pending:
            st.session_state.ai_chat_pending = False
            api_msgs = [{"role": m["role"], "content": m["content"]}
                        for m in st.session_state.ai_chat_history]
            try:
                chat_client = _anthropic.Anthropic(api_key=st.session_state.claude_key)
                with st.chat_message("assistant"):
                    reply = ""
                    ph2 = st.empty()
                    with chat_client.messages.stream(
                        model="claude-sonnet-4-20250514",
                        max_tokens=2048,
                        system=build_chat_system(),
                        messages=api_msgs,
                    ) as stream:
                        for delta in stream.text_stream:
                            reply += delta
                            ph2.markdown(reply + "▌")
                    ph2.markdown(reply)
                st.session_state.ai_chat_history.append({"role": "assistant", "content": reply})
            except _anthropic.AuthenticationError:
                st.error("Invalid API key.")
            except _anthropic.RateLimitError:
                st.error("Rate limit. Please wait and retry.")
            except Exception as e:
                st.error(f"Chat error: {type(e).__name__}: {e}")

        user_msg = st.chat_input("Ask a follow-up question…", key="ai_chat_input")
        if user_msg:
            st.session_state.ai_chat_history.append({"role": "user", "content": user_msg})
            st.session_state.ai_chat_pending = True
            st.rerun()

        if st.session_state.ai_chat_history:
            if st.button("Clear chat history", key="clear_chat"):
                st.session_state.ai_chat_history = []
                st.session_state.ai_chat_pending = False
                st.rerun()

# ─────────────────────────────────────────────────────────────
# EMPTY STATE
# ─────────────────────────────────────────────────────────────

elif not st.session_state.active_query:
    st.markdown("""
    <div class="empty-state">
      <div class="empty-title">NO ANALYSIS SELECTED</div>
      <div class="empty-sub">
        Fetch live CCU data above, then choose an analysis type
        or enter a custom question to generate your report.
      </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="footer">
  <div class="footer-brand">SEGA SHOOTER INTELLIGENCE</div>
  <div class="footer-note">Data sourced from Steam public API · Powered by Claude · Internal analytics use only</div>
</div>
""", unsafe_allow_html=True)