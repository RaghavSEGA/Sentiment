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
# Roster built from CSVs present in the /data folder (30 titles).
# App IDs verified against Steam store. Corrected IDs vs previous roster:
#   Helldivers 2:       553850  (was 2668510)
#   Crosshair X:        1366800 (was 1070560)
#   Deadlock:           1422450 (was 2933620)
#   Arena Breakout:     2073620 (was 2457170)
#   Delta Force:        2507950 (was 2483290)
#   Battlefield 6:      2807960 (was 2377570)
#   Marathon:           3065800 (was 2379780)
#   Schedule I:         3164500 (was 2835570)
SHOOTER_ROSTER = [
    {"app_id": 440,     "name": "Team Fortress 2",                "sub": "Arena / Class FPS",       "publisher": "Valve",                "f2p": True},
    {"app_id": 550,     "name": "Left 4 Dead 2",                  "sub": "Co-op FPS / Horror",      "publisher": "Valve",                "f2p": False},
    {"app_id": 730,     "name": "Counter-Strike 2",               "sub": "Tactical / Competitive",  "publisher": "Valve",                "f2p": True},
    {"app_id": 4000,    "name": "Garry's Mod",                   "sub": "Sandbox / Shooter",       "publisher": "Facepunch Studios",    "f2p": False},
    {"app_id": 218620,  "name": "PAYDAY 2",                       "sub": "Co-op FPS / Heist",       "publisher": "Overkill Software",    "f2p": False},
    {"app_id": 221100,  "name": "DayZ",                           "sub": "Survival / Shooter",      "publisher": "Bohemia Interactive",  "f2p": False},
    {"app_id": 230410,  "name": "Warframe",                       "sub": "Looter Shooter / Co-op",  "publisher": "Digital Extremes",     "f2p": True},
    {"app_id": 236390,  "name": "War Thunder",                    "sub": "Vehicle Combat / MMO",    "publisher": "Gaijin",               "f2p": True},
    {"app_id": 252490,  "name": "Rust",                           "sub": "Open World / Survival",   "publisher": "Facepunch Studios",    "f2p": False},
    {"app_id": 271590,  "name": "Grand Theft Auto V Legacy",      "sub": "Open World / Action",     "publisher": "Rockstar Games",       "f2p": False},
    {"app_id": 359550,  "name": "Tom Clancy's Rainbow Six Siege","sub": "Tactical / Arena",        "publisher": "Ubisoft",              "f2p": False},
    {"app_id": 377160,  "name": "Fallout 4",                      "sub": "FPS / RPG",               "publisher": "Bethesda",             "f2p": False},
    {"app_id": 553850,  "name": "Helldivers 2",                   "sub": "Co-op Shooter",           "publisher": "Arrowhead",            "f2p": False},
    {"app_id": 578080,  "name": "PUBG: Battlegrounds",            "sub": "Battle Royale",           "publisher": "Krafton",              "f2p": True},
    {"app_id": 1151340, "name": "Fallout 76",                     "sub": "Online RPG / Shooter",    "publisher": "Bethesda",             "f2p": False},
    {"app_id": 1172470, "name": "Apex Legends",                   "sub": "Battle Royale / Hero",    "publisher": "EA / Respawn",         "f2p": True},
    {"app_id": 1174180, "name": "Red Dead Redemption 2",          "sub": "Open World / TPS",        "publisher": "Rockstar Games",       "f2p": False},
    {"app_id": 1366800, "name": "Crosshair X",                    "sub": "Aim Trainer / Utility",   "publisher": "Reflex Gaming",        "f2p": False},
    {"app_id": 1422450, "name": "Deadlock",                       "sub": "Hero Shooter / MOBA",     "publisher": "Valve",                "f2p": True},
    {"app_id": 1808500, "name": "ARC Raiders",                    "sub": "Extraction Shooter",      "publisher": "Embark Studios",       "f2p": False},
    {"app_id": 1938090, "name": "Call of Duty",                   "sub": "Military FPS",            "publisher": "Activision",           "f2p": True},
    {"app_id": 2073620, "name": "Arena Breakout: Infinite",       "sub": "Extraction Shooter",      "publisher": "MoreFun Studios",      "f2p": True},
    {"app_id": 2221490, "name": "Tom Clancy's The Division 2",   "sub": "Cover Shooter / MMO",     "publisher": "Ubisoft",              "f2p": False},
    {"app_id": 2357570, "name": "Overwatch 2",                    "sub": "Hero Shooter",            "publisher": "Blizzard",             "f2p": True},
    {"app_id": 2507950, "name": "Delta Force",                    "sub": "Military FPS / BR",       "publisher": "Team Jade / TiMi",     "f2p": True},
    {"app_id": 2767030, "name": "Marvel Rivals",                  "sub": "Hero Shooter",            "publisher": "NetEase Games",        "f2p": True},
    {"app_id": 2807960, "name": "Battlefield 6",                  "sub": "Military FPS",            "publisher": "EA / DICE",            "f2p": False},
    {"app_id": 3065800, "name": "Marathon",                       "sub": "Extraction Shooter",      "publisher": "Bungie",               "f2p": False},
    {"app_id": 3164500, "name": "Schedule I",                     "sub": "Simulation / Action",     "publisher": "TVGS",                 "f2p": False},
    {"app_id": 3240220, "name": "Grand Theft Auto V Enhanced",    "sub": "Open World / Action",     "publisher": "Rockstar Games",       "f2p": False},
    {"app_id": 4465480, "name": "Counter-Strike: Global Offensive","sub": "Tactical / Competitive", "publisher": "Valve",                "f2p": True},
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
    Loads all SteamDB CSVs. Returns {app_id: monthly_df} for charts/YoY.
    monthly_df columns: month (Period), peak_ccu, avg_ccu
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
            ).sort_values("month")
            historical[app_id] = monthly
        except Exception:
            pass
    return historical

@st.cache_data(show_spinner=False)
def load_all_raw() -> dict[int, pd.DataFrame]:
    """
    Loads all SteamDB CSVs retaining the full 10-minute interval rows.
    Used for WoW and precise MoM comparisons.
    Returns {app_id: df} where df has columns: DateTime, Players
    """
    raw: dict[int, pd.DataFrame] = {}
    if not DATA_DIR.exists():
        return raw
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
            df = df.sort_values("DateTime").reset_index(drop=True)
            raw[app_id] = df[["DateTime", "Players"]]
        except Exception:
            pass
    return raw


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
    last_12   = monthly_df.tail(12)
    peak_ever = monthly_df["peak_ccu"].max()
    peak_12m  = last_12["peak_ccu"].max()
    avg_12m   = last_12["avg_ccu"].mean()

    # Real month-over-month: last month vs. the month before it
    mom_pct   = None
    mom_trend = "—"
    if len(monthly_df) >= 2:
        def _val(row):
            v = row["avg_ccu"]
            return v if not pd.isna(v) else row["peak_ccu"]
        v_now  = _val(monthly_df.iloc[-1])
        v_prev = _val(monthly_df.iloc[-2])
        if not pd.isna(v_now) and not pd.isna(v_prev) and v_prev > 0:
            mom_pct   = (v_now - v_prev) / v_prev * 100
            mom_trend = f"{'+' if mom_pct >= 0 else ''}{mom_pct:.1f}%"

    return {
        "peak_ever":   int(peak_ever) if not pd.isna(peak_ever) else None,
        "peak_12m":    int(peak_12m)  if not pd.isna(peak_12m)  else None,
        "avg_12m":     int(avg_12m)   if not pd.isna(avg_12m)   else None,
        "mom_trend":   mom_trend,
        "mom_pct":     mom_pct,
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
        "Avoid vague generalisations. Outputs will be read by product leads and senior management. "
        "IMPORTANT: For every factual claim, benchmark figure, or industry statistic you include that is NOT "
        "derived from the data provided to you, you MUST cite a source inline using the format [Source: Name, Year]. "
        "Examples: [Source: Newzoo Global Games Market Report, 2025], [Source: Steam Spy, Mar 2026], "
        "[Source: GDC State of the Game Industry 2025], [Source: Valve Steam Blog, 2024]. "
        "If you are uncertain of a specific source, write [Source: industry estimates] rather than omitting attribution. "
        "Data provided directly in the prompt (SteamDB CSV, SteamSpy, Steam API) should be attributed as such inline."
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

Format as a structured technical brief with a clear PASS/FAIL checklist at the end.

**Source requirements:** Cite every benchmark figure, tick rate standard, and infrastructure cost estimate with [Source: Name, Year]. Reference specific developer blog posts, GDC talks, or published postmortems where possible (e.g. Riot Games engineering blog, Valve networking blog, Epic GDC 2024)."""

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

6. **Budget Implication** — Given these metrics, what social/influencer spend is required to hit minimum viable social velocity for a Western competitive shooter launch?

**Source requirements:** Every benchmark figure, conversion rate, and spend estimate must be cited with [Source: Name, Year]. Reference specific investor reports (Embracer, EA, Krafton, Nexon), GDC talks, or published postmortems where applicable."""

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
# SNAPSHOT STORE  (week-over-week diff)
# ─────────────────────────────────────────────────────────────

SNAPSHOT_PATH = Path(__file__).parent / "data" / "snapshots.json"
SNAPSHOT_MIN_AGE_HOURS = 20  # minimum hours between saved snapshots

def load_snapshots() -> list[dict]:
    try:
        if SNAPSHOT_PATH.exists():
            return json.loads(SNAPSHOT_PATH.read_text())
    except Exception:
        pass
    return []

def save_snapshot(ccu_data: list[dict]) -> None:
    """Save a snapshot only if the last saved one is older than SNAPSHOT_MIN_AGE_HOURS.
    This prevents every fetch from overwriting the reference point, ensuring
    the WoW diff is always comparing against a genuinely older snapshot."""
    snaps = load_snapshots()
    now   = datetime.utcnow()
    if snaps:
        try:
            last_ts   = datetime.fromisoformat(snaps[-1]["ts"])
            age_hours = (now - last_ts).total_seconds() / 3600
            if age_hours < SNAPSHOT_MIN_AGE_HOURS:
                return  # too recent — don't overwrite
        except Exception:
            pass
    snap = {
        "ts": now.isoformat(),
        "data": [{
            "app_id":  r["app_id"],
            "name":    r["name"],
            "ccu":     r["ccu"],
            "yoy":     r.get("yoy", "N/A"),
            "yoy_val": r.get("yoy_val", 0),
        } for r in ccu_data],
    }
    snaps.append(snap)
    snaps = snaps[-12:]  # keep last 12 snapshots (~12 weeks)
    try:
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(json.dumps(snaps, indent=2))
    except Exception:
        pass

def compute_period_diff(ccu_data: list[dict], raw_data: dict, days: int = 7) -> dict[int, dict]:
    """
    For titles with CSV data: find the Players value closest to exactly `days`
    ago within the raw 10-minute interval data, and compare to the latest value.

    For titles without CSV data: returns nothing (no fallback to snapshots —
    snapshot-based comparisons were unreliable).

    Returns {app_id: {prev_ccu, delta, delta_pct, source, period_label, ref_dt}}
    """
    result = {}
    now = pd.Timestamp.utcnow().tz_localize(None)
    for r in ccu_data:
        aid = r["app_id"]
        df  = raw_data.get(aid)
        if df is None or df.empty:
            continue
        df = df.dropna(subset=["Players"])
        if len(df) < 2:
            continue
        # Use live CCU from the fetched data, not the CSV's last row
        live_ccu   = r["ccu"]
        # Look for the row closest to exactly `days` ago from now
        target_dt  = now - pd.Timedelta(days=days)
        idx_closest = (df["DateTime"] - target_dt).abs().idxmin()
        ref_row    = df.loc[idx_closest]
        ref_dt     = ref_row["DateTime"]
        ref_ccu    = ref_row["Players"]
        # Allow up to ±4 days gap (handles stale CSVs and sparse early data)
        gap_hours  = abs((ref_dt - target_dt).total_seconds()) / 3600
        if pd.isna(ref_ccu) or ref_ccu == 0 or gap_hours > 96:
            continue
        delta = live_ccu - ref_ccu
        pct   = delta / ref_ccu * 100
        label = f"{days}d ago ({ref_dt.strftime('%d %b %Y')})"
        result[aid] = {
            "prev_ccu":    int(ref_ccu),
            "delta":       int(delta),
            "delta_pct":   pct,
            "source":      "SteamDB CSV",
            "period_label": label,
            "ref_dt":      ref_dt.isoformat(),
        }
    return result

# ─────────────────────────────────────────────────────────────
# PPTX EXPORT  (generates via pptxgenjs node script)
# ─────────────────────────────────────────────────────────────

def build_pptx_script(report_md: str, ccu_data: list[dict], label: str) -> str:
    """
    Generate a pptxgenjs Node.js script styled to the SEGA.com brand guide:
      - Backgrounds: #050818 (near-black) / #0D1126 (dark navy) / #002266 (section accent)
      - Primary accent: #0057FF (SEGA blue), secondary highlight #E1EAFF
      - Typography: Inter Tight ExtraBold (headings), Poppins (body)
      - Motif: thick left-side blue border on content slides, oversized display numbers
      - Layouts alternate between: full-bleed header, two-column, stat callout, bullet list
    """

    # ── helpers ──────────────────────────────────────────────
    def js_str(s: str) -> str:
        return (s.replace("\\", "\\\\")
                 .replace("`", "\\`")
                 .replace("${", "\\${")
                 .replace("\n", " "))

    def js_arr(items: list[dict]) -> str:
        """Render a pptxgenjs text array from [{text, bold, sub}]."""
        parts = []
        for it in items:
            color   = "0057FF" if it.get("sub") else ("E1EAFF" if it.get("bold") else "C3C5D5")
            size    = 13 if it.get("bold") else 11
            bullet  = "false" if it.get("bold") or it.get("sub") else "true"
            spacing = 6 if it.get("bold") else 3
            parts.append(
                f'{{text:`{js_str(it["text"][:140])}`,options:{{bold:{"true" if it.get("bold") else "false"},'
                f'fontSize:{size},color:"{color}",bullet:{bullet},'
                f'fontFace:"Poppins",paraSpaceAfter:{spacing}}}}}'
            )
        return ",\n      ".join(parts)

    # ── parse markdown into slide objects ────────────────────
    lines   = report_md.split("\n")
    slides  = []
    current = {"title": "", "items": [], "stat": None}

    for line in lines:
        if line.startswith("## "):
            if current["title"] or current["items"]:
                slides.append(current)
            current = {"title": line[3:].strip(), "items": [], "stat": None}
        elif line.startswith("### "):
            current["items"].append({"text": line[4:].strip(), "bold": True})
        elif line.startswith("- ") or line.startswith("* "):
            current["items"].append({"text": line[2:].strip(), "bold": False})
        elif line.strip() and not line.startswith("#") and len(line) < 220:
            # detect bold **stat** patterns for callout layout
            stripped = line.strip().lstrip("*").rstrip("*")
            current["items"].append({"text": stripped, "bold": False})

    if current["title"] or current["items"]:
        slides.append(current)

    slides = slides[:14]

    # ── CCU stat cards for title slide ───────────────────────
    top5     = ccu_data[:5]
    top5_str = "   ·   ".join(f"{r['name']}  {r['ccu']:,}" for r in top5)
    date_str = datetime.utcnow().strftime("%B %d, %Y")

    # ── per-slide JS ─────────────────────────────────────────
    slide_js_parts = []
    LAYOUTS = ["border", "accent", "border", "split", "border", "accent",
               "border", "split", "border", "accent", "border", "split", "border", "border"]

    for idx, s in enumerate(slides):
        layout  = LAYOUTS[idx % len(LAYOUTS)]
        title_e = js_str(s["title"][:70])
        items   = s["items"][:14]
        arr     = js_arr(items)

        if layout == "border":
            # Dark navy bg + thick left blue border accent bar
            block = f"""
  // ── Slide {idx+1}: {title_e[:35]} (border layout) ──
  slide = pptx.addSlide();
  slide.background = {{color:"0D1126"}};
  slide.addShape(pptx.ShapeType.rect, {{x:0,   y:0, w:0.07, h:"100%", fill:{{color:"0057FF"}}}});
  slide.addShape(pptx.ShapeType.rect, {{x:0.07,y:0, w:"100%", h:0.06, fill:{{color:"002266"}}}});
  slide.addText(`{title_e}`, {{
    x:0.35, y:0.18, w:9.3, h:0.72,
    fontSize:26, bold:true, color:"FFFFFF",
    fontFace:"Inter Tight", charSpacing:-0.5
  }});
  slide.addText([{arr}], {{
    x:0.35, y:1.05, w:9.3, h:5.55,
    valign:"top", fontFace:"Poppins", paraSpaceAfter:4
  }});
  slide.addShape(pptx.ShapeType.rect, {{x:0.35,y:6.78,w:9.3,h:0.005,fill:{{color:"002266"}}}});
  slide.addText("SEGA Shooter Intelligence  ·  Internal Use Only  ·  {date_str}", {{
    x:0.35, y:6.82, w:9.3, h:0.2, fontSize:7.5, color:"4A5080", fontFace:"Poppins"
  }});"""

        elif layout == "accent":
            # SEGA blue header band, dark body
            block = f"""
  // ── Slide {idx+1}: {title_e[:35]} (accent layout) ──
  slide = pptx.addSlide();
  slide.background = {{color:"050818"}};
  slide.addShape(pptx.ShapeType.rect, {{x:0, y:0, w:"100%", h:1.1, fill:{{color:"0057FF"}}}});
  slide.addText(`{title_e}`, {{
    x:0.5, y:0.18, w:9.0, h:0.75,
    fontSize:28, bold:true, color:"FFFFFF",
    fontFace:"Inter Tight", charSpacing:-0.5
  }});
  slide.addText([{arr}], {{
    x:0.5, y:1.25, w:9.0, h:5.35,
    valign:"top", fontFace:"Poppins", paraSpaceAfter:5
  }});
  slide.addText("SEGA Shooter Intelligence  ·  Internal Use Only", {{
    x:0.5, y:6.82, w:9.0, h:0.2, fontSize:7.5, color:"4A5080", fontFace:"Poppins"
  }});"""

        else:  # split — title left column, bullets right column
            half = max(1, len(items) // 2)
            left_items  = items[:half]
            right_items = items[half:]
            arr_l = js_arr(left_items)
            arr_r = js_arr(right_items)
            block = f"""
  // ── Slide {idx+1}: {title_e[:35]} (split layout) ──
  slide = pptx.addSlide();
  slide.background = {{color:"0D1126"}};
  slide.addShape(pptx.ShapeType.rect, {{x:0,    y:0, w:"100%", h:0.06, fill:{{color:"0057FF"}}}});
  slide.addShape(pptx.ShapeType.rect, {{x:4.85, y:0.06, w:0.04, h:"100%", fill:{{color:"002266"}}}});
  slide.addText(`{title_e}`, {{
    x:0.4, y:0.2, w:9.2, h:0.7,
    fontSize:24, bold:true, color:"FFFFFF",
    fontFace:"Inter Tight", charSpacing:-0.5
  }});
  slide.addText([{arr_l}], {{
    x:0.4, y:1.05, w:4.2, h:5.55,
    valign:"top", fontFace:"Poppins", paraSpaceAfter:5
  }});
  slide.addText([{arr_r}], {{
    x:5.1, y:1.05, w:4.55, h:5.55,
    valign:"top", fontFace:"Poppins", paraSpaceAfter:5
  }});
  slide.addText("SEGA Shooter Intelligence  ·  Internal Use Only", {{
    x:0.4, y:6.82, w:9.2, h:0.2, fontSize:7.5, color:"4A5080", fontFace:"Poppins"
  }});"""

        slide_js_parts.append(block)

    all_slides = "\n".join(slide_js_parts)

    # ── CCU stat cards slide (if data available) ─────────────
    stat_cards_js = ""
    if ccu_data:
        top6      = ccu_data[:6]
        card_w    = 1.5
        card_gap  = 0.1
        card_y    = 2.2
        cards_total_w = len(top6) * card_w + (len(top6) - 1) * card_gap
        start_x   = (10 - cards_total_w) / 2
        card_blocks = ""
        for ci, r in enumerate(top6):
            cx    = start_x + ci * (card_w + card_gap)
            yoy_v = r.get("yoy_val", 0)
            yoy_s = js_str(r.get("yoy", "N/A"))
            yoy_c = "20C65A" if yoy_v > 0 else ("FF3D52" if yoy_v < 0 else "C3C5D5")
            name_s = js_str(r["name"][:14])
            ccu_raw = r["ccu"]
            if ccu_raw >= 1_000_000:
                ccu_s = f"{ccu_raw/1_000_000:.2f}M"
            elif ccu_raw >= 1_000:
                ccu_s = f"{ccu_raw/1_000:.1f}K"
            else:
                ccu_s = str(ccu_raw)
            card_blocks += f"""
  slide.addShape(pptx.ShapeType.rect, {{x:{cx:.2f},y:{card_y:.2f},w:{card_w},h:1.9,
    fill:{{color:"0D1126"}}, line:{{color:"002266",pt:1}}}});
  slide.addShape(pptx.ShapeType.rect, {{x:{cx:.2f},y:{card_y:.2f},w:{card_w},h:0.06,
    fill:{{color:"0057FF"}}}});
  slide.addText(`{name_s}`,{{x:{cx+0.1:.2f},y:{card_y+0.12:.2f},w:{card_w-0.2},h:0.38,
    fontSize:9,bold:true,color:"E1EAFF",fontFace:"Inter Tight",wrap:true}});
  slide.addText(`{ccu_s}`,{{x:{cx+0.1:.2f},y:{card_y+0.55:.2f},w:{card_w-0.2},h:0.65,
    fontSize:22,bold:true,color:"FFFFFF",fontFace:"Inter Tight"}});
  slide.addText(`{yoy_s} YoY`,{{x:{cx+0.1:.2f},y:{card_y+1.22:.2f},w:{card_w-0.2},h:0.3,
    fontSize:10,bold:true,color:"{yoy_c}",fontFace:"Poppins"}});
  slide.addText("live CCU",{{x:{cx+0.1:.2f},y:{card_y+1.56:.2f},w:{card_w-0.2},h:0.22,
    fontSize:7.5,color:"4A5080",fontFace:"Poppins"}});"""

        stat_cards_js = f"""
  // ── CCU Snapshot slide ──
  slide = pptx.addSlide();
  slide.background = {{color:"050818"}};
  slide.addShape(pptx.ShapeType.rect, {{x:0, y:0, w:"100%", h:0.06, fill:{{color:"0057FF"}}}});
  slide.addText("LIVE CCU SNAPSHOT", {{
    x:0.5, y:0.18, w:9.0, h:0.55,
    fontSize:28, bold:true, color:"FFFFFF", fontFace:"Inter Tight", charSpacing:2
  }});
  slide.addText("Steam concurrent users at time of export  ·  Source: Steam public API", {{
    x:0.5, y:0.78, w:9.0, h:0.3,
    fontSize:10, color:"C3C5D5", fontFace:"Poppins"
  }});
  {card_blocks}
  slide.addText("SEGA Shooter Intelligence  ·  Internal Use Only  ·  {date_str}", {{
    x:0.5, y:6.82, w:9.0, h:0.2, fontSize:7.5, color:"4A5080", fontFace:"Poppins"
  }});"""

    return f"""const PptxGenJS = require("pptxgenjs");
const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE";
pptx.author  = "SEGA Shooter Intelligence";
pptx.subject = "{js_str(label)}";
pptx.company = "SEGA";

let slide;

// ══════════════════════════════════════════════
// TITLE SLIDE
// ══════════════════════════════════════════════
slide = pptx.addSlide();
slide.background = {{color:"050818"}};

// Full-bleed deep blue left panel
slide.addShape(pptx.ShapeType.rect, {{x:0, y:0, w:4.6, h:"100%", fill:{{color:"002266"}}}});
// SEGA blue accent stripe on left edge
slide.addShape(pptx.ShapeType.rect, {{x:0, y:0, w:0.12, h:"100%", fill:{{color:"0057FF"}}}});
// Subtle top bar
slide.addShape(pptx.ShapeType.rect, {{x:0, y:0, w:"100%", h:0.06, fill:{{color:"0057FF"}}}});

// "SEGA" logotype
slide.addText("SEGA", {{
  x:0.35, y:1.4, w:3.9, h:1.2,
  fontSize:72, bold:true, color:"FFFFFF",
  fontFace:"Inter Tight", charSpacing:-2
}});

// Thin rule below SEGA
slide.addShape(pptx.ShapeType.rect, {{x:0.35, y:2.68, w:3.6, h:0.04, fill:{{color:"0057FF"}}}});

// "SHOOTER INTELLIGENCE"
slide.addText("SHOOTER\\nINTELLIGENCE", {{
  x:0.35, y:2.82, w:4.0, h:1.1,
  fontSize:20, bold:true, color:"E1EAFF",
  fontFace:"Inter Tight", charSpacing:1.5, lineSpacingMultiple:1.1
}});

// Report label (right panel)
slide.addText("{js_str(label)}", {{
  x:4.9, y:1.6, w:4.7, h:0.9,
  fontSize:32, bold:true, color:"FFFFFF",
  fontFace:"Inter Tight", charSpacing:-0.5, wrap:true
}});
slide.addText("{date_str}", {{
  x:4.9, y:2.6, w:4.7, h:0.4,
  fontSize:13, color:"C3C5D5", fontFace:"Poppins"
}});
slide.addText("Internal Use Only", {{
  x:4.9, y:3.1, w:4.7, h:0.3,
  fontSize:10, color:"0057FF", bold:true, fontFace:"Poppins", charSpacing:2
}});

// Top CCU ticker at bottom right
slide.addText("{js_str(top5_str)}", {{
  x:4.9, y:6.3, w:4.7, h:0.4,
  fontSize:8, color:"4A5080", fontFace:"Poppins", wrap:true
}});

// Footer
slide.addText("SEGA Shooter Intelligence  ·  {date_str}", {{
  x:0.35, y:6.82, w:9.3, h:0.2, fontSize:7.5, color:"323760", fontFace:"Poppins"
}});

{stat_cards_js}

{all_slides}

// ══════════════════════════════════════════════
// CLOSING SLIDE
// ══════════════════════════════════════════════
slide = pptx.addSlide();
slide.background = {{color:"050818"}};
slide.addShape(pptx.ShapeType.rect, {{x:0, y:0, w:0.12, h:"100%", fill:{{color:"0057FF"}}}});
slide.addShape(pptx.ShapeType.rect, {{x:0, y:0, w:"100%", h:0.06, fill:{{color:"0057FF"}}}});
slide.addText("SEGA", {{
  x:0.5, y:2.2, w:9.0, h:1.4,
  fontSize:80, bold:true, color:"002266",
  fontFace:"Inter Tight", charSpacing:-3, align:"center"
}});
slide.addText("SHOOTER INTELLIGENCE", {{
  x:0.5, y:3.65, w:9.0, h:0.55,
  fontSize:16, bold:true, color:"0057FF",
  fontFace:"Inter Tight", charSpacing:4, align:"center"
}});
slide.addText("{date_str}  ·  Internal Use Only", {{
  x:0.5, y:6.62, w:9.0, h:0.3,
  fontSize:9, color:"4A5080", fontFace:"Poppins", align:"center"
}});

pptx.writeFile({{fileName:"report.pptx"}})
  .then(()=>{{ process.exit(0); }})
  .catch(e=>{{ console.error(e); process.exit(1); }});
"""

def generate_pptx_bytes(report_md: str, ccu_data: list[dict], label: str) -> bytes | None:
    """Run pptxgenjs and return bytes of the generated pptx."""
    import subprocess, tempfile
    script = build_pptx_script(report_md, ccu_data, label)
    with tempfile.TemporaryDirectory() as tmp:
        script_path = Path(tmp) / "gen.js"
        out_path    = Path(tmp) / "report.pptx"
        script_path.write_text(script)
        # Install pptxgenjs if not present
        subprocess.run(["npm", "install", "pptxgenjs"], cwd=tmp,
                       capture_output=True, timeout=60)
        result = subprocess.run(["node", "gen.js"], cwd=tmp,
                                capture_output=True, timeout=30)
        if result.returncode == 0 and out_path.exists():
            return out_path.read_bytes()
    return None

# ─────────────────────────────────────────────────────────────
# GAME DRILL-DOWN PROMPT
# ─────────────────────────────────────────────────────────────

def build_drilldown_prompt(game: dict, historical: dict) -> str:
    hs   = game.get("hist_summary", {})
    mdf  = historical.get(game["app_id"])
    src  = "SteamDB CSV" if game.get("has_hist") else "SteamSpy proxy"

    # Last 12 months table for prompt
    history_table = ""
    if mdf is not None and not mdf.empty:
        last_12 = mdf.tail(12)
        rows = []
        for _, row in last_12.iterrows():
            rows.append(
                f"  {str(row['month'])}: peak {int(row['peak_ccu']):,}"
                + (f" / avg {int(row['avg_ccu']):,}" if not pd.isna(row["avg_ccu"]) else "")
            )
        history_table = "\n".join(rows)

    return f"""## Deep Dive: {game['name']}

**Publisher:** {game['publisher']}  |  **Sub-genre:** {game['sub']}  |  **F2P:** {"Yes" if game['f2p'] else "No"}

### Current Data
- Live CCU: {game['ccu']:,}
- YoY: {game.get('yoy','N/A')} [{src}]
- Peak ever: {hs.get('peak_ever', 'Unknown'):,} | Peak 12m: {hs.get('peak_12m', 'Unknown'):,}
- Avg CCU 12m: {hs.get('avg_12m', 'Unknown'):,} | MoM trend: {hs.get('mom_trend','—')}
- Review score: {game.get('review_pct','?')}% positive | Est. owners: {game.get('owners','Unknown')}
- Avg hrs played/2wk: {game.get('avg_2w_hrs','?')}

### Monthly CCU History (last 12 months)
{history_table if history_table else "No historical data available."}

### Provide a focused analysis with these sections:

1. **Performance Summary** — How is this title performing right now vs. its own history? Is it growing, peaking, or declining?
2. **Player Retention Signals** — What do the CCU trends and engagement metrics suggest about retention health?
3. **Competitive Position** — Where does this title sit in the broader shooter market? Who are its closest competitors right now?
4. **Key Risk Factors** — What are the 2-3 biggest threats to this title's playerbase over the next 6 months?
5. **SEGA Relevance** — What can SEGA learn from this title's trajectory? Any mechanics, monetisation, or community strategies worth noting?

Cite all external benchmarks and industry figures. Be specific and commercially sharp."""

# ─────────────────────────────────────────────────────────────
# GENRE AGGREGATION
# ─────────────────────────────────────────────────────────────

def compute_genre_share(ccu_data: list[dict]) -> pd.DataFrame:
    """Aggregate CCU by sub-genre for the heat map."""
    genre_map: dict[str, int] = {}
    for r in ccu_data:
        genre = r["sub"].split("/")[0].strip()
        genre_map[genre] = genre_map.get(genre, 0) + r["ccu"]
    df = pd.DataFrame([
        {"Sub-genre": g, "Total CCU": v,
         "Share %": v / max(sum(genre_map.values()), 1) * 100}
        for g, v in sorted(genre_map.items(), key=lambda x: x[1], reverse=True)
    ])
    return df

# ─────────────────────────────────────────────────────────────
# REPORT HASH  (for analysis caching)
# ─────────────────────────────────────────────────────────────

def data_hash(ccu_data: list[dict]) -> str:
    import hashlib
    sig = json.dumps([{"id": r["app_id"], "ccu": r["ccu"]} for r in ccu_data], sort_keys=True)
    return hashlib.md5(sig.encode()).hexdigest()[:12]

# ─────────────────────────────────────────────────────────────
# ANNOTATIONS  (events to overlay on history chart)
# ─────────────────────────────────────────────────────────────

ANNOTATIONS: dict[int, list[dict]] = {
    730:     [{"month": "2023-09", "label": "CS2 Launch"},
              {"month": "2024-04", "label": "Premier update"},
              {"month": "2025-04", "label": "All-time peak"}],
    1172470: [{"month": "2023-02", "label": "Season 16 (peak)"},
              {"month": "2024-06", "label": "Season 22"},
              {"month": "2025-01", "label": "Revival event"}],
    578080:  [{"month": "2022-01", "label": "F2P switch"},
              {"month": "2023-03", "label": "Season 20"}],
    1808500: [{"month": "2025-10", "label": "Early Access launch"}],
    2767030: [{"month": "2024-12", "label": "Global launch"}],
    230410:  [{"month": "2023-04", "label": "Duviri Paradox"},
              {"month": "2024-11", "label": "1999 update"}],
    2668510: [{"month": "2024-02", "label": "Global launch"},
              {"month": "2024-05", "label": "Major patch / peak"}],
    1237970: [{"month": "2022-02", "label": "Witch Queen launch"},
              {"month": "2024-06", "label": "The Final Shape"}],
    359550:  [{"month": "2021-06", "label": "F2P launch"},
              {"month": "2023-08", "label": "Operation Solar Raid"}],
    1509960: [{"month": "2023-08", "label": "AC6 Launch"},
              {"month": "2024-04", "label": "DLC: Fires of Raven"}],
    1238810: [{"month": "2022-11", "label": "BF2042 launch"},
              {"month": "2023-09", "label": "Season 6 / F2P"}],
    2933620: [{"month": "2024-09", "label": "Beta access begins"}],
    1449560: [{"month": "2022-10", "label": "OW2 launch (F2P)"},
              {"month": "2023-08", "label": "Invasion update"}],
}


# ─────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────

defaults = {
    "claude_key":      st.secrets.get("CLAUDE_KEY", os.environ.get("CLAUDE_KEY", "")),
    "ccu_data":        [],
    "active_query":    None,
    "ai_report":       "",
    "ai_chat_history": [],
    "ai_chat_pending": False,
    "report_label":    "",
    "custom_query":    "",
    "report_cache":    {},      # {hash+query_key: report_text}
    "drilldown_game":  None,    # app_id of selected game
    "drilldown_report": "",     # cached drill-down report
    "watchlist":       [],      # list of app_ids pinned by user
    "active_view":     "main",  # "main" | "drilldown"
    "ccu_fetched_at":  None,    # datetime of last fetch
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
  <div class="topbar-pill">Internal Use Only</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="font-family:'Inter Tight',sans-serif;font-weight:900;font-size:1rem;
    letter-spacing:.1em;text-transform:uppercase;color:#4080ff;margin-bottom:1rem;">
    Configuration</div>
    """, unsafe_allow_html=True)

    _cl_ok = bool(st.session_state.claude_key)
    if _cl_ok:
        st.success("Anthropic API key loaded")
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

    # Last updated
    if st.session_state.ccu_fetched_at:
        st.caption(f"⏱ CCU last fetched: {st.session_state.ccu_fetched_at.strftime('%H:%M UTC, %d %b %Y')}")

    st.markdown("---")
    historical_sb = load_all_historical()
    hist_ids   = set(historical_sb.keys())
    roster_ids = {g["app_id"] for g in SHOOTER_ROSTER}
    loaded     = hist_ids & roster_ids
    missing    = roster_ids - hist_ids
    st.caption(f"SteamDB CSVs: {len(loaded)}/{len(roster_ids)} loaded")
    if missing:
        missing_names = [g["name"] for g in SHOOTER_ROSTER if g["app_id"] in missing]
        st.caption("Missing: " + ", ".join(missing_names))
    st.caption("Drop steamdb_chart_{appid}.csv into /data to update")

    st.markdown("---")
    # Watchlist management
    st.markdown("""<div style="font-size:.65rem;font-weight:800;letter-spacing:.18em;
    text-transform:uppercase;color:#5a5f82;margin-bottom:.5rem;">My Watchlist</div>""",
    unsafe_allow_html=True)
    for g in SHOOTER_ROSTER:
        is_pinned = g["app_id"] in st.session_state.watchlist
        label = f"{'[pinned]' if is_pinned else ''} {g['name']}"
        if st.button(label, key=f"pin_{g['app_id']}",
                     type="primary" if is_pinned else "secondary",
                     use_container_width=True):
            if is_pinned:
                st.session_state.watchlist.remove(g["app_id"])
            else:
                if len(st.session_state.watchlist) < 5:
                    st.session_state.watchlist.append(g["app_id"])
            st.rerun()
    if len(st.session_state.watchlist) >= 5:
        st.caption("Max 5 pinned titles")

# ─────────────────────────────────────────────────────────────
# BACK BUTTON (drill-down view)
# ─────────────────────────────────────────────────────────────

if st.session_state.active_view == "drilldown":
    if st.button("← Back to Dashboard", key="back_main"):
        st.session_state.active_view    = "main"
        st.session_state.drilldown_game  = None
        st.session_state.drilldown_report = ""
        st.rerun()

# ─────────────────────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────────────────────

if st.session_state.active_view == "main":
    st.markdown("""
    <div class="hero">
      <div class="hero-title">SHOOTER MARKET<br><span class="accent">INTELLIGENCE</span></div>
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# DRILL-DOWN VIEW
# ═══════════════════════════════════════════════════════════════

if st.session_state.active_view == "drilldown" and st.session_state.drilldown_game is not None:
    historical = load_all_historical()
    game = next((r for r in st.session_state.ccu_data
                 if r["app_id"] == st.session_state.drilldown_game), None)

    if game is None:
        st.warning("Game data not found — please fetch CCU data first.")
    else:
        hs   = game.get("hist_summary", {})
        mdf  = historical.get(game["app_id"])

        # ── Title bar ──
        st.markdown(f"""
        <div class="section-header" style="margin-top:0">
          <span class="dot"></span>{game['name'].upper()} — DEEP DIVE
          <span style="color:var(--muted);font-size:.7rem;margin-left:.5rem;">{game['sub']} · {game['publisher']}</span>
        </div>
        """, unsafe_allow_html=True)

        # ── KPI row ──
        d1, d2, d3, d4, d5 = st.columns(5)
        peak_health = (game['ccu'] / hs['peak_ever'] * 100) if hs.get('peak_ever') else None
        ph_color = "var(--pos)" if peak_health and peak_health > 50 else "var(--amber)" if peak_health and peak_health > 25 else "var(--neg)"
        for col, label, val, sub in [
            (d1, "Live CCU",      f"{game['ccu']:,}",                             "right now"),
            (d2, "YoY Change",    game.get('yoy','N/A'),                           "vs same month last year"),
            (d3, "Peak Ever",     f"{hs['peak_ever']:,}" if hs.get('peak_ever') else "—", "all-time"),
            (d4, "Peak 12m",      f"{hs['peak_12m']:,}"  if hs.get('peak_12m')  else "—", "rolling 12 months"),
            (d5, "Peak Health",   f"{peak_health:.0f}%"  if peak_health else "—",  "current vs all-time peak"),
        ]:
            with col:
                color = ph_color if label == "Peak Health" else ("var(--pos)" if game.get('yoy_val', 0) > 0 and label == "YoY Change" else "inherit")
                st.markdown(f"""<div class="metric-card blue-top">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color:{color}">{val}</div>
                <div class="metric-sub">{sub}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Full history chart with annotations ──
        if mdf is not None and not mdf.empty:
            fig_dd = go.Figure()
            fig_dd.add_trace(go.Scatter(
                x=[str(p) for p in mdf["month"]],
                y=mdf["peak_ccu"],
                mode="lines",
                name="Peak CCU",
                line=dict(color="#4080ff", width=2),
                fill="tozeroy",
                fillcolor="rgba(64,128,255,0.07)",
                hovertemplate="<b>%{x}</b><br>Peak CCU: %{y:,}<extra></extra>",
            ))
            if not mdf["avg_ccu"].isna().all():
                fig_dd.add_trace(go.Scatter(
                    x=[str(p) for p in mdf["month"]],
                    y=mdf["avg_ccu"],
                    mode="lines",
                    name="Avg CCU",
                    line=dict(color="#20c65a", width=1.5, dash="dot"),
                    hovertemplate="<b>%{x}</b><br>Avg CCU: %{y:,}<extra></extra>",
                ))
            # Add annotations
            for ann in ANNOTATIONS.get(game["app_id"], []):
                row = mdf[mdf["month"] == ann["month"]]
                if not row.empty:
                    y_val = row.iloc[0]["peak_ccu"]
                    fig_dd.add_annotation(
                        x=ann["month"], y=y_val,
                        text=ann["label"],
                        showarrow=True, arrowhead=2, arrowcolor="#ffb938",
                        font=dict(size=9, color="#ffb938"),
                        bgcolor="rgba(15,17,32,0.85)",
                        bordercolor="#ffb938", borderwidth=1,
                        ay=-36,
                    )
            fig_dd.update_layout(
                **PLOTLY_BASE,
                title=dict(text=f"{game['name']} — Full CCU History (SteamDB)", font=dict(size=13, color="#b8bcd4"), x=0),
                xaxis=dict(showgrid=False, tickangle=-45, tickfont=dict(size=8)),
                yaxis=dict(showgrid=True, gridcolor="#1a1e30", tickformat=","),
                height=400,
                legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig_dd, use_container_width=True)
            st.caption(f"Source: SteamDB CSV · {hs.get('months_data',0)} months of data · Annotations mark key events")
        else:
            st.info("No historical CSV data for this title. Drop steamdb_chart_{game['app_id']}.csv into /data.")

        # ── Supplemental stats ──
        st.markdown("<br>", unsafe_allow_html=True)
        ss1, ss2, ss3 = st.columns(3)
        with ss1:
            st.markdown(f"""<div class="metric-card amber-top">
            <div class="metric-label">Review Score</div>
            <div class="metric-value">{game.get('review_pct','?')}%</div>
            <div class="metric-sub">{game.get('pos_reviews',0):,} positive reviews (SteamSpy)</div>
            </div>""", unsafe_allow_html=True)
        with ss2:
            st.markdown(f"""<div class="metric-card pos-top">
            <div class="metric-label">Avg Hrs Played / 2wk</div>
            <div class="metric-value">{game.get('avg_2w_hrs','?')}</div>
            <div class="metric-sub">per owner, last 14 days (SteamSpy)</div>
            </div>""", unsafe_allow_html=True)
        with ss3:
            st.markdown(f"""<div class="metric-card purple-top">
            <div class="metric-label">Est. Owners</div>
            <div class="metric-value" style="font-size:1rem">{game.get('owners','Unknown')}</div>
            <div class="metric-sub">SteamSpy band estimate</div>
            </div>""", unsafe_allow_html=True)

        # ── AI drill-down analysis ──
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="section-header">
          <span class="dot"></span>AI DEEP DIVE — {game['name'].upper()}
        </div>
        """, unsafe_allow_html=True)

        if not st.session_state.claude_key:
            st.warning("CLAUDE_KEY not found. Add it to .streamlit/secrets.toml to run AI analysis.")
        elif not ANTHROPIC_AVAILABLE:
            st.error("Install the `anthropic` package: `pip install anthropic`")
        else:
            drill_cache_key = f"drill_{game['app_id']}_{game['ccu']}"
            if st.session_state.drilldown_report and st.session_state.get("drilldown_cache_key") == drill_cache_key:
                st.markdown(st.session_state.drilldown_report)
            else:
                if st.button(f"Generate Deep Dive — {game['name']}", key="run_drilldown"):
                    with st.spinner(f"Analysing {game['name']}…"):
                        prompt = build_drilldown_prompt(game, historical)
                        ph_dd = st.empty()
                        report_text = ""
                        try:
                            client = _anthropic.Anthropic(api_key=st.session_state.claude_key)
                            with client.messages.stream(
                                model="claude-sonnet-4-20250514",
                                max_tokens=3000,
                                system=build_system_prompt(),
                                messages=[{"role": "user", "content": prompt}],
                            ) as stream:
                                for delta in stream.text_stream:
                                    report_text += delta
                                    ph_dd.markdown(report_text + "▌")
                            ph_dd.markdown(report_text)
                            st.session_state.drilldown_report    = report_text
                            st.session_state.drilldown_cache_key = drill_cache_key
                        except Exception as e:
                            st.error(f"Analysis error: {e}")

            # Download drill-down
            if st.session_state.drilldown_report:
                slug = re.sub(r"[^a-z0-9]+", "_", game["name"].lower())
                st.download_button("Download Deep Dive (.md)",
                    data=st.session_state.drilldown_report,
                    file_name=f"sega_drilldown_{slug}.md",
                    mime="text/markdown", key="dl_drill")

# ═══════════════════════════════════════════════════════════════
# MAIN DASHBOARD VIEW
# ═══════════════════════════════════════════════════════════════

elif st.session_state.active_view == "main":

    # ─────────────────────────────────────────────────────────
    # WATCHLIST PANEL (shown when pinned titles exist)
    # ─────────────────────────────────────────────────────────

    if st.session_state.watchlist and st.session_state.ccu_data:
        st.markdown("""
        <div class="section-header">
          <span class="dot"></span>MY WATCHLIST
        </div>
        """, unsafe_allow_html=True)
        pinned = [r for r in st.session_state.ccu_data
                  if r["app_id"] in st.session_state.watchlist]
        wcols = st.columns(min(len(pinned), 5))
        for col, r in zip(wcols, pinned):
            yoy_color = "var(--pos)" if r.get("yoy_val", 0) > 0 else "var(--neg)" if r.get("yoy_val", 0) < 0 else "var(--muted)"
            with col:
                st.markdown(f"""<div class="metric-card blue-top" style="cursor:pointer">
                <div class="metric-label">{r['name'][:20]}</div>
                <div class="metric-value" style="font-size:1rem">{r['ccu']:,}</div>
                <div class="metric-sub" style="color:{yoy_color}">YoY {r.get('yoy','N/A')}</div>
                </div>""", unsafe_allow_html=True)
                if st.button("Drill Down", key=f"watch_drill_{r['app_id']}"):
                    st.session_state.drilldown_game   = r["app_id"]
                    st.session_state.drilldown_report  = ""
                    st.session_state.active_view       = "drilldown"
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # QUERY BLOCK
    # ─────────────────────────────────────────────────────────

    st.markdown('<div class="query-block">', unsafe_allow_html=True)
    st.markdown("""
    <div class="section-header" style="margin-top:0">
      <span class="dot"></span>SELECT ANALYSIS TYPE
    </div>
    """, unsafe_allow_html=True)

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
                st.session_state.active_query  = preset["prompt_key"]
                st.session_state.ai_report     = ""
                st.session_state.ai_chat_history = []
                st.session_state.report_label  = preset["label"]
                st.rerun()

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
        st.session_state.custom_query    = custom.strip()
        st.session_state.active_query    = "custom"
        st.session_state.ai_report       = ""
        st.session_state.ai_chat_history = []
        st.session_state.report_label    = "Custom Query"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # LIVE CCU PANEL
    # ─────────────────────────────────────────────────────────

    st.markdown("""
    <div class="section-header">
      <span class="dot"></span>LIVE STEAM CCU SNAPSHOT
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.ccu_data:
        if st.button("Fetch Live CCU Data", key="fetch_ccu"):
            with st.spinner("Pulling live CCU from Steam + SteamSpy…"):
                historical = load_all_historical()
                raw_data   = load_all_raw()
                results    = []
                prog       = st.progress(0.0)
                status     = st.empty()
                for idx, game in enumerate(SHOOTER_ROSTER):
                    status.caption(f"Fetching: {game['name']}…")
                    ccu     = fetch_ccu(game["app_id"])
                    hist_df = historical.get(game["app_id"])
                    has_hist = hist_df is not None and not hist_df.empty
                    if has_hist:
                        yoy_str, yoy_pct = compute_yoy(hist_df)
                        hist_summary     = get_historical_summary(hist_df)
                    else:
                        ss               = fetch_steamspy(game["app_id"])
                        yoy_str, yoy_pct = parse_yoy_from_steamspy(ss)
                        hist_summary     = {}
                    ss          = fetch_steamspy(game["app_id"])
                    owners      = ss.get("owners", "Unknown")
                    avg_2w_hrs  = round((ss.get("average_2weeks", 0) or 0) / 60, 1)
                    pos_reviews = ss.get("positive", 0) or 0
                    neg_reviews = ss.get("negative", 0) or 0
                    total_rev   = pos_reviews + neg_reviews
                    review_pct  = round(pos_reviews / total_rev * 100, 1) if total_rev else None
                    results.append({
                        **game,
                        # Fall back to latest CSV row if API returns 0 or None
                        # (e.g. Deadlock blocks the public CCU endpoint)
                        "ccu":          ccu if ccu else (
                            int(raw_data[game["app_id"]].dropna(subset=["Players"])["Players"].iloc[-1])
                            if game["app_id"] in raw_data and not raw_data[game["app_id"]].empty
                            else 0
                        ),
                        "ccu_from_csv": not bool(ccu),
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
                    time.sleep(0.4)
                status.empty()
                results.sort(key=lambda x: x["ccu"], reverse=True)
                st.session_state.ccu_data      = results
                st.session_state.ccu_fetched_at = datetime.utcnow()
            st.rerun()

    else:
        ccu_data = st.session_state.ccu_data
        raw_data = load_all_raw()
        wow_diff = compute_period_diff(ccu_data, raw_data, days=7)

        # ── Derived stats ──
        total_ccu  = sum(r["ccu"] for r in ccu_data)
        top_title  = ccu_data[0]["name"]
        top_ccu    = ccu_data[0]["ccu"]
        f2p_share  = sum(r["ccu"] for r in ccu_data if r["f2p"]) / max(total_ccu, 1) * 100
        hist_count = sum(1 for r in ccu_data if r.get("has_hist"))

        yoy_titled = [(r["name"], r["yoy_val"], r.get("yoy","N/A"), r.get("has_hist", False))
                      for r in ccu_data if r.get("yoy","N/A") != "N/A"]
        growing    = sum(1 for _, v, _, _ in yoy_titled if v > 0)
        declining  = sum(1 for _, v, _, _ in yoy_titled if v < 0)

        csv_yoy     = [(r["name"], r["yoy_val"]) for r in ccu_data
                       if r.get("has_hist") and r.get("yoy","N/A") != "N/A"]
        best_mover  = max(csv_yoy, key=lambda x: x[1],  default=("—", 0))
        worst_mover = min(csv_yoy, key=lambda x: x[1], default=("—", 0))

        health_ratios = []
        for r in ccu_data:
            hs = r.get("hist_summary", {})
            if hs.get("peak_ever") and r["ccu"] > 0:
                health_ratios.append(r["ccu"] / hs["peak_ever"] * 100)
        avg_health = sum(health_ratios) / len(health_ratios) if health_ratios else 0

        # ── Compute MoM growth balance from raw CSV data ──
        mom_growing  = sum(1 for r in ccu_data if wow_diff.get(r["app_id"], {}).get("delta", 0) > 0
                           and r.get("has_hist"))  # reuse 7d diff as proxy until monthly computed
        # Real MoM from historical monthly summaries
        mom_up   = sum(1 for r in ccu_data if (r.get("hist_summary") or {}).get("mom_pct") is not None
                       and (r.get("hist_summary") or {}).get("mom_pct", 0) > 0)
        mom_down = sum(1 for r in ccu_data if (r.get("hist_summary") or {}).get("mom_pct") is not None
                       and (r.get("hist_summary") or {}).get("mom_pct", 0) < 0)
        mom_total = mom_up + mom_down

        # WoW balance from compute_period_diff (7-day CSV lookback)
        wow_up   = sum(1 for v in wow_diff.values() if v["delta"] > 0)
        wow_down = sum(1 for v in wow_diff.values() if v["delta"] < 0)
        wow_total = len(wow_diff)

        # ── Row 1: Primary KPI cards ──
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f"""<div class="metric-card blue-top">
            <div class="metric-label">Total CCU (Tracked)</div>
            <div class="metric-value">{total_ccu:,}</div>
            <div class="metric-sub">Across {len(ccu_data)} shooter titles</div>
            </div>""", unsafe_allow_html=True)
        with k2:
            wow_color = "var(--pos)" if wow_up >= wow_down else "var(--neg)"
            wow_sub   = f"of {wow_total} titles with CSV data" if wow_total else "No CSV data loaded"
            st.markdown(f"""<div class="metric-card pos-top">
            <div class="metric-label">WoW Growth Balance</div>
            <div class="metric-value" style="color:{wow_color}">{wow_up}↑ / {wow_down}↓</div>
            <div class="metric-sub">{wow_sub}</div>
            </div>""", unsafe_allow_html=True)
        with k3:
            yoy_color = "var(--pos)" if growing >= declining else "var(--neg)"
            st.markdown(f"""<div class="metric-card amber-top">
            <div class="metric-label">YoY Growth Balance</div>
            <div class="metric-value" style="color:{yoy_color}">{growing}↑ / {declining}↓</div>
            <div class="metric-sub">of {len(yoy_titled)} titles with YoY data</div>
            </div>""", unsafe_allow_html=True)
        with k4:
            mom_color = "var(--pos)" if mom_up >= mom_down else "var(--neg)"
            mom_sub   = f"of {mom_total} titles with CSV data" if mom_total else "No CSV data loaded"
            st.markdown(f"""<div class="metric-card purple-top">
            <div class="metric-label">MoM Growth Balance</div>
            <div class="metric-value" style="color:{mom_color}">{mom_up}↑ / {mom_down}↓</div>
            <div class="metric-sub">{mom_sub}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Row 2: CSV-derived stat cards ──
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.markdown(f"""<div class="metric-card blue-top">
            <div class="metric-label">SteamDB CSVs Loaded</div>
            <div class="metric-value">{hist_count}/{len(ccu_data)}</div>
            <div class="metric-sub">titles with full historical data</div>
            </div>""", unsafe_allow_html=True)
        with s2:
            health_color = "var(--pos)" if avg_health > 50 else "var(--amber)" if avg_health > 25 else "var(--neg)"
            st.markdown(f"""<div class="metric-card amber-top">
            <div class="metric-label">Avg Peak Health</div>
            <div class="metric-value" style="color:{health_color}">{avg_health:.0f}%</div>
            <div class="metric-sub">current CCU vs. all-time peak</div>
            </div>""", unsafe_allow_html=True)
        with s3:
            bm_pct = f"+{best_mover[1]:.1f}%" if best_mover[1] >= 0 else f"{best_mover[1]:.1f}%"
            st.markdown(f"""<div class="metric-card pos-top">
            <div class="metric-label">Biggest YoY Grower</div>
            <div class="metric-value" style="font-size:1rem;color:var(--pos)">{best_mover[0][:18]}</div>
            <div class="metric-sub">{bm_pct} YoY (SteamDB)</div>
            </div>""", unsafe_allow_html=True)
        with s4:
            wm_pct = f"{worst_mover[1]:.1f}%"
            st.markdown(f"""<div class="metric-card purple-top">
            <div class="metric-label">Biggest YoY Decline</div>
            <div class="metric-value" style="font-size:1rem;color:var(--neg)">{worst_mover[0][:18]}</div>
            <div class="metric-sub">{wm_pct} YoY (SteamDB)</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── YoY breakdown expander ──
        with st.expander(f"YoY Growth Breakdown — {growing} growing, {declining} declining"):
            if yoy_titled:
                yoy_sorted = sorted(yoy_titled, key=lambda x: x[1], reverse=True)
                yoy_df = pd.DataFrame([{
                    "Title":      name,
                    "YoY Change": pct_str,
                    "Direction":  "↑ Growing" if val > 0 else ("↓ Declining" if val < 0 else "→ Flat"),
                    "Source":     "SteamDB CSV" if has_hist else "SteamSpy proxy",
                    "Value":      val,
                } for name, val, pct_str, has_hist in yoy_sorted])
                yoy_colors = ["#20c65a" if v > 0 else "#ff3d52" for v in yoy_df["Value"]]
                fig_yoy = go.Figure(go.Bar(
                    x=yoy_df["Title"], y=yoy_df["Value"],
                    marker_color=yoy_colors,
                    text=yoy_df["YoY Change"],
                    textposition="outside",
                    textfont=dict(size=10, color="#b8bcd4"),
                    hovertemplate="<b>%{x}</b><br>YoY: %{text}<extra></extra>",
                ))
                fig_yoy.add_hline(y=0, line_color="#5a5f82", line_width=1)
                fig_yoy.update_layout(
                    **PLOTLY_BASE,
                    title=dict(text="Year-over-Year CCU Change by Title", font=dict(size=13, color="#b8bcd4"), x=0),
                    xaxis=dict(showgrid=False, tickangle=-30, tickfont=dict(size=10)),
                    yaxis=dict(showgrid=True, gridcolor="#1a1e30", ticksuffix="%"),
                    height=300, showlegend=False,
                )
                st.plotly_chart(fig_yoy, use_container_width=True)
                st.dataframe(yoy_df[["Title","Direction","YoY Change","Source"]], use_container_width=True, hide_index=True)
                st.caption("SteamDB CSV = genuine same-month YoY · SteamSpy proxy = engagement momentum estimate")
            else:
                st.info("No YoY data available — fetch CCU data first.")

        # ── Week-over-Week diff expander ──
        n_wow = sum(1 for r in ccu_data if r["app_id"] in wow_diff)
        with st.expander(f"Week-over-Week CCU Change ({n_wow} titles with CSV data)"):
            if wow_diff:
                wow_rows = []
                for r in sorted(ccu_data, key=lambda x: abs(wow_diff.get(x["app_id"], {}).get("delta", 0)), reverse=True):
                    diff = wow_diff.get(r["app_id"])
                    if diff:
                        wow_rows.append({
                            "Title":       r["name"],
                            "Current CCU": f"{r['ccu']:,}",
                            "7d Ago CCU":  f"{diff['prev_ccu']:,}",
                            "Δ CCU":       diff["delta"],
                            "Δ %":         f"{diff['delta_pct']:+.1f}%",
                            "Direction":   "Up" if diff["delta"] > 0 else "Down" if diff["delta"] < 0 else "Flat",
                            "Reference":   diff["period_label"],
                        })
                if wow_rows:
                    wow_df = pd.DataFrame(wow_rows)
                    st.dataframe(wow_df, use_container_width=True, hide_index=True)
                    st.caption("Comparing latest CSV value vs. the row closest to exactly 7 days prior. Source: SteamDB 10-minute interval data.")
            else:
                st.info("No CSV data loaded yet. Add steamdb_chart_{appid}.csv files to the /data folder.")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── CCU Bar Chart ──
        top10  = ccu_data[:10]
        colors = ["#4080ff" if not r["f2p"] else "#20c65a" for r in top10]

        # Add WoW delta to hover (from raw CSV 7-day diff)
        hover_texts = []
        for r in top10:
            diff    = wow_diff.get(r["app_id"])
            wow_str = f"<br>WoW: {diff['delta_pct']:+.1f}% ({diff['period_label']})" if diff else ""
            hover_texts.append(f"<b>{r['name']}</b><br>CCU: {r['ccu']:,}<br>YoY: {r.get('yoy','N/A')}{wow_str}<extra></extra>")

        fig = go.Figure(go.Bar(
            x=[r["name"] for r in top10],
            y=[r["ccu"] for r in top10],
            marker_color=colors,
            text=[f"{r['ccu']:,}" for r in top10],
            textposition="outside",
            textfont=dict(size=10, color="#b8bcd4"),
            hovertemplate=hover_texts,
        ))
        fig.update_layout(
            **PLOTLY_BASE,
            title=dict(text="Top 10 Shooters by Live CCU", font=dict(size=13, color="#b8bcd4"), x=0),
            xaxis=dict(showgrid=False, tickfont=dict(size=10), tickangle=-30,
                       linecolor="#232640", tickcolor="#232640"),
            yaxis=dict(showgrid=True, gridcolor="#1a1e30", tickformat=","),
            height=340, showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Paid titles (blue) / F2P titles (green)  |  Hover bars for YoY & Week-over-Week delta  |  Source: Steam public API")

        # ── Drill-down buttons row ──
        dd_col, dd_btn_col = st.columns([4, 1])
        with dd_col:
            drill_options = ["Select a title to deep dive..."] + [r["name"] for r in ccu_data]
            drill_choice  = st.selectbox("Deep Dive", drill_options, label_visibility="collapsed", key="drill_select")
        with dd_btn_col:
            if st.button("Deep Dive", key="drill_go", use_container_width=True,
                         disabled=drill_choice == "Select a title to deep dive..."):
                selected = next(r for r in ccu_data if r["name"] == drill_choice)
                st.session_state.drilldown_game   = selected["app_id"]
                st.session_state.drilldown_report  = ""
                st.session_state.active_view       = "drilldown"
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Genre Heat Map ──
        with st.expander("Sub-Genre CCU Heat Map"):
            genre_df = compute_genre_share(ccu_data)
            if not genre_df.empty:
                fig_g = go.Figure(go.Bar(
                    x=genre_df["Sub-genre"],
                    y=genre_df["Total CCU"],
                    marker_color="#4080ff",
                    text=[f"{v:.1f}%" for v in genre_df["Share %"]],
                    textposition="outside",
                    textfont=dict(size=10, color="#b8bcd4"),
                    hovertemplate="<b>%{x}</b><br>CCU: %{y:,}<br>Share: %{text}<extra></extra>",
                ))
                fig_g.update_layout(
                    **PLOTLY_BASE,
                    title=dict(text="CCU by Sub-Genre (% market share)", font=dict(size=13, color="#b8bcd4"), x=0),
                    xaxis=dict(showgrid=False, tickangle=-20, tickfont=dict(size=10)),
                    yaxis=dict(showgrid=True, gridcolor="#1a1e30", tickformat=","),
                    height=300, showlegend=False,
                )
                st.plotly_chart(fig_g, use_container_width=True)
                st.dataframe(genre_df.style.format({"Total CCU": "{:,}", "Share %": "{:.1f}%"}),
                             use_container_width=True, hide_index=True)
                st.caption("Source: Aggregated from Steam API live CCU, grouped by sub-genre tag in roster.")

        # ── Full Data Table ──
        with st.expander("Full Data Table — All Tracked Titles"):
            df = pd.DataFrame([{
                "Title":       r["name"],
                "Sub-genre":   r["sub"],
                "Publisher":   r["publisher"],
                "F2P":         "Yes" if r["f2p"] else "No",
                "Live CCU":    f"{r['ccu']:,} *" if r.get("ccu_from_csv") else r["ccu"],
                "YoY":         r.get("yoy", "N/A"),
                "Data Source": "SteamDB CSV" if r.get("has_hist") else "SteamSpy proxy",
                "Peak Ever":   f"{r['hist_summary']['peak_ever']:,}" if r.get("hist_summary",{}).get("peak_ever") else "—",
                "Peak 12m":    f"{r['hist_summary']['peak_12m']:,}"  if r.get("hist_summary",{}).get("peak_12m")  else "—",
                "Avg CCU 12m": f"{r['hist_summary']['avg_12m']:,}"   if r.get("hist_summary",{}).get("avg_12m")   else "—",
                "MoM":         r.get("hist_summary",{}).get("mom_trend","—"),
                "Review":      f"{r['review_pct']}%" if r.get("review_pct") else "—",
                "Est. Owners": r.get("owners","—"),
            } for r in ccu_data])
            st.dataframe(df, use_container_width=True, hide_index=True)
            hist_count2 = sum(1 for r in ccu_data if r.get("has_hist"))
            st.caption(
                f"{hist_count2}/{len(ccu_data)} titles have SteamDB CSV data. "
                "YoY = real same-month comparison (CSV) or SteamSpy proxy. "
                "Sources: SteamDB CSV, Steam API, SteamSpy."
            )

        # ── CSV Deep Stats ──
        csv_games = [r for r in ccu_data if r.get("has_hist")]
        if csv_games:
            with st.expander(f"SteamDB CSV Deep Stats — {len(csv_games)} titles"):
                historical2 = load_all_historical()
                deep_rows   = []
                for r in csv_games:
                    mdf2 = historical2.get(r["app_id"])
                    if mdf2 is None or mdf2.empty:
                        continue
                    hs2       = r.get("hist_summary", {})
                    peak_ever = hs2.get("peak_ever", 0) or 0
                    live_ccu  = r["ccu"]
                    peak_health = f"{live_ccu/peak_ever*100:.1f}%" if peak_ever else "—"
                    last_12   = mdf2.tail(12)["peak_ccu"].dropna()
                    volatility = f"{last_12.std()/last_12.mean()*100:.1f}%" if len(last_12) > 2 and last_12.mean() > 0 else "—"
                    best_month_row = mdf2.loc[mdf2["peak_ccu"].idxmax()] if not mdf2["peak_ccu"].isna().all() else None
                    best_month = str(best_month_row["month"]) if best_month_row is not None else "—"
                    span = f"{str(mdf2.iloc[0]['month'])} → {str(mdf2.iloc[-1]['month'])}" if len(mdf2) > 0 else "—"
                    deep_rows.append({
                        "Title":          r["name"],
                        "Data Span":      span,
                        "Months":         hs2.get("months_data", 0),
                        "All-Time Peak":  f"{peak_ever:,}" if peak_ever else "—",
                        "Best Month":     best_month,
                        "Peak 12m":       f"{hs2.get('peak_12m',0):,}" if hs2.get("peak_12m") else "—",
                        "Avg CCU 12m":    f"{hs2.get('avg_12m',0):,}"  if hs2.get("avg_12m")  else "—",
                        "Peak Health":    peak_health,
                        "Volatility":     volatility,
                        "YoY":            r.get("yoy","N/A"),
                        "MoM":            hs2.get("mom_trend","—"),
                    })
                if deep_rows:
                    st.dataframe(pd.DataFrame(deep_rows), use_container_width=True, hide_index=True)
                    st.caption(
                        "Peak Health = live CCU ÷ all-time peak. "
                        "Volatility = coefficient of variation of monthly peaks (lower = more stable). "
                        "Source: SteamDB 10-min interval CSVs."
                    )

        # ── Historical trend chart with annotations ──
        hist_titles2 = [r for r in ccu_data if r.get("has_hist")]
        if hist_titles2:
            historical3 = load_all_historical()
            with st.expander("Monthly Peak CCU History — SteamDB Data"):
                # Range selector
                range_opt = st.radio("Time range", ["12m", "24m", "All"], horizontal=True, key="hist_range")
                n_months  = 12 if range_opt == "12m" else 24 if range_opt == "24m" else 9999

                fig2 = go.Figure()
                for r in hist_titles2:
                    mdf3 = historical3.get(r["app_id"])
                    if mdf3 is not None and not mdf3.empty:
                        sub_df = mdf3.tail(n_months)
                        fig2.add_trace(go.Scatter(
                            x=[str(p) for p in sub_df["month"]],
                            y=sub_df["peak_ccu"],
                            mode="lines",
                            name=r["name"],
                            hovertemplate=f"<b>{r['name']}</b><br>%{{x}}<br>Peak: %{{y:,}}<extra></extra>",
                            line=dict(width=2),
                        ))
                        # Add annotations for this game
                        for ann in ANNOTATIONS.get(r["app_id"], []):
                            row_ann = mdf3[mdf3["month"] == ann["month"]]
                            if not row_ann.empty:
                                y_ann = row_ann.iloc[0]["peak_ccu"]
                                fig2.add_annotation(
                                    x=ann["month"], y=y_ann,
                                    text=ann["label"],
                                    showarrow=True, arrowhead=2, arrowcolor="#ffb938",
                                    font=dict(size=8, color="#ffb938"),
                                    bgcolor="rgba(15,17,32,0.85)",
                                    bordercolor="#ffb938", borderwidth=1,
                                    ay=-30,
                                )
                fig2.update_layout(
                    **PLOTLY_BASE,
                    title=dict(text=f"Monthly Peak CCU — {range_opt} (SteamDB)",
                               font=dict(size=13, color="#b8bcd4"), x=0),
                    xaxis=dict(showgrid=False, tickangle=-45, tickfont=dict(size=9)),
                    yaxis=dict(showgrid=True, gridcolor="#1a1e30", tickformat=","),
                    height=420,
                    legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
                )
                st.plotly_chart(fig2, use_container_width=True)
                st.caption("Source: SteamDB 10-min interval CSVs, aggregated to monthly peak. Annotations mark key events.")

        if st.button("Refresh CCU Data", key="refresh_ccu"):
            st.cache_data.clear()
            st.session_state.ccu_data      = []
            st.session_state.ccu_fetched_at = None
            st.rerun()

    # ─────────────────────────────────────────────────────────
    # AI ANALYSIS ENGINE
    # ─────────────────────────────────────────────────────────

    if st.session_state.active_query:
        st.markdown(f"""
        <div class="section-header">
          <span class="dot"></span>AI ANALYSIS — {st.session_state.report_label.upper()}
        </div>
        """, unsafe_allow_html=True)

        if not st.session_state.claude_key:
            st.warning("CLAUDE_KEY not found. Add it to .streamlit/secrets.toml to run AI analysis.")
        elif not ANTHROPIC_AVAILABLE:
            st.error("Install the `anthropic` package: `pip install anthropic`")
        else:
            ccu_data    = st.session_state.ccu_data or []
            aq          = st.session_state.active_query
            cache_key   = f"{aq}_{data_hash(ccu_data)}" if ccu_data else aq

            # Check cache
            cached = st.session_state.report_cache.get(cache_key)
            if cached and not st.session_state.ai_report:
                st.session_state.ai_report = cached
                st.info("Loaded from cache — data unchanged since last run. Re-fetch CCU to force refresh.")

            if not st.session_state.ai_report:
                if aq == "ccu_mecha":
                    if not ccu_data:
                        st.warning("Please fetch live CCU data first.")
                        st.stop()
                    user_prompt = build_ccu_mecha_prompt(ccu_data[:10])
                elif aq == "table_stakes":
                    user_prompt = build_table_stakes_prompt()
                elif aq == "social_metrics":
                    user_prompt = build_social_metrics_prompt()
                elif aq == "weekly_report":
                    if not ccu_data:
                        st.warning("Please fetch live CCU data first.")
                        st.stop()
                    user_prompt = build_weekly_report_prompt(ccu_data[:20])
                else:
                    user_prompt = st.session_state.custom_query

                with st.spinner("Claude is generating your analysis…"):
                    ph        = st.empty()
                    report_text = ""
                    try:
                        client = _anthropic.Anthropic(api_key=st.session_state.claude_key)
                        with client.messages.stream(
                            model="claude-sonnet-4-20250514",
                            max_tokens=4096,
                            system=build_system_prompt(),
                            messages=[{"role": "user", "content": user_prompt}],
                        ) as stream:
                            for delta in stream.text_stream:
                                report_text += delta
                                ph.markdown(report_text + "▌")
                        ph.markdown(report_text)
                        st.session_state.ai_report = report_text
                        st.session_state.report_cache[cache_key] = report_text
                    except _anthropic.AuthenticationError:
                        st.error("Invalid API key. Check CLAUDE_KEY in .streamlit/secrets.toml.")
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
                slug  = re.sub(r"[^a-z0-9]+", "_", st.session_state.report_label.lower())[:40]
                fname = f"sega_shooter_intel_{slug}"

                dl1, dl2, dl3, dl4 = st.columns(4)
                with dl1:
                    st.download_button("Download Markdown", data=st.session_state.ai_report,
                        file_name=f"{fname}.md", mime="text/markdown",
                        use_container_width=True, key="dl_md")
                with dl2:
                    html_bytes = report_to_html(st.session_state.ai_report).encode("utf-8")
                    st.download_button("Download HTML", data=html_bytes,
                        file_name=f"{fname}.html", mime="text/html",
                        use_container_width=True, key="dl_html")
                with dl3:
                    if _REPORTLAB_AVAILABLE:
                        pdf_bytes = report_to_pdf(st.session_state.ai_report)
                        if pdf_bytes:
                            st.download_button("Download PDF", data=pdf_bytes,
                                file_name=f"{fname}.pdf", mime="application/pdf",
                                use_container_width=True, key="dl_pdf")
                    else:
                        st.caption("PDF: install `reportlab`")
                with dl4:
                    if st.button("Download PowerPoint", key="dl_pptx", use_container_width=True):
                        with st.spinner("Building slides…"):
                            pptx_bytes = generate_pptx_bytes(
                                st.session_state.ai_report,
                                st.session_state.ccu_data or [],
                                st.session_state.report_label,
                            )
                        if pptx_bytes:
                            st.download_button("Download .pptx", data=pptx_bytes,
                                file_name=f"{fname}.pptx",
                                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                key="dl_pptx_actual")
                        else:
                            st.error("PPTX generation failed — ensure Node.js is installed (`node --version`).")

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
                        "Cite sources for any external facts or benchmarks you introduce. "
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
                            ph2   = st.empty()
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
  <div class="footer-note">Steam API · SteamDB CSVs · SteamSpy · Powered by Claude · Internal analytics use only</div>
</div>
""", unsafe_allow_html=True)