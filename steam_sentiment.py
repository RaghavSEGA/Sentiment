"""
Steam Genre Review Analyzer — SEGA-branded Streamlit App
=========================================================
Run with:  streamlit run steam_review_app.py

Required:  pip install streamlit requests pandas plotly anthropic matplotlib wordcloud httpx
"""

import time
import re
import os
import json
from collections import Counter
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import io
import json as _json

try:
    from wordcloud import WordCloud as _WC
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    WORDCLOUD_AVAILABLE = True
except ImportError:
    WORDCLOUD_AVAILABLE = False

try:
    import anthropic as _anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer as _VaderAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="SEGA Steam Lens",
    page_icon=":material/sports_esports:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# SEGA BRAND STYLES
# Colors from SEGA.com style guide:
#   Primary:   #0057FF (blue), #FFFFFF, #000000, #C3C5D5, #002266
#   Secondary: #15161E, #F4F6F9, #0D1126, #E1EAFF, #0044FF, #050818
# Typography: Inter Tight ExtraBold (headings), Poppins (body)
# ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;700;800;900&family=Poppins:wght@300;400;500;600&display=swap');

/* ═══════════════════════════════════════════════════════
   LOCK TO DARK THEME — defeats Streamlit light mode
   ═══════════════════════════════════════════════════════ */
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
}

/* ── Global reset: force every pixel dark ── */
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

/* Typography */
*, *::before, *::after {
    font-family: 'Poppins', sans-serif;
    box-sizing: border-box;
}

/* Force text colour on every Streamlit text node */
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
[class*="css"] {
    color: var(--text) !important;
}

/* Captions */
.stCaption, [data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {
    color: var(--muted) !important;
}

/* code blocks */
code { background: var(--surface3) !important; color: var(--blue) !important; padding: 0.1em 0.4em; border-radius: 3px; }

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 2.5rem 4rem !important; max-width: 1440px !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-hi); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--muted); }

/* ══════════════════════════════════
   TOP NAV
══════════════════════════════════ */
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
.topbar-logo {
    font-family: 'Inter Tight', sans-serif;
    font-size: 0.95rem;
    font-weight: 900;
    color: var(--text) !important;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}
.topbar-logo .seg { color: var(--blue); }
.topbar-divider { width: 1px; height: 18px; background: var(--border-hi); flex-shrink: 0; }
.topbar-label {
    font-size: 0.6rem;
    font-weight: 600;
    color: var(--muted) !important;
    letter-spacing: 0.2em;
    text-transform: uppercase;
}
.topbar-pill {
    margin-left: auto;
    background: var(--blue-glow);
    border: 1px solid rgba(64,128,255,0.28);
    border-radius: 20px;
    padding: 0.18rem 0.7rem;
    font-size: 0.58rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--blue) !important;
}

/* ══════════════════════════════════
   HERO
══════════════════════════════════ */
.hero { padding: 1.5rem 0 0.75rem; }
.hero-title {
    font-family: 'Inter Tight', sans-serif;
    font-size: 2.4rem;
    font-weight: 900;
    line-height: 1.05;
    color: var(--text) !important;
    letter-spacing: -0.03em;
    margin-bottom: 0.5rem;
}
.hero-title .accent {
    color: var(--blue);
    position: relative;
}
.hero-sub {
    font-size: 0.87rem;
    font-weight: 300;
    color: var(--muted) !important;
    max-width: 520px;
    line-height: 1.65;
}

/* ══════════════════════════════════
   SEARCH BLOCK
══════════════════════════════════ */
.search-block {
    background: var(--surface);
    border: 1px solid var(--border);
    border-top: 2px solid var(--blue);
    border-radius: 0 0 10px 10px;
    padding: 1.4rem 1.75rem 1.25rem;
    margin: 1.25rem 0 0;
}
.field-label {
    font-size: 0.58rem;
    font-weight: 700;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--muted) !important;
    margin-bottom: 0.3rem;
}

/* ══════════════════════════════════
   FORM CONTROLS
══════════════════════════════════ */
/* Text + number inputs */
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background: var(--bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    color: var(--text) !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.88rem !important;
    caret-color: var(--blue) !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 3px var(--blue-glow) !important;
}
input::placeholder { color: var(--muted) !important; opacity: 0.6 !important; }

/* Number input +/− buttons */
.stNumberInput button {
    background: var(--surface2) !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
}

/* Selectbox */
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
div[data-baseweb="menu"] [role="option"] {
    color: var(--text) !important;
    background: transparent !important;
}
div[data-baseweb="menu"] li:hover,
div[data-baseweb="menu"] [aria-selected="true"] {
    background: var(--surface3) !important;
    color: var(--text) !important;
}

/* Checkbox */
.stCheckbox > label,
.stCheckbox > label > span,
.stCheckbox label p,
[data-testid="stCheckbox"] span,
[data-testid="stCheckbox"] p {
    color: var(--text) !important;
    font-size: 0.84rem !important;
}

/* ══════════════════════════════════
   BUTTONS
══════════════════════════════════ */
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

/* ══════════════════════════════════
   KPI METRIC CARDS
══════════════════════════════════ */
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
.metric-card.blue-top { border-top: 2px solid var(--blue); }
.metric-card.pos-top  { border-top: 2px solid var(--pos);  }
.metric-card:hover { border-color: var(--border-hi); box-shadow: 0 4px 24px rgba(0,0,0,0.3); }
.metric-label {
    font-size: 0.58rem;
    font-weight: 700;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--muted) !important;
    margin-bottom: 0.45rem;
}
.metric-value {
    font-family: 'Inter Tight', sans-serif;
    font-size: 2.1rem;
    font-weight: 900;
    color: var(--text) !important;
    line-height: 1;
    margin-bottom: 0.25rem;
    letter-spacing: -0.025em;
}
.metric-sub { font-size: 0.69rem; color: var(--muted) !important; font-weight: 300; }

/* ══════════════════════════════════
   SECTION HEADER
══════════════════════════════════ */
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
.section-header .dot {
    width: 5px; height: 5px;
    background: var(--blue);
    border-radius: 1px;
    display: inline-block;
    flex-shrink: 0;
    box-shadow: 0 0 5px var(--blue);
}

/* ══════════════════════════════════
   PROGRESS BARS
══════════════════════════════════ */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, var(--blue) 0%, #7ab0ff 100%) !important;
    border-radius: 4px !important;
}

/* ══════════════════════════════════
   TABS
══════════════════════════════════ */
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
.stTabs [aria-selected="true"] {
    color: var(--text) !important;
    border-bottom-color: var(--blue) !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 0.5rem !important; }

/* ══════════════════════════════════
   EXPANDERS
══════════════════════════════════ */
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
[data-testid="stExpander"] summary div {
    color: var(--text) !important;
    background: var(--surface) !important;
}
[data-testid="stExpanderDetails"],
[data-testid="stExpanderDetails"] > div {
    background: var(--surface) !important;
    color: var(--text) !important;
}

/* ══════════════════════════════════
   DATA TABLE
══════════════════════════════════ */
[data-testid="stDataFrame"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    overflow: hidden;
}
[data-testid="stDataFrame"] iframe { background: var(--surface) !important; color: var(--text) !important; }

/* ══════════════════════════════════
   ALERTS (info / success / error / warning)
══════════════════════════════════ */
[data-testid="stAlert"],
div[data-baseweb="notification"] {
    background: var(--surface2) !important;
    border: 1px solid var(--border-hi) !important;
    border-radius: 6px !important;
    color: var(--text) !important;
}
[data-testid="stAlert"] p,
[data-testid="stAlert"] span { color: var(--text) !important; }

/* ══════════════════════════════════
   SPINNER
══════════════════════════════════ */
[data-testid="stSpinner"] p { color: var(--text) !important; }

/* ══════════════════════════════════
   REVIEW CARDS  (legacy class — used in keyword tab)
══════════════════════════════════ */
.review-card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-left: 3px solid var(--blue);
    border-radius: 0 6px 6px 0;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.75rem;
    font-size: 0.84rem;
    line-height: 1.65;
    color: var(--text);
}
.review-card.negative { border-left-color: var(--neg); }
.review-meta { font-size: 0.67rem; color: var(--muted); margin-top: 0.4rem; font-weight: 500; }

/* ══════════════════════════════════
   EMPTY STATE
══════════════════════════════════ */
.empty-state {
    margin-top: 3.5rem;
    text-align: center;
    padding: 4rem 2rem;
    border: 1px dashed var(--border-hi);
    border-radius: 12px;
    background: radial-gradient(ellipse at 50% 0%, rgba(64,128,255,0.05) 0%, transparent 65%);
}
.empty-title {
    font-family: 'Inter Tight', sans-serif;
    font-size: 2rem;
    font-weight: 900;
    color: var(--border-hi) !important;
    letter-spacing: -0.02em;
    margin-bottom: 0.7rem;
}
.empty-sub {
    font-size: 0.86rem;
    color: var(--muted) !important;
    max-width: 340px;
    margin: 0 auto;
    line-height: 1.75;
}

/* ══════════════════════════════════
   FOOTER
══════════════════════════════════ */
.footer {
    margin-top: 4rem;
    padding-top: 1.25rem;
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.footer-brand {
    font-family: 'Inter Tight', sans-serif;
    font-weight: 900;
    font-size: 0.7rem;
    color: var(--border-hi) !important;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}
.footer-note { font-size: 0.63rem; color: var(--muted) !important; }
</style>
""", unsafe_allow_html=True)
# ─────────────────────────────────────────────────────────────

STEAM_SEARCH_URL = "https://store.steampowered.com/search/results"
STEAM_REVIEW_URL = "https://store.steampowered.com/appreviews/{app_id}"

PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Poppins, sans-serif", color="#eef0fa"),
    margin=dict(l=10, r=10, t=30, b=10),
)

# ─────────────────────────────────────────────────────────────
# STEAM API HELPERS
# ─────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────
# CURATED GENRE LISTS  (verified Steam App IDs)
# Steam's search endpoints do title/keyword matching, not genre
# filtering. Curated lists guarantee correct, high-quality results.
# ─────────────────────────────────────────────────────────────

CURATED_GENRES: dict[str, list[dict]] = {
    "fighting": [
        {"app_id": 1364780, "name": "Street Fighter 6"},
        {"app_id": 1778820, "name": "Tekken 8"},
        {"app_id": 1971870, "name": "Mortal Kombat 1"},
        {"app_id": 1384160, "name": "Guilty Gear Strive"},
        {"app_id": 678950,  "name": "Dragon Ball FighterZ"},
        {"app_id": 2157560, "name": "Granblue Fantasy Versus: Rising"},
        {"app_id": 1498570, "name": "The King of Fighters XV"},
        {"app_id": 544750,  "name": "SoulCalibur VI"},
        {"app_id": 586140,  "name": "BlazBlue: Central Fiction"},
        {"app_id": 2076010, "name": "Under Night In-Birth II Sys:Celes"},
        {"app_id": 1372280, "name": "Melty Blood: Type Lumina"},
        {"app_id": 245170,  "name": "Skullgirls 2nd Encore"},
        {"app_id": 627270,  "name": "Injustice 2"},
        {"app_id": 310950,  "name": "Street Fighter V"},
        {"app_id": 389730,  "name": "Tekken 7"},
        {"app_id": 838380,  "name": "Dead or Alive 6"},
        {"app_id": 1110100, "name": "Power Rangers: Battle for the Grid"},
        {"app_id": 383980,  "name": "Rivals of Aether"},
        {"app_id": 390560,  "name": "Fantasy Strike"},
        {"app_id": 1555150, "name": "Pocket Bravery"},
    ],
    "soulslike": [
        {"app_id": 1245620, "name": "Elden Ring"},
        {"app_id": 814380,  "name": "Sekiro: Shadows Die Twice"},
        {"app_id": 374320,  "name": "Dark Souls III"},
        {"app_id": 570940,  "name": "Dark Souls: Remastered"},
        {"app_id": 335300,  "name": "Dark Souls II: Scholar of the First Sin"},
        {"app_id": 2370650, "name": "Lies of P"},
        {"app_id": 836570,  "name": "Remnant: From the Ashes"},
        {"app_id": 2161700, "name": "Remnant II"},
        {"app_id": 1163020, "name": "Mortal Shell"},
        {"app_id": 367520,  "name": "Hollow Knight"},
        {"app_id": 1120030, "name": "Nioh 2 – The Complete Edition"},
        {"app_id": 485510,  "name": "Nioh: Complete Edition"},
        {"app_id": 1461450, "name": "Salt and Sacrifice"},
        {"app_id": 1282730, "name": "Eldest Souls"},
        {"app_id": 1401290, "name": "Death's Gambit: Afterlife"},
        {"app_id": 2179430, "name": "Lords of the Fallen"},
        {"app_id": 1547330, "name": "Demon's Souls Remake"},
        {"app_id": 1869150, "name": "Steelrising"},
        {"app_id": 1621290, "name": "Nine Sols"},
        {"app_id": 1850050, "name": "The Last Faith"},
    ],
    "battle royale": [
        {"app_id": 578080,  "name": "PUBG: Battlegrounds"},
        {"app_id": 1172470, "name": "Apex Legends"},
        {"app_id": 1422450, "name": "Naraka: Bladepoint"},
        {"app_id": 1222680, "name": "Fall Guys"},
        {"app_id": 1128920, "name": "Spellbreak"},
        {"app_id": 1293830, "name": "Realm Royale Reforged"},
        {"app_id": 437220,  "name": "Darwin Project"},
        {"app_id": 1262560, "name": "BattleBit Remastered"},
        {"app_id": 1840080, "name": "The Cycle: Frontier"},
        {"app_id": 1269060, "name": "Super People"},
    ],
    "metroidvania": [
        {"app_id": 367520,  "name": "Hollow Knight"},
        {"app_id": 858300,  "name": "Ori and the Will of the Wisps"},
        {"app_id": 261570,  "name": "Ori and the Blind Forest"},
        {"app_id": 1233840, "name": "Blasphemous 2"},
        {"app_id": 774361,  "name": "Blasphemous"},
        {"app_id": 2260570, "name": "Prince of Persia: The Lost Crown"},
        {"app_id": 1029690, "name": "Bloodstained: Ritual of the Night"},
        {"app_id": 1082800, "name": "Ghost Song"},
        {"app_id": 1340030, "name": "Aeterna Noctis"},
        {"app_id": 1366540, "name": "Record of Lodoss War: Deedlit in Wonder Labyrinth"},
        {"app_id": 914730,  "name": "Astalon: Tears of the Earth"},
        {"app_id": 1145270, "name": "Carrion"},
        {"app_id": 1163660, "name": "Cathedral"},
        {"app_id": 1621290, "name": "Nine Sols"},
        {"app_id": 1401290, "name": "Death's Gambit: Afterlife"},
        {"app_id": 2284190, "name": "Pizza Tower"},
        {"app_id": 1850050, "name": "The Last Faith"},
        {"app_id": 2246460, "name": "Islets"},
        {"app_id": 1104200, "name": "Vigil: The Longest Night"},
        {"app_id": 1619010, "name": "Baba Is You"},
    ],
    "roguelike": [
        {"app_id": 1145360, "name": "Hades"},
        {"app_id": 2179850, "name": "Hades II"},
        {"app_id": 646570,  "name": "Slay the Spire"},
        {"app_id": 1942280, "name": "Vampire Survivors"},
        {"app_id": 1678690, "name": "Cult of the Lamb"},
        {"app_id": 1868140, "name": "Returnal"},
        {"app_id": 1631570, "name": "The Binding of Isaac: Repentance"},
        {"app_id": 311690,  "name": "Enter the Gungeon"},
        {"app_id": 632360,  "name": "Risk of Rain 2"},
        {"app_id": 588650,  "name": "Dead Cells"},
        {"app_id": 1307550, "name": "Loop Hero"},
        {"app_id": 2217000, "name": "Balatro"},
        {"app_id": 1079903, "name": "Noita"},
        {"app_id": 774171,  "name": "Caves of Qud"},
        {"app_id": 1194700, "name": "Dicey Dungeons"},
        {"app_id": 1770170, "name": "Dome Keeper"},
        {"app_id": 1350670, "name": "Monster Train"},
        {"app_id": 1659420, "name": "Fights in Tight Spaces"},
        {"app_id": 823230,  "name": "Void Stranger"},
        {"app_id": 1150440, "name": "Dungeon Drafters"},
    ],
    "rpg": [
        {"app_id": 1086940, "name": "Baldur's Gate 3"},
        {"app_id": 1245620, "name": "Elden Ring"},
        {"app_id": 1716740, "name": "Cyberpunk 2077"},
        {"app_id": 292030,  "name": "The Witcher 3: Wild Hunt"},
        {"app_id": 1593500, "name": "God of War"},
        {"app_id": 534380,  "name": "Divinity: Original Sin 2"},
        {"app_id": 602960,  "name": "Disco Elysium"},
        {"app_id": 1971650, "name": "Starfield"},
        {"app_id": 489830,  "name": "The Elder Scrolls V: Skyrim Special Edition"},
        {"app_id": 22380,   "name": "Fallout: New Vegas"},
        {"app_id": 377160,  "name": "Fallout 4"},
        {"app_id": 1238840, "name": "Pathfinder: Wrath of the Righteous"},
        {"app_id": 960090,  "name": "Pathfinder: Kingmaker"},
        {"app_id": 1145360, "name": "Hades"},
        {"app_id": 2138710, "name": "Hi-Fi Rush"},
        {"app_id": 1627720, "name": "Horizon Zero Dawn Complete Edition"},
        {"app_id": 2089270, "name": "Lies of P"},
        {"app_id": 2369780, "name": "Armored Core VI: Fires of Rubicon"},
        {"app_id": 1151640, "name": "FINAL FANTASY VII REMAKE INTERGRADE"},
        {"app_id": 2358720, "name": "Like a Dragon: Ishin!"},
    ],
    "platformer": [
        {"app_id": 367520,  "name": "Hollow Knight"},
        {"app_id": 858300,  "name": "Ori and the Will of the Wisps"},
        {"app_id": 261570,  "name": "Ori and the Blind Forest"},
        {"app_id": 504230,  "name": "Celeste"},
        {"app_id": 268910,  "name": "Cuphead"},
        {"app_id": 1450450, "name": "Cuphead – The Delicious Last Course"},
        {"app_id": 530610,  "name": "Sonic Mania"},
        {"app_id": 2138710, "name": "Hi-Fi Rush"},
        {"app_id": 2284190, "name": "Pizza Tower"},
        {"app_id": 1081770, "name": "Superliminal"},
        {"app_id": 1619010, "name": "Baba Is You"},
        {"app_id": 1145270, "name": "Carrion"},
        {"app_id": 1353230, "name": "Bright Memory: Infinite"},
        {"app_id": 1237320, "name": "It Takes Two"},
        {"app_id": 1426210, "name": "It Takes Two"},
        {"app_id": 2244550, "name": "Trine 5: A Clockwork Conspiracy"},
        {"app_id": 35700,   "name": "Trine 2: Complete Story"},
        {"app_id": 2018490, "name": "Kirby and the Forgotten Land"},
        {"app_id": 1378990, "name": "GRIS"},
        {"app_id": 1303950, "name": "Psychonauts 2"},
    ],
    "shooter": [
        {"app_id": 730,     "name": "Counter-Strike 2"},
        {"app_id": 1172470, "name": "Apex Legends"},
        {"app_id": 359550,  "name": "Tom Clancy's Rainbow Six Siege"},
        {"app_id": 550,     "name": "Left 4 Dead 2"},
        {"app_id": 381210,  "name": "Devil May Cry 5"},
        {"app_id": 1621690, "name": "Prodeus"},
        {"app_id": 2379780, "name": "Warhammer 40,000: Space Marine 2"},
        {"app_id": 782330,  "name": "DOOM Eternal"},
        {"app_id": 1262560, "name": "BattleBit Remastered"},
        {"app_id": 578080,  "name": "PUBG: Battlegrounds"},
        {"app_id": 1716740, "name": "Cyberpunk 2077"},
        {"app_id": 1422450, "name": "Naraka: Bladepoint"},
        {"app_id": 2369730, "name": "Armored Core VI: Fires of Rubicon"},
        {"app_id": 1086940, "name": "Deep Rock Galactic"},
        {"app_id": 548430,  "name": "Deep Rock Galactic"},
        {"app_id": 1690500, "name": "Severed Steel"},
        {"app_id": 2094270, "name": "Turbo Overkill"},
        {"app_id": 976730,  "name": "Halo: The Master Chief Collection"},
        {"app_id": 2311200, "name": "Helldivers 2"},
        {"app_id": 252490,  "name": "Rust"},
    ],
}

# Aliases: alternate spellings → canonical key
GENRE_ALIASES: dict[str, str] = {
    "fight":         "fighting",
    "fighter":       "fighting",
    "2d fighter":    "fighting",
    "3d fighter":    "fighting",
    "souls":         "soulslike",
    "souls-like":    "soulslike",
    "soulsborne":    "soulslike",
    "br":            "battle royale",
    "royale":        "battle royale",
    "rogue":         "roguelike",
    "roguelite":     "roguelike",
    "rogue-like":    "roguelike",
    "metroid":       "metroidvania",
    "vania":         "metroidvania",
    "action rpg":    "rpg",
    "jrpg":          "rpg",
    "fps":           "shooter",
    "tps":           "shooter",
    "platform":      "platformer",
    "platforming":   "platformer",
}

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://store.steampowered.com/",
}


@st.cache_data(ttl=300, show_spinner=False)
def search_games_by_genre(genre: str, max_results: int = 30) -> list[dict]:
    """
    Return a game list for the given genre.
    Curated lists take priority (guaranteed correct results).
    Falls back to Steam api/storesearch for unrecognised terms.
    """
    key = genre.lower().strip()
    key = GENRE_ALIASES.get(key, key)

    # ── Curated list hit ──
    if key in CURATED_GENRES:
        games = CURATED_GENRES[key]
        seen, unique = set(), []
        for g in games:
            if g["app_id"] not in seen:
                seen.add(g["app_id"])
                unique.append(g)
        return unique[:max_results]

    # ── Live fallback: api/storesearch ──
    games = []
    try:
        resp = requests.get(
            "https://store.steampowered.com/api/storesearch/",
            params={"term": genre, "l": "english", "cc": "US", "count": max_results},
            headers=BROWSER_HEADERS,
            timeout=12,
        )
        if resp.ok:
            for item in resp.json().get("items", []):
                aid  = item.get("id")
                name = item.get("name", "").strip()
                if aid and name:
                    games.append({"app_id": int(aid), "name": name})
    except Exception as e:
        st.warning(f"Search error: {e}")

    return games[:max_results]


def fetch_reviews_for_game(
    app_id: int, title: str, max_reviews: int, progress_cb=None,
) -> list[dict]:
    collected, cursor = [], "*"
    base = {
        "json": 1, "language": "english", "review_type": "all",
        "purchase_type": "steam", "num_per_page": 100, "filter": "recent",
    }
    while len(collected) < max_reviews:
        try:
            resp = requests.get(
                STEAM_REVIEW_URL.format(app_id=app_id),
                params={**base, "cursor": cursor}, timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            break

        if not data.get("success"):
            break
        reviews = data.get("reviews", [])
        if not reviews:
            break

        for r in reviews:
            author = r.get("author", {})
            collected.append({
                "app_id":                   app_id,
                "game_title":               title,
                "recommendation_id":        r.get("recommendationid", ""),
                "voted_up":                 r.get("voted_up"),
                "author_steamid":           author.get("steamid", ""),
                "author_num_reviews":       author.get("num_reviews", 0),
                "author_num_games_owned":   author.get("num_games_owned", 0),
                "author_playtime_hrs":      round(author.get("playtime_at_review", 0) / 60, 1),
                "author_playtime_total_hrs":round(author.get("playtime_forever", 0) / 60, 1),
                "votes_helpful":            r.get("votes_up", 0),
                "votes_funny":              r.get("votes_funny", 0),
                "timestamp_created":        r.get("timestamp_created"),
                "review_text":              r.get("review", "").strip(),
                "written_during_ea":        r.get("written_during_early_access", False),
            })
            if len(collected) >= max_reviews:
                break

        if progress_cb:
            progress_cb(min(len(collected) / max(max_reviews, 1), 1.0))

        new_cursor = data.get("cursor")
        if not new_cursor or new_cursor == cursor:
            break
        cursor = new_cursor
        time.sleep(0.6)

    return collected

# ─────────────────────────────────────────────────────────────
# SUMMARY BUILDER
# ─────────────────────────────────────────────────────────────

def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for title, grp in df.groupby("game_title"):
        pos = grp["voted_up"].sum()
        rows.append({
            "game_title":          title,
            "total_reviews":       len(grp),
            "positive_reviews":    int(pos),
            "negative_reviews":    int(len(grp) - pos),
            "positive_pct":        round(pos / len(grp) * 100, 1) if len(grp) else 0,
            "avg_playtime_hrs":    round(grp["author_playtime_hrs"].mean(), 1),
            "median_playtime_hrs": round(grp["author_playtime_hrs"].median(), 1),
            "avg_helpful_votes":   round(grp["votes_helpful"].mean(), 2),
        })
    return pd.DataFrame(rows).sort_values("positive_pct", ascending=False)

# ─────────────────────────────────────────────────────────────
# CHART HELPERS
# ─────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────
# KEYWORD EXTRACTION
# ─────────────────────────────────────────────────────────────

STOPWORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","with","is",
    "it","its","i","my","me","you","your","we","this","that","was","are","be",
    "been","have","has","had","not","so","if","as","by","from","they","them",
    "their","there","then","than","very","just","get","got","can","cant","would",
    "could","should","will","when","what","which","who","more","much","some",
    "all","one","two","also","do","did","no","yes","up","out","about","into",
    "like","really","still","even","back","way","well","only","time","after",
    "before","because","see","how","good","great","bad","game","games","play",
    "played","playing","hours","hrs","steam","review","reviews","though",
    "overall","feel","felt","make","makes","made","ve","re","ll","m","t","s",
    "d","dont","doesnt","didnt","wasnt","isnt","im","ive","id","its","thats",
    "hes","shes","were","theyre","youre","actually","pretty","bit","lot","things",
    "thing","really","too","now","since","little","every","other","same","most",
    "many","few","just","already","always","never","ever","maybe","probably",
    "actually","quite","sure","while","without","through","around","against",
    "between","own","off","over","here","where","why","something","someone",
    "nothing","everything","anything","nothing","buy","bought","worth","price",
    "free","dlc","update","patch","early","access","new","old","first","last",
    "another","second","different","better","best","worst","worse","less","far",
}

def extract_keywords(texts: list[str], top_n: int = 30) -> list[tuple[str, int]]:
    """Extract top unigrams and bigrams from a list of review texts."""
    words_all: list[str] = []
    bigrams_all: list[str] = []
    for text in texts:
        tokens = re.findall(r"[a-z]{3,}", text.lower())
        tokens = [t for t in tokens if t not in STOPWORDS]
        words_all.extend(tokens)
        bigrams_all.extend(f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens)-1))
    counter = Counter(words_all) + Counter(bigrams_all)
    return counter.most_common(top_n)


@st.cache_data(show_spinner=False)
def generate_wordcloud_img(freq_json: str, positive: bool) -> bytes:
    """
    Given a JSON-serialised {word: count} dict, produce a PNG word cloud
    and return raw bytes. Cached so re-runs don't re-render.
    """
    import json as _json
    freqs = _json.loads(freq_json)
    if not freqs:
        return b""

    bg      = "#0d0f1a"
    hi      = "#20c65a" if positive else "#ff3d52"
    lo      = "#1a4a2e" if positive else "#4a1a1a"

    def colour_fn(word, font_size, position, orientation, random_state=None, **kw):
        # Shade from bright (hi) to dim (lo) based on relative font size
        t = min(font_size / 120, 1.0)
        hi_rgb = tuple(int(hi[i:i+2], 16) for i in (1,3,5))
        lo_rgb = tuple(int(lo[i:i+2], 16) for i in (1,3,5))
        r = int(lo_rgb[0] + t*(hi_rgb[0]-lo_rgb[0]))
        g = int(lo_rgb[1] + t*(hi_rgb[1]-lo_rgb[1]))
        b = int(lo_rgb[2] + t*(hi_rgb[2]-lo_rgb[2]))
        return f"rgb({r},{g},{b})"

    wc = _WC(
        width=800, height=380,
        background_color=bg,
        max_words=60,
        font_path=None,           # uses default font
        collocations=False,
        prefer_horizontal=0.85,
        min_font_size=10,
        max_font_size=120,
        color_func=colour_fn,
        margin=6,
    ).generate_from_frequencies(freqs)

    fig, ax = plt.subplots(figsize=(8, 3.8), facecolor=bg)
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    fig.tight_layout(pad=0)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=bg, bbox_inches="tight", dpi=130)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


@st.cache_data(show_spinner=False)
def run_vader_on_df(df_json: str) -> str:
    """Run VADER on all reviews. Accepts/returns JSON for Streamlit caching."""
    import io as _io
    df = pd.read_json(_io.StringIO(df_json), orient="records")
    if VADER_AVAILABLE:
        analyzer = _VaderAnalyzer()
        scores = [analyzer.polarity_scores(t or "") for t in df["review_text"].fillna("").tolist()]
        df["vader_compound"] = [s["compound"] for s in scores]
    else:
        df["vader_compound"] = None
    return df.to_json(orient="records")


def _normalise_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Convert timestamp_created/updated from any type (int, Timestamp, str)
    to plain Python int (Unix seconds). Called once after every DataFrame load."""
    for col in ("timestamp_created", "timestamp_updated"):
        if col not in df.columns:
            continue
        def _to_int(v):
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return None
            if hasattr(v, "timestamp"):          # pd.Timestamp
                return int(v.timestamp())
            try:
                return int(v)
            except Exception:
                return None
        df[col] = df[col].apply(_to_int)
    return df


# ─────────────────────────────────────────────────────────────
# LIVE GAME LOOKUP  (for manual "add a game" feature)
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=120, show_spinner=False)
def lookup_game(query: str) -> list[dict]:
    """Search Steam for a specific game title. Returns up to 8 candidates."""
    results = []
    try:
        resp = requests.get(
            "https://store.steampowered.com/api/storesearch/",
            params={"term": query, "l": "english", "cc": "US", "count": 8},
            headers=BROWSER_HEADERS,
            timeout=10,
        )
        if resp.ok:
            for item in resp.json().get("items", []):
                aid  = item.get("id")
                name = item.get("name", "").strip()
                tiny = item.get("tiny_image", "")
                if aid and name:
                    results.append({"app_id": int(aid), "name": name, "img": tiny})
    except Exception:
        pass


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_game_events(app_id: int, game_name: str) -> list[dict]:
    """Fetch patch/DLC/update events from Steam News API for a single game.
    Returns list of {ts, date_str, title, event_type} sorted oldest→newest."""
    UPDATE_KEYWORDS = [
        "update", "patch", "hotfix", "fix", "dlc", "expansion",
        "content", "season", "version", "release", "launch",
        "major", "anniversary", "early access", "full release",
    ]
    results = []
    try:
        resp = requests.get(
            "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/",
            params={"appid": app_id, "count": 100, "maxlength": 1200, "format": "json"},
            headers=BROWSER_HEADERS,
            timeout=12,
        )
        if not resp.ok:
            return []
        items = resp.json().get("appnews", {}).get("newsitems", [])
        from datetime import datetime, timezone as _tz
        for item in items:
            title = item.get("title", "").strip()
            ts    = item.get("date")
            if not title or not ts:
                continue
            tl = title.lower()
            # Only keep items whose title contains an update/DLC keyword
            if not any(kw in tl for kw in UPDATE_KEYWORDS):
                continue
            # Skip if it looks like a sale or community announcement
            skip_words = ["sale", "discount", "contest", "giveaway", "stream", "tournament", "esport"]
            if any(sw in tl for sw in skip_words):
                continue
            dt  = datetime.fromtimestamp(int(ts), _tz.utc)
            # Categorise
            if any(k in tl for k in ["dlc", "expansion", "season pass", "content pack"]):
                etype = "DLC"
            elif any(k in tl for k in ["early access", "full release", "launch", "release"]):
                etype = "Release"
            else:
                etype = "Update"
            # Strip simple HTML tags from contents for clean display
            import re as _re2
            raw_contents = item.get("contents", "") or ""
            clean_contents = _re2.sub(r"<[^>]+>", " ", raw_contents).strip()
            clean_contents = _re2.sub(r" {2,}", " ", clean_contents)
            results.append({
                "ts":       int(ts),
                "date_str": dt.strftime("%b %d, %Y"),
                "month":    dt.strftime("%Y-%m"),
                "title":    title[:80],
                "type":     etype,
                "game":     game_name,
                "app_id":   app_id,
                "url":      item.get("url", ""),
                "contents": clean_contents[:1000],
            })
    except Exception:
        pass
    # Deduplicate by month+type to avoid noise, keep earliest per month
    seen = {}
    for ev in sorted(results, key=lambda x: x["ts"]):
        key = (ev["app_id"], ev["month"], ev["type"])
        if key not in seen:
            seen[key] = ev
    return sorted(seen.values(), key=lambda x: x["ts"])

def chart_sentiment_bar(sdf: pd.DataFrame) -> go.Figure:
    df = sdf.sort_values("positive_pct", ascending=True).tail(15)
    # Colour gradient: red → amber → blue by score
    def bar_colour(v):
        if v >= 80: return "#4080ff"
        if v >= 70: return "#2d6aee"
        if v >= 55: return "#f0a500"
        return "#ff3d52"
    colours = [bar_colour(v) for v in df["positive_pct"]]
    # Steam label overlay
    def steam_label(v):
        if v >= 95: return "Overwhelmingly Positive"
        if v >= 80: return "Very Positive"
        if v >= 70: return "Mostly Positive"
        if v >= 40: return "Mixed"
        return "Negative"
    labels = [f"  {v:.0f}%  {steam_label(v)}" for v in df["positive_pct"]]
    fig = go.Figure(go.Bar(
        y=df["game_title"], x=df["positive_pct"], orientation="h",
        marker=dict(
            color=colours,
            line=dict(color="rgba(0,0,0,0)", width=0),
        ),
        text=labels,
        textposition="outside",
        textfont=dict(size=10, color="#b8bcd4"),
        cliponaxis=False,
    ))
    # Subtle 80% reference line
    fig.add_vline(x=80, line=dict(color="rgba(64,128,255,0.2)", width=1, dash="dot"))
    fig.update_layout(
        **PLOTLY_BASE,
        xaxis=dict(range=[0, 130], showgrid=False, zeroline=False,
                   tickfont=dict(color="#5a5f82"), showticklabels=False),
        yaxis=dict(showgrid=False, tickfont=dict(color="#eef0fa", size=11),
                   ticksuffix="  "),
        height=max(320, len(df) * 42),
        bargap=0.35,
    )
    return fig


def chart_scatter(sdf: pd.DataFrame) -> go.Figure:
    # Colour by sentiment, size by review count
    fig = go.Figure(go.Scatter(
        x=sdf["avg_playtime_hrs"],
        y=sdf["positive_pct"],
        mode="markers+text",
        text=sdf["game_title"].str[:20],
        textposition="top center",
        textfont=dict(size=9, color="#6b7194"),
        marker=dict(
            size=sdf["total_reviews"].apply(lambda v: max(10, min(36, v / 6))),
            color=sdf["positive_pct"],
            colorscale=[[0, "#ff3d52"], [0.4, "#f0a500"], [0.7, "#4080ff"], [1, "#a0c8ff"]],
            showscale=True,
            colorbar=dict(
                title=dict(text="% Pos", font=dict(color="#5a5f82", size=10)),
                tickfont=dict(color="#5a5f82", size=9),
                thickness=10,
                len=0.7,
            ),
            line=dict(color="rgba(0,0,0,0.4)", width=1),
            opacity=0.9,
        ),
        hovertemplate=(
            "<b>%{text}</b><br>"
            "%{y:.1f}% positive<br>"
            "%{x:.1f} hrs avg playtime<br>"
            "<extra></extra>"
        ),
    ))
    fig.update_layout(
        **PLOTLY_BASE,
        xaxis=dict(
            title=dict(text="Avg Playtime at Review (hrs)", font=dict(color="#5a5f82", size=11)),
            showgrid=True, gridcolor="#1a1d2e", zeroline=False,
            tickfont=dict(color="#5a5f82"),
        ),
        yaxis=dict(
            title=dict(text="% Positive", font=dict(color="#5a5f82", size=11)),
            showgrid=True, gridcolor="#1a1d2e", zeroline=False,
            tickfont=dict(color="#5a5f82"), range=[0, 105],
        ),
        height=420,
    )
    return fig


def chart_review_volume(sdf: pd.DataFrame) -> go.Figure:
    """Grouped bar: positive vs negative per game, sorted by total."""
    df = sdf.sort_values("total_reviews", ascending=False).head(12)
    short = df["game_title"].str[:18]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Positive", x=short, y=df["positive_reviews"],
        marker=dict(color="#4080ff", opacity=0.9,
                    line=dict(color="rgba(0,0,0,0)", width=0)),
        hovertemplate="%{x}<br>%{y:,} positive<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Negative", x=short, y=df["negative_reviews"],
        marker=dict(color="#ff3d52", opacity=0.75,
                    line=dict(color="rgba(0,0,0,0)", width=0)),
        hovertemplate="%{x}<br>%{y:,} negative<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_BASE, barmode="group",
        xaxis=dict(tickangle=-32, tickfont=dict(color="#6b7194", size=10),
                   showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#1a1d2e",
                   tickfont=dict(color="#5a5f82")),
        legend=dict(font=dict(color="#b8bcd4", size=11),
                    bgcolor="rgba(0,0,0,0)", orientation="h",
                    yanchor="bottom", y=1.02, xanchor="right", x=1),
        bargap=0.22, bargroupgap=0.06,
        height=380,
    )
    return fig


def chart_playtime_hist(df: pd.DataFrame) -> go.Figure:
    capped = df[df["author_playtime_hrs"] <= 200]["author_playtime_hrs"]
    # Colour bins by playtime bucket
    fig = go.Figure(go.Histogram(
        x=capped, nbinsx=30,
        marker=dict(
            color=capped,
            colorscale=[[0, "#1a3acc"], [0.5, "#4080ff"], [1, "#a0c8ff"]],
            line=dict(color="#0a0c1a", width=0.3),
        ),
        hovertemplate="~%{x:.0f} hrs: %{y} reviews<extra></extra>",
    ))
    # Median line
    med = capped.median()
    fig.add_vline(
        x=med,
        line=dict(color="#f0a500", width=1.5, dash="dash"),
        annotation=dict(
            text=f"median {med:.0f}h",
            font=dict(color="#f0a500", size=10),
            yanchor="top",
        ),
    )
    fig.update_layout(
        **PLOTLY_BASE,
        xaxis=dict(
            title=dict(text="Hours at Review", font=dict(color="#5a5f82", size=11)),
            tickfont=dict(color="#5a5f82"), showgrid=False,
        ),
        yaxis=dict(
            title=dict(text="Reviews", font=dict(color="#5a5f82", size=11)),
            showgrid=True, gridcolor="#1a1d2e",
            tickfont=dict(color="#5a5f82"),
        ),
        height=340,
    )
    return fig


def chart_sentiment_timeline(df: pd.DataFrame, events: list | None = None) -> go.Figure:
    """Monthly rolling sentiment % over time, one line per game. events = list of event dicts."""
    from datetime import datetime, UTC
    _df = df.copy()
    _df["month"] = pd.to_datetime(_df["timestamp_created"].apply(
        lambda ts: datetime.fromtimestamp(int(ts), UTC).strftime("%Y-%m")
        if ts is not None and pd.notna(ts) else None
    ), errors="coerce")
    _df = _df.dropna(subset=["month"])
    if _df.empty:
        return go.Figure()

    fig = go.Figure()
    palette = ["#4080ff", "#20c65a", "#ff3d52", "#f0a500", "#a060ff",
               "#00d4ff", "#ff8c00", "#60ff9a", "#ff60a0", "#c0ff40"]
    games = sorted(_df["game_title"].unique())
    for i, game in enumerate(games):
        g = _df[_df["game_title"] == game]
        monthly = (
            g.groupby("month")
            .apply(lambda x: x["voted_up"].mean() * 100, include_groups=False)
            .reset_index()
        )
        monthly.columns = ["month", "pct_pos"]
        monthly = monthly.sort_values("month")
        if len(monthly) < 2:
            continue
        colour = palette[i % len(palette)]
        fig.add_trace(go.Scatter(
            x=monthly["month"].astype(str),
            y=monthly["pct_pos"],
            mode="lines+markers",
            name=game[:22],
            line=dict(color=colour, width=2, shape="spline", smoothing=0.6),
            marker=dict(size=5, color=colour,
                        line=dict(color="#0a0c1a", width=1)),
            hovertemplate=f"<b>{game[:30]}</b><br>%{{x}}<br>%{{y:.1f}}% positive<extra></extra>",
        ))
    # ── Event vertical lines ──────────────────────────────────
    if events:
        _type_colours = {"DLC": "#f0a500", "Update": "#a060ff", "Release": "#20c65a"}
        _drawn_labels = set()
        for ev in events:
            _col   = _type_colours.get(ev["type"], "#6b7194")
            # add_shape works on categorical x-axes without arithmetic
            fig.add_shape(
                type="line",
                x0=ev["month"], x1=ev["month"],
                y0=0, y1=1,
                xref="x", yref="paper",
                line=dict(color=_col, width=1.5, dash="dot"),
            )
            if ev["type"] not in _drawn_labels:
                fig.add_annotation(
                    x=ev["month"],
                    y=0.98,
                    xref="x", yref="paper",
                    text=f"<b>{ev['type']}</b>",
                    font=dict(color=_col, size=9),
                    bgcolor="rgba(10,12,26,0.75)",
                    bordercolor=_col,
                    borderwidth=1,
                    showarrow=False,
                    yanchor="top",
                    xanchor="left",
                )
                _drawn_labels.add(ev["type"])
    fig.add_hline(y=70, line=dict(color="rgba(64,128,255,0.18)", width=1, dash="dot"))
    fig.update_layout(
        **PLOTLY_BASE,
        xaxis=dict(
            tickangle=-38, tickfont=dict(color="#5a5f82", size=9),
            showgrid=False, title=None,
        ),
        yaxis=dict(
            title=dict(text="% Positive", font=dict(color="#5a5f82", size=11)),
            showgrid=True, gridcolor="#1a1d2e",
            tickfont=dict(color="#5a5f82"), range=[0, 105],
        ),
        legend=dict(
            font=dict(color="#b8bcd4", size=10),
            bgcolor="rgba(15,17,32,0.8)",
            bordercolor="#232640", borderwidth=1,
        ),
        height=420,
        hovermode="x unified",
    )
    return fig


# ─────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────

for key, default in [
    ("found_games",         []),
    ("selected_games",      {}),
    ("results_df",          None),
    ("summary_df",          None),
    ("last_genre",          ""),
    ("game_search_results", []),   # candidates from "add a game" lookup
    ("anthropic_api_key",    os.environ.get("ANTHROPIC_API_KEY", "")),
    ("ai_report",           ""),   # last generated report text
    ("game_events",          {}),   # {app_id: [event dicts]} fetched from Steam News
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─────────────────────────────────────────────────────────────
# TOP NAV
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="topbar">
  <div class="topbar-logo"><span class="seg">SEGA</span> STEAM LENS</div>
  <div class="topbar-divider"></div>
  <div class="topbar-label">Review Analytics Platform</div>
  <div class="topbar-pill">Beta</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
  <div class="hero-title">GENRE <span class="accent">ANALYTICS</span></div>
  <div class="hero-sub">Pull Steam reviews for any genre — explore sentiment, playtime, keywords, and AI insights in one view.</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# QUICK-START GENRE CHIPS
# ─────────────────────────────────────────────────────────────
QUICK_GENRES = [
    "soulslike", "fighting", "roguelike",
    "metroidvania", "battle royale", "rpg",
]

st.markdown("""
<style>
.chip-row { display:flex; gap:.65rem; margin:.4rem 0 1.1rem; }
.genre-chip > button {
    background: var(--surface) !important;
    color: var(--text-dim) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    font-family: 'Inter Tight', sans-serif !important;
    font-size: .78rem !important;
    font-weight: 700 !important;
    letter-spacing: .1em !important;
    text-transform: uppercase !important;
    padding: .4rem 1.1rem !important;
    min-height: unset !important;
    height: auto !important;
    line-height: 1.5 !important;
    transition: border-color .15s, color .15s, background .15s !important;
    box-shadow: none !important;
    width: 100% !important;
}
.genre-chip > button:hover {
    background: var(--surface2) !important;
    border-color: var(--blue) !important;
    color: var(--text) !important;
    transform: none !important;
    box-shadow: none !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="chip-row">', unsafe_allow_html=True)
_chip_cols = st.columns(len(QUICK_GENRES))
_chip_clicked = None
for _ci, _label in enumerate(QUICK_GENRES):
    with _chip_cols[_ci]:
        st.markdown('<div class="genre-chip">', unsafe_allow_html=True)
        if st.button(_label, key=f"chip_{_label}"):
            _chip_clicked = _label
        st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SEARCH FORM
# ─────────────────────────────────────────────────────────────

st.markdown('<div class="search-block">', unsafe_allow_html=True)
c1, c2, c3 = st.columns([3, 1.2, 1.2])
with c1:
    st.markdown('<div class="field-label">Genre / Search Term</div>', unsafe_allow_html=True)
    genre_input = st.text_input(
        "genre", label_visibility="collapsed",
        placeholder="e.g.  fighting,  soulslike,  battle royale,  metroidvania…",
        value=_chip_clicked or "",
        key="genre_text_input",
    )
with c2:
    st.markdown('<div class="field-label">Max Games</div>', unsafe_allow_html=True)
    max_games = st.selectbox("max games", [10, 20, 30], index=1, label_visibility="collapsed")
with c3:
    st.markdown('<div class="field-label">Reviews / Game</div>', unsafe_allow_html=True)
    reviews_per = st.selectbox("reviews per game", [100, 250, 500], index=0, label_visibility="collapsed")
btn_col, _ = st.columns([1, 5])
with btn_col:
    search_clicked = st.button("SEARCH GENRE", width='stretch')
st.markdown("</div>", unsafe_allow_html=True)

# If chip was clicked, auto-trigger search
if _chip_clicked:
    search_clicked = True
    genre_input = _chip_clicked

# ─────────────────────────────────────────────────────────────
# SEARCH LOGIC
# ─────────────────────────────────────────────────────────────

if search_clicked and genre_input.strip():
    with st.spinner("Searching Steam…"):
        games = search_games_by_genre(genre_input.strip(), max_games)
    if games:
        st.session_state.found_games    = games
        st.session_state.selected_games = {g["app_id"]: True for g in games}
        st.session_state.results_df     = None
        st.session_state.summary_df     = None
        st.session_state.last_genre     = genre_input.strip()
    else:
        st.warning("No games found. Try a different search term.")

# ─────────────────────────────────────────────────────────────
# ADD A SPECIFIC GAME
# ─────────────────────────────────────────────────────────────

with st.expander("Add a specific game to the list", expanded=False):
    st.markdown(
        '<div class="field-label" style="margin-bottom:.5rem;">Search for a game by name</div>',
        unsafe_allow_html=True,
    )
    ag_col, ab_col = st.columns([3, 1])
    with ag_col:
        add_query = st.text_input(
            "add_game_query", label_visibility="collapsed",
            placeholder="e.g.  Hollow Knight,  Tekken 8,  Baldur's Gate 3…",
            key="add_game_input",
        )
    with ab_col:
        add_search = st.button("FIND", width='stretch', key="btn_add_search")

    if add_search and add_query.strip():
        with st.spinner("Searching…"):
            st.session_state.game_search_results = lookup_game(add_query.strip())
        if not st.session_state.game_search_results:
            st.warning("No results found. Try a different title.")

    if st.session_state.game_search_results:
        st.markdown(
            '<div class="field-label" style="margin:.6rem 0 .4rem;">Select a game to add:</div>',
            unsafe_allow_html=True,
        )
        for candidate in st.session_state.game_search_results:
            already = any(g["app_id"] == candidate["app_id"]
                          for g in st.session_state.found_games)
            rc1, rc2 = st.columns([5, 1])
            with rc1:
                # Use tiny_image from API if present, else fall back to header capsule
                _img_src = (
                    candidate.get("img") or
                    f'https://cdn.cloudflare.steamstatic.com/steam/apps/{candidate["app_id"]}/header.jpg'
                )
                _img_html = (
                    f'<img src="{_img_src}" style="height:45px;width:80px;object-fit:cover;'
                    f'border-radius:4px;border:1px solid var(--border);flex-shrink:0;">'
                )
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:.75rem;padding:.3rem 0;">'
                    + _img_html +
                    f'<div>'
                    f'<div style="font-size:.88rem;color:var(--text);font-weight:500;">{candidate["name"]}</div>'
                    f'<div style="font-size:.7rem;color:var(--muted);margin-top:.1rem;">App ID {candidate["app_id"]}</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
            with rc2:
                if already:
                    st.markdown(
                        '<span style="font-size:.75rem;color:var(--muted);">already added</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    if st.button("Add", key=f"add_{candidate['app_id']}"):
                        st.session_state.found_games.append(
                            {"app_id": candidate["app_id"], "name": candidate["name"]}
                        )
                        st.session_state.selected_games[candidate["app_id"]] = True
                        st.session_state.results_df = None
                        st.session_state.summary_df = None

# ─────────────────────────────────────────────────────────────
# GAME SELECTION PANEL
# ─────────────────────────────────────────────────────────────

if st.session_state.found_games:
    n = len(st.session_state.found_games)
    st.markdown(
        f'<div class="section-header"><span class="dot"></span>'
        f'SELECT GAMES '
        f'<span style="color:var(--muted);font-weight:400;font-size:0.72rem;">'
        f'— {n} found</span></div>',
        unsafe_allow_html=True,
    )

    sa, ca, _ = st.columns([1.5, 1.5, 7])
    with sa:
        if st.button("Select All", width='stretch'):
            for g in st.session_state.found_games:
                st.session_state.selected_games[g["app_id"]] = True
    with ca:
        if st.button("Clear All", width='stretch'):
            for g in st.session_state.found_games:
                st.session_state.selected_games[g["app_id"]] = False

    cols = st.columns(4)
    for i, game in enumerate(st.session_state.found_games):
        with cols[i % 4]:
            val = st.checkbox(
                game["name"],
                value=st.session_state.selected_games.get(game["app_id"], True),
                key=f"chk_{game['app_id']}",
            )
            st.session_state.selected_games[game["app_id"]] = val

    selected_list = [
        g for g in st.session_state.found_games
        if st.session_state.selected_games.get(g["app_id"], False)
    ]

    if selected_list:
        st.markdown("<br>", unsafe_allow_html=True)
        fb_col, _ = st.columns([1.4, 5])
        with fb_col:
            fetch_clicked = st.button(
                f"FETCH {len(selected_list)} GAMES",
                width='stretch',
            )

        # ── FETCH LOOP ──
        if fetch_clicked:
            all_reviews = []
            st.markdown(
                '<div class="section-header"><span class="dot"></span>FETCHING REVIEWS</div>',
                unsafe_allow_html=True,
            )
            _fetch_cols = st.columns([3, 1])
            with _fetch_cols[0]:
                overall_bar = st.progress(0.0)
            with _fetch_cols[1]:
                live_counter = st.empty()
            status_box  = st.empty()
            game_bar    = st.progress(0.0)

            for idx, game in enumerate(selected_list):
                title, app_id = game["name"], game["app_id"]
                status_box.markdown(
                    f'<div style="font-size:0.83rem;color:var(--muted);padding:0.25rem 0;">'
                    f'↳ Fetching <strong style="color:var(--text);">{title}</strong>'
                    f'&nbsp;<span style="color:var(--muted);">{idx+1}/{len(selected_list)}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                game_bar.progress(0.0)
                _reviews_before = len(all_reviews)

                def _cb(pct, bar=game_bar, counter=live_counter,
                        total_so_far=all_reviews, target=reviews_per, gidx=idx):
                    bar.progress(float(pct))
                    _est = _reviews_before + int(pct * target)
                    counter.markdown(
                        f'<div style="font-size:.82rem;font-family:Inter Tight,sans-serif;'
                        f'font-weight:800;color:var(--blue);text-align:right;padding-top:.3rem;">'
                        f'{len(total_so_far) + int(pct * target):,}'
                        f'<span style="font-size:.65rem;font-weight:400;color:var(--muted);">'
                        f' reviews</span></div>',
                        unsafe_allow_html=True,
                    )

                reviews = fetch_reviews_for_game(app_id, title, reviews_per, _cb)
                all_reviews.extend(reviews)
                overall_bar.progress((idx + 1) / len(selected_list))
                live_counter.markdown(
                    f'<div style="font-size:.82rem;font-family:Inter Tight,sans-serif;'
                    f'font-weight:800;color:var(--blue);text-align:right;padding-top:.3rem;">'
                    f'{len(all_reviews):,}'
                    f'<span style="font-size:.65rem;font-weight:400;color:var(--muted);"> reviews</span></div>',
                    unsafe_allow_html=True,
                )

            status_box.markdown(
                f'<div style="font-size:0.83rem;color:#20c65a;padding:0.25rem 0;">'
                f'Fetched <strong>{len(all_reviews):,}</strong> reviews across {len(selected_list)} games</div>',
                unsafe_allow_html=True,
            )
            game_bar.empty()

            if all_reviews:
                import io as _io2
                _rdf = pd.DataFrame(all_reviews)
                _rdf = _normalise_timestamps(_rdf)
                if VADER_AVAILABLE:
                    _rdf = pd.read_json(
                        _io2.StringIO(run_vader_on_df(_rdf.to_json(orient="records"))),
                        orient="records",
                    )
                    _rdf = _normalise_timestamps(_rdf)
                st.session_state.results_df = _rdf
                st.session_state.summary_df = build_summary(st.session_state.results_df)
                # Auto-fetch Steam News events for all selected games
                _all_events = {}
                for _g in selected_list:
                    _evs = fetch_game_events(_g["app_id"], _g["name"])
                    if _evs:
                        _all_events[_g["app_id"]] = _evs
                st.session_state.game_events = _all_events
            else:
                st.error("No reviews collected. Try different games or a higher review limit.")

# ─────────────────────────────────────────────────────────────
# RESULTS DASHBOARD
# ─────────────────────────────────────────────────────────────

if st.session_state.results_df is not None and st.session_state.summary_df is not None:
    df  = st.session_state.results_df
    sdf = st.session_state.summary_df

    # ── Playtime filter ───────────────────────────────────────
    _max_hrs = int(df["author_playtime_hrs"].max()) if len(df) else 1000
    _max_hrs = max(_max_hrs, 1)
    _cap     = min(_max_hrs, 2000)   # slider cap — outliers above 2k hrs are rare

    with st.expander("Filter by playtime at review", expanded=False):
        st.markdown(
            '<div style="font-size:.78rem;color:var(--muted);margin-bottom:.75rem;">'
            'Only include reviews written by players whose playtime at the time of reviewing '
            'falls within the entered range. Useful for separating day-one impressions '
            'from long-term players.</div>',
            unsafe_allow_html=True,
        )
        pt_col1, pt_col2, pt_col3 = st.columns([1, 1, 3])
        with pt_col1:
            st.markdown('<div class="field-label">Min hours</div>', unsafe_allow_html=True)
            pt_low = st.number_input(
                "min_hrs", label_visibility="collapsed",
                min_value=0, max_value=999999,
                value=0, step=1, key="playtime_min",
            )
        with pt_col2:
            st.markdown('<div class="field-label">Max hours</div>', unsafe_allow_html=True)
            pt_high = st.number_input(
                "max_hrs", label_visibility="collapsed",
                min_value=0, max_value=999999,
                value=_cap, step=1, key="playtime_max",
            )
        n_before = len(df)
        if pt_low > pt_high:
            st.warning("Min hours must be less than or equal to max hours.")
        else:
            df = df[
                (df["author_playtime_hrs"] >= pt_low) &
                (df["author_playtime_hrs"] <= pt_high)
            ].copy()
            n_after = len(df)
            if pt_low != 0 or pt_high != _cap:
                st.markdown(
                    f'<div style="font-size:.75rem;color:var(--blue);margin-top:.4rem;">'
                    f'Showing <strong>{n_after:,}</strong> of {n_before:,} reviews'
                    f' &nbsp;·&nbsp; {pt_low}–{pt_high} hrs at review</div>',
                    unsafe_allow_html=True,
                )
                sdf = build_summary(df) if len(df) else sdf

    # ── Date range filter ─────────────────────────────────────
    from datetime import datetime, timedelta, timezone, date as _date

    # Compute the actual min/max dates present in the data
    _ts_col = df["timestamp_created"].dropna()
    if len(_ts_col):
        _ts_min = int(_ts_col.min())
        _ts_max = int(_ts_col.max())
        _data_start = datetime.fromtimestamp(_ts_min, timezone.utc).date()
        _data_end   = datetime.fromtimestamp(_ts_max, timezone.utc).date()
    else:
        _data_start = _date(2010, 1, 1)
        _data_end   = _date.today()

    _today = _date.today()

    # Initialise session state for date filter
    if "date_from" not in st.session_state:
        st.session_state.date_from = _data_start
    if "date_to" not in st.session_state:
        st.session_state.date_to = _data_end

    # Clamp stored values to actual data range on new dataset load
    _stored_from = st.session_state.date_from
    _stored_to   = st.session_state.date_to
    if _stored_from < _data_start or _stored_from > _data_end:
        st.session_state.date_from = _data_start
    if _stored_to < _data_start or _stored_to > _data_end:
        st.session_state.date_to = _data_end

    with st.expander("Filter by review date", expanded=False):
        st.markdown(
            '<div style="font-size:.78rem;color:var(--muted);margin-bottom:.9rem;">'
            'Only include reviews written within a specific date range. '
            'Use the quick-select buttons or enter custom dates below.</div>',
            unsafe_allow_html=True,
        )

        # ── Quick-select preset buttons ──────────────────────
        st.markdown('<div class="field-label" style="margin-bottom:.45rem;">Quick select</div>',
                    unsafe_allow_html=True)

        _qb_css = """
<style>
.date-preset > button {
    background: var(--surface2) !important;
    color: var(--text-dim) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: .72rem !important;
    font-weight: 500 !important;
    letter-spacing: .04em !important;
    padding: .28rem .7rem !important;
    min-height: unset !important;
    height: auto !important;
    line-height: 1.5 !important;
    text-transform: none !important;
    box-shadow: none !important;
    transition: border-color .15s, color .15s !important;
}
.date-preset > button:hover {
    border-color: var(--blue) !important;
    color: var(--text) !important;
    background: var(--surface3) !important;
    box-shadow: none !important;
    transform: none !important;
}
</style>"""
        st.markdown(_qb_css, unsafe_allow_html=True)

        _presets = [
            ("Last 7 days",   _today - timedelta(days=7),   _today),
            ("Last 30 days",  _today - timedelta(days=30),  _today),
            ("Last 90 days",  _today - timedelta(days=90),  _today),
            ("Last year",     _today - timedelta(days=365), _today),
            ("Last 3 years",  _today - timedelta(days=1095),_today),
            ("All time",      _data_start,                  _data_end),
        ]

        _pb_cols = st.columns(len(_presets))
        for _pi, (_plabel, _pfrom, _pto) in enumerate(_presets):
            with _pb_cols[_pi]:
                st.markdown('<div class="date-preset">', unsafe_allow_html=True)
                if st.button(_plabel, key=f"date_preset_{_pi}"):
                    # Clamp to data range
                    st.session_state.date_from = max(_pfrom, _data_start)
                    st.session_state.date_to   = min(_pto,   _data_end)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div style="height:.6rem;"></div>', unsafe_allow_html=True)

        # ── Custom date inputs ────────────────────────────────
        st.markdown('<div class="field-label" style="margin-bottom:.45rem;">Custom range</div>',
                    unsafe_allow_html=True)
        _dc1, _dc2, _dc3 = st.columns([1, 1, 3])
        with _dc1:
            st.markdown('<div class="field-label">From</div>', unsafe_allow_html=True)
            _di_from = st.date_input(
                "date_from_input", label_visibility="collapsed",
                value=st.session_state.date_from,
                min_value=_data_start, max_value=_data_end,
                key="date_from_widget",
            )
        with _dc2:
            st.markdown('<div class="field-label">To</div>', unsafe_allow_html=True)
            _di_to = st.date_input(
                "date_to_input", label_visibility="collapsed",
                value=st.session_state.date_to,
                min_value=_data_start, max_value=_data_end,
                key="date_to_widget",
            )

        # Sync widget values back to session state
        st.session_state.date_from = _di_from
        st.session_state.date_to   = _di_to

        # ── Apply the date filter ─────────────────────────────
        _dt_active = (
            st.session_state.date_from != _data_start or
            st.session_state.date_to   != _data_end
        )
        _df_before = len(df)
        if _di_from > _di_to:
            st.warning("'From' date must be on or before 'To' date.")
        else:
            _ts_from = int(datetime.combine(_di_from, datetime.min.time(),
                                            tzinfo=timezone.utc).timestamp())
            _ts_to   = int(datetime.combine(_di_to,   datetime.max.time(),
                                            tzinfo=timezone.utc).timestamp())
            df = df[
                (df["timestamp_created"] >= _ts_from) &
                (df["timestamp_created"] <= _ts_to)
            ].copy()
            _df_after = len(df)
            if _dt_active:
                _label_from = _di_from.strftime("%b %d, %Y")
                _label_to   = _di_to.strftime("%b %d, %Y")
                st.markdown(
                    f'<div style="font-size:.75rem;color:var(--blue);margin-top:.5rem;">'
                    f'Showing <strong>{_df_after:,}</strong> of {_df_before:,} reviews'
                    f' &nbsp;·&nbsp; {_label_from} → {_label_to}</div>',
                    unsafe_allow_html=True,
                )
                if len(df):
                    sdf = build_summary(df)

    # ── KPI strip ──
    total_reviews = len(df)
    total_games   = sdf["game_title"].nunique()
    avg_sentiment = sdf["positive_pct"].mean()
    top_game      = sdf.iloc[0]["game_title"] if len(sdf) else "—"
    top_game_pct  = sdf.iloc[0]["positive_pct"] if len(sdf) else 0
    avg_playtime  = df["author_playtime_hrs"].mean()

    # ── Sticky KPI bar + animated count-up ──
    _sentiment_colour = "#20c65a" if avg_sentiment >= 70 else "#f0a500" if avg_sentiment >= 50 else "#ff3d52"
    short = top_game[:24] + ("…" if len(top_game) > 24 else "")
    st.markdown(f"""
<style>
/* Sticky KPI strip */
.kpi-sticky {{
    position: sticky;
    top: 0;
    z-index: 999;
    background: var(--bg);
    padding: .6rem 0 .5rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.25rem;
}}
.kpi-strip {{
    display: flex;
    gap: 1rem;
    align-items: stretch;
}}
.kpi-tile {{
    flex: 1;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: .9rem 1.2rem;
    position: relative;
    overflow: hidden;
    transition: border-color .2s;
}}
.kpi-tile:hover {{ border-color: var(--border-hi); }}
.kpi-tile.blue-top {{ border-top: 2px solid var(--blue); }}
.kpi-tile.pos-top  {{ border-top: 2px solid {_sentiment_colour}; }}
.kpi-tile-label {{
    font-size: .58rem;
    font-weight: 700;
    letter-spacing: .2em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: .3rem;
}}
.kpi-tile-val {{
    font-family: 'Inter Tight', sans-serif;
    font-size: 1.9rem;
    font-weight: 900;
    color: var(--text);
    line-height: 1;
    letter-spacing: -.025em;
}}
.kpi-tile-sub {{ font-size: .68rem; color: var(--muted); margin-top: .2rem; }}
/* Count-up animation */
@keyframes countUp {{
    from {{ opacity: 0; transform: translateY(6px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
.kpi-tile-val {{ animation: countUp .5s ease forwards; }}
</style>
<div class="kpi-sticky">
  <div class="kpi-strip">
    <div class="kpi-tile blue-top">
      <div class="kpi-tile-label">Reviews Collected</div>
      <div class="kpi-tile-val">{total_reviews:,}</div>
      <div class="kpi-tile-sub">across {total_games} games</div>
    </div>
    <div class="kpi-tile pos-top">
      <div class="kpi-tile-label">Avg Sentiment</div>
      <div class="kpi-tile-val" style="color:{_sentiment_colour};">{avg_sentiment:.0f}%</div>
      <div class="kpi-tile-sub">positive reviews</div>
    </div>
    <div class="kpi-tile blue-top">
      <div class="kpi-tile-label">Top Rated</div>
      <div class="kpi-tile-val" style="font-size:1.1rem;line-height:1.25;padding-top:.15rem;">{short}</div>
      <div class="kpi-tile-sub">{top_game_pct:.0f}% positive</div>
    </div>
    <div class="kpi-tile blue-top">
      <div class="kpi-tile-label">Avg Playtime at Review</div>
      <div class="kpi-tile-val">{avg_playtime:.1f}<span style="font-size:1rem;font-weight:400;"> hrs</span></div>
      <div class="kpi-tile-sub">across all reviewers</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Tabs ──
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["SENTIMENT", "ENGAGEMENT", "GAME TABLE", "REVIEWS", "KEYWORD INSIGHTS", "AI ANALYSIS"])

    with tab1:
        # ── Methodology explainer ──
        with st.expander("How sentiment is calculated", expanded=False):
            st.markdown(
                'Steam reviewers must click thumbs up or thumbs down before submitting. '
                'This app reads that signal directly from the Steam API and computes '
                '**% Positive = thumbs up ÷ total reviews × 100**. '
                'No NLP or AI is involved in the score itself.\\n\\n'
                'Steam labels: ≥95% Overwhelmingly Positive · ≥80% Very Positive · '
                '≥70% Mostly Positive · ≥40% Mixed · <40% Negative.'
            )

        # ── Event split (shown first if events available) ────────────────────
        _all_ev_flat = [
            ev for evs in st.session_state.game_events.values() for ev in evs
        ]
        if _all_ev_flat and len(df):
            _df_ts_min = int(df["timestamp_created"].min())
            _df_ts_max = int(df["timestamp_created"].max())
            _all_ev_flat = [
                ev for ev in _all_ev_flat
                if _df_ts_min <= ev["ts"] <= _df_ts_max
            ]

        if _all_ev_flat:
            st.markdown(
                '<div class="section-header"><span class="dot"></span>'
                'SPLIT BY UPDATE / DLC EVENT</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div style="font-size:.78rem;color:var(--muted);margin-bottom:.75rem;">'
                'Select an event to split reviews into <strong style="color:var(--text);">Before</strong>'
                ' and <strong style="color:var(--text);">After</strong> windows. '
                'Optionally filter to a single game first.</div>',
                unsafe_allow_html=True,
            )

            # ── Controls row: game filter + event selector ────────────────────
            _all_games_in_events = sorted({ev["game"] for ev in _all_ev_flat})
            _ctrl_left, _ctrl_right = st.columns([1, 2])
            with _ctrl_left:
                st.markdown('<div class="field-label">Filter by game</div>', unsafe_allow_html=True)
                _game_filter = st.selectbox(
                    "Game filter", ["All games"] + _all_games_in_events,
                    key="event_game_filter",
                    label_visibility="collapsed",
                )
            with _ctrl_right:
                st.markdown('<div class="field-label">Event</div>', unsafe_allow_html=True)
                _evs_for_sel = _all_ev_flat if _game_filter == "All games" else [
                    ev for ev in _all_ev_flat if ev["game"] == _game_filter
                ]
                _ev_options = {
                    f"{ev['date_str']}  —  [{ev['type']}]  {ev['game'][:28]}: {ev['title'][:50]}": ev
                    for ev in sorted(_evs_for_sel, key=lambda x: x["ts"])
                }
                _ev_sel_label = st.selectbox(
                    "Event", ["— none —"] + list(_ev_options.keys()),
                    key="event_split_sel",
                    label_visibility="collapsed",
                )

            if _ev_sel_label != "— none —":
                _ev = _ev_options[_ev_sel_label]
                _split_ts = _ev["ts"]
                _split_date = _ev["date_str"]

                # Apply game filter to the data if set
                _df_split = df[df["game_title"] == _game_filter].copy() if _game_filter != "All games" else df.copy()

                _before = _df_split[_df_split["timestamp_created"] <  _split_ts].copy()
                _after  = _df_split[_df_split["timestamp_created"] >= _split_ts].copy()

                def _window_stats(wdf):
                    if not len(wdf):
                        # Use None to signal "empty window" — distinct from 0%
                        return {"reviews": 0, "pos_pct": None, "avg_hrs": None, "games": 0}
                    return {
                        "reviews": len(wdf),
                        "pos_pct": wdf["voted_up"].mean() * 100,
                        "avg_hrs": wdf["author_playtime_hrs"].mean(),
                        "games":   wdf["game_title"].nunique(),
                    }

                _bs = _window_stats(_before)
                _as = _window_stats(_after)

                def _delta(a, b, fmt=".1f", suffix=""):
                    # Suppress arrow if either window is empty or values are None
                    if a is None or b is None:
                        return ""
                    d = a - b
                    col = "#20c65a" if d > 0 else "#ff3d52" if d < 0 else "#5a5f82"
                    arrow = "▲" if d > 0 else "▼" if d < 0 else "—"
                    return (f'<span style="font-size:.72rem;color:{col};'
                            f'font-weight:700;margin-left:.4rem;">'
                            f'{arrow} {abs(d):{fmt}}{suffix}</span>')

                _type_col = {"DLC": "#f0a500", "Update": "#a060ff", "Release": "#20c65a"}
                _ecol = _type_col.get(_ev["type"], "#6b7194")

                # Event expander — click to expand full update details
                _ev_url      = _ev.get("url", "")
                _ev_contents = _ev.get("contents", "")
                _expander_label = (
                    f"[{_ev['type']}]  {_ev['title']}  ·  {_ev['game']}  ·  {_split_date}"
                )
                with st.expander(_expander_label, expanded=False):
                    st.markdown(
                        f'<span style="background:{_ecol}22;color:{_ecol};'
                        f'border:1px solid {_ecol}44;font-size:.66rem;font-weight:700;'
                        f'letter-spacing:.08em;padding:.15rem .5rem;border-radius:3px;'
                        f'text-transform:uppercase;">{_ev["type"]}</span>'
                        f'&nbsp;&nbsp;<strong>{_ev["title"]}</strong>'
                        f'<span style="color:var(--muted);font-size:.8rem;"> &nbsp;·&nbsp; '
                        f'{_ev["game"]} &nbsp;·&nbsp; {_split_date}</span>',
                        unsafe_allow_html=True,
                    )
                    if _ev_contents:
                        st.markdown(
                            f'<div style="font-size:.82rem;color:var(--text);line-height:1.65;'
                            f'margin-top:.6rem;padding-top:.6rem;border-top:1px solid var(--border);">'
                            f'{_ev_contents}</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.caption("No description available for this event.")
                    if _ev_url:
                        st.markdown(
                            f'<a href="{_ev_url}" target="_blank" rel="noopener" '
                            f'style="font-size:.78rem;color:var(--blue);text-decoration:none;'
                            f'font-weight:600;">View full announcement on Steam ↗</a>',
                            unsafe_allow_html=True,
                        )

                # Before/After stat panels
                def _fmt_edge_date(wdf, side):
                    from datetime import datetime, timezone as _tz
                    col = wdf["timestamp_created"]
                    t = col.max() if side == "before" else col.min()
                    if t is None or (hasattr(t, "__float__") and pd.isna(t)):
                        return "—"
                    try:
                        return datetime.fromtimestamp(int(t), _tz.utc).strftime("%b %Y")
                    except Exception:
                        return "—"

                _bc1, _divider, _ac1 = st.columns([5, 1, 5])

                def _render_window(col, label, stats, other_stats, border_col):
                    with col:
                        _empty   = stats["reviews"] == 0
                        _pct_val = stats["pos_pct"]
                        _hrs_val = stats["avg_hrs"]
                        # Sentiment colour — grey when empty
                        _s_col   = (
                            "var(--muted)" if _empty else
                            "#20c65a" if _pct_val >= 70 else
                            "#f0a500" if _pct_val >= 50 else
                            "#ff3d52"
                        )
                        _s_txt   = "—" if _empty else f"{_pct_val:.1f}%"
                        _h_txt   = "—" if _empty else f"{_hrs_val:.1f}h"
                        st.markdown(
                            f'<div style="background:var(--surface2);border:1px solid var(--border);'
                            f'border-top:2px solid {border_col};border-radius:8px;padding:1rem 1.2rem;">'
                            f'<div style="font-size:.6rem;font-weight:700;letter-spacing:.18em;'
                            f'text-transform:uppercase;color:{border_col};margin-bottom:.75rem;">'
                            f'{label}</div>'
                            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:.6rem;">'
                            f'<div><div style="font-size:.55rem;font-weight:700;letter-spacing:.15em;'
                            f'text-transform:uppercase;color:var(--muted);margin-bottom:.15rem;">Reviews</div>'
                            f'<div style="font-family:Inter Tight,sans-serif;font-size:1.6rem;'
                            f'font-weight:900;color:{"var(--muted)" if _empty else "var(--text)"};line-height:1;">'
                            f'{stats["reviews"]:,}</div></div>'
                            f'<div><div style="font-size:.55rem;font-weight:700;letter-spacing:.15em;'
                            f'text-transform:uppercase;color:var(--muted);margin-bottom:.15rem;">Sentiment</div>'
                            f'<div style="font-family:Inter Tight,sans-serif;font-size:1.6rem;'
                            f'font-weight:900;line-height:1;color:{_s_col};">'
                            f'{_s_txt}'
                            f'{_delta(_pct_val, other_stats["pos_pct"], ".1f", "%")}'
                            f'</div></div>'
                            f'<div><div style="font-size:.55rem;font-weight:700;letter-spacing:.15em;'
                            f'text-transform:uppercase;color:var(--muted);margin-bottom:.15rem;">Avg Playtime</div>'
                            f'<div style="font-family:Inter Tight,sans-serif;font-size:1.6rem;'
                            f'font-weight:900;color:{"var(--muted)" if _empty else "var(--text)"};line-height:1;">'
                            f'{_h_txt}'
                            f'{_delta(_hrs_val, other_stats["avg_hrs"], ".1f", "h")}'
                            f'</div></div>'
                            f'<div><div style="font-size:.55rem;font-weight:700;letter-spacing:.15em;'
                            f'text-transform:uppercase;color:var(--muted);margin-bottom:.15rem;">Games</div>'
                            f'<div style="font-family:Inter Tight,sans-serif;font-size:1.6rem;'
                            f'font-weight:900;color:{"var(--muted)" if _empty else "var(--text)"};line-height:1;">'
                            f'{stats["games"]}</div></div>'
                            f'</div></div>',
                            unsafe_allow_html=True,
                        )

                _render_window(
                    _bc1,
                    f"Before  ·  up to {_fmt_edge_date(_before, 'before') if len(_before) else '—'}",
                    _bs, _as, "#4080ff",
                )
                with _divider:
                    st.markdown(
                        '<div style="display:flex;justify-content:center;align-items:center;'
                        'height:100%;padding-top:2rem;">'
                        '<div style="font-size:1.4rem;color:var(--muted);">→</div></div>',
                        unsafe_allow_html=True,
                    )
                _render_window(
                    _ac1,
                    f"After  ·  from {_fmt_edge_date(_after, 'after') if len(_after) else '—'}",
                    _as, _bs, _ecol,
                )

                # Warn if one window is empty (usually a fetch limit issue)
                if _bs["reviews"] == 0 or _as["reviews"] == 0:
                    _empty_side = "Before" if _bs["reviews"] == 0 else "After"
                    st.info(
                        f"The **{_empty_side}** window has no reviews. "
                        "This is usually because the review fetch limit was set low and all "
                        "collected reviews fall on one side of the event date. "
                        "Try re-fetching with a higher review limit (500+) to capture a wider date range."
                    )

                # Per-game breakdown (when not filtered to a single game)
                if _game_filter == "All games" and len(df["game_title"].unique()) > 1:
                    st.markdown(
                        '<div style="margin-top:1.25rem;">'
                        '<div style="font-size:.62rem;font-weight:700;letter-spacing:.18em;'
                        'text-transform:uppercase;color:var(--muted);margin-bottom:.6rem;">'
                        'Per-game sentiment shift</div>',
                        unsafe_allow_html=True,
                    )
                    _pg_rows = []
                    for _gname in sorted(df["game_title"].unique()):
                        _gb = _before[_before["game_title"] == _gname]
                        _ga = _after[_after["game_title"] == _gname]
                        _b_pct = _gb["voted_up"].mean() * 100 if len(_gb) else None
                        _a_pct = _ga["voted_up"].mean() * 100 if len(_ga) else None
                        _pg_rows.append({
                            "Game":       _gname,
                            "Before":     f"{_b_pct:.1f}%" if _b_pct is not None else "—",
                            "After":      f"{_a_pct:.1f}%" if _a_pct is not None else "—",
                            "Change":     round(_a_pct - _b_pct, 1) if (_b_pct is not None and _a_pct is not None) else None,
                            "Before (#)": len(_gb),
                            "After (#)":  len(_ga),
                        })
                    st.dataframe(
                        pd.DataFrame(_pg_rows),
                        width='stretch',
                        hide_index=True,
                        column_config={"Change": st.column_config.NumberColumn("Change (pp)", format="%.1f")},
                    )
                    st.markdown('</div>', unsafe_allow_html=True)

                # ── CSV export ────────────────────────────────────────────────
                st.markdown(
                    '<div style="font-size:.62rem;font-weight:700;letter-spacing:.18em;'
                    'text-transform:uppercase;color:var(--muted);margin-top:1.25rem;margin-bottom:.5rem;">'
                    'Export reviews</div>',
                    unsafe_allow_html=True,
                )
                _csv_cols = st.columns(3)
                _ev_slug  = _ev["title"][:24].strip().replace(" ", "_").lower()
                _game_slug = _game_filter.replace(" ", "_").lower() if _game_filter != "All games" else "all"
                for _ci, (_clabel, _cdf, _cfname) in enumerate([
                    ("Before", _before, f"reviews_before_{_ev_slug}_{_game_slug}.csv"),
                    ("After",  _after,  f"reviews_after_{_ev_slug}_{_game_slug}.csv"),
                    ("Both",   _df_split, f"reviews_all_{_ev_slug}_{_game_slug}.csv"),
                ]):
                    with _csv_cols[_ci]:
                        st.download_button(
                            f"Download {_clabel} ({len(_cdf):,})",
                            data=_cdf.to_csv(index=False).encode("utf-8"),
                            file_name=_cfname,
                            mime="text/csv",
                            width='stretch',
                            key=f"dl_csv_{_clabel.lower()}_{_ev['ts']}",
                        )

                # Timeline with all events marked
                _tl2 = chart_sentiment_timeline(_df_split, events=_all_ev_flat)
                if _tl2.data:
                    st.markdown(
                        '<div style="margin-top:1rem;font-size:.62rem;font-weight:700;'
                        'letter-spacing:.18em;text-transform:uppercase;color:var(--muted);">'
                        'Timeline with all events marked</div>',
                        unsafe_allow_html=True,
                    )
                    st.plotly_chart(_tl2, width='stretch',
                                    config={"displayModeBar": False})

        elif st.session_state.results_df is not None and not _all_ev_flat:
            st.caption("No patch/DLC/update events found in Steam News for the selected games.")

        # ── Standard charts ───────────────────────────────────────────────────
        st.markdown(
            '<div class="section-header"><span class="dot"></span>POSITIVE SENTIMENT RANKING</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(chart_sentiment_bar(sdf), width='stretch',
                        config={"displayModeBar": False})

        st.markdown(
            '<div class="section-header"><span class="dot"></span>SENTIMENT vs. PLAYTIME</div>',
            unsafe_allow_html=True,
        )
        st.caption("Bubble size = number of reviews collected")
        st.plotly_chart(chart_scatter(sdf), width='stretch',
                        config={"displayModeBar": False})

        st.markdown(
            '<div class="section-header"><span class="dot"></span>SENTIMENT OVER TIME</div>',
            unsafe_allow_html=True,
        )
        st.caption("Monthly % positive reviews — shows how reception has shifted over time")
        _tl = chart_sentiment_timeline(df)
        if _tl.data:
            st.plotly_chart(_tl, width='stretch',
                            config={"displayModeBar": False})
        else:
            st.info("Not enough timestamped reviews to plot a timeline.")

    with tab2:
        left, right = st.columns(2)
        with left:
            st.markdown(
                '<div class="section-header"><span class="dot"></span>REVIEW VOLUME BY GAME</div>',
                unsafe_allow_html=True,
            )
            st.plotly_chart(chart_review_volume(sdf), width='stretch',
                            config={"displayModeBar": False})
        with right:
            st.markdown(
                '<div class="section-header"><span class="dot"></span>PLAYTIME DISTRIBUTION</div>',
                unsafe_allow_html=True,
            )
            st.caption("Reviews capped at 200 hrs · amber line = median")
            st.plotly_chart(chart_playtime_hist(df), width='stretch',
                            config={"displayModeBar": False})


    with tab3:
        st.markdown(
            '<div class="section-header"><span class="dot"></span>GAME SUMMARY</div>',
            unsafe_allow_html=True,
        )
        # Build sparkline data: monthly sentiment % per game as a list
        from datetime import datetime, UTC as _UTC
        _df_ts = df.copy()
        _df_ts["month"] = pd.to_datetime(_df_ts["timestamp_created"].apply(
            lambda ts: datetime.fromtimestamp(int(ts), _UTC).strftime("%Y-%m")
            if ts is not None and pd.notna(ts) else None
        ), errors="coerce")

        def _sparkline(game):
            g = _df_ts[_df_ts["game_title"] == game].dropna(subset=["month"])
            if len(g) < 3:
                return []
            monthly = (
                g.groupby("month")
                .apply(lambda x: round(x["voted_up"].mean() * 100, 1), include_groups=False)
                .reset_index()
            )
            monthly.columns = ["month", "pct"]
            monthly = monthly.sort_values("month")
            return monthly["pct"].tolist()

        display = sdf.copy()
        display["Trend"] = display["game_title"].apply(_sparkline)
        display = display.rename(columns={
            "game_title":          "Game",
            "total_reviews":       "Reviews",
            "positive_reviews":    "Positive",
            "negative_reviews":    "Negative",
            "positive_pct":        "% Positive",
            "avg_playtime_hrs":    "Avg Hrs",
            "median_playtime_hrs": "Median Hrs",
            "avg_helpful_votes":   "Avg Helpful",
        })
        # Reorder columns
        col_order = ["Game", "Reviews", "% Positive", "Trend",
                     "Positive", "Negative", "Avg Hrs", "Median Hrs", "Avg Helpful"]
        display = display[[c for c in col_order if c in display.columns]]
        st.dataframe(
            display,
            width='stretch',
            hide_index=True,
            column_config={
                "% Positive": st.column_config.ProgressColumn(
                    "% Positive", min_value=0, max_value=100, format="%.1f%%",
                ),
                "Trend": st.column_config.LineChartColumn(
                    "Sentiment Trend", y_min=0, y_max=100,
                ),
            },
        )
        dl_col, _ = st.columns([1, 4])
        with dl_col:
            csv = df.to_csv(index=False, encoding="utf-8-sig").encode()
            genre_slug = st.session_state.last_genre.replace(" ", "_")
            st.download_button(
                "EXPORT RAW CSV",
                data=csv,
                file_name=f"steam_reviews_{genre_slug}.csv",
                mime="text/csv",
                width='stretch',
            )

    with tab4:
        st.markdown(
            '<div class="section-header"><span class="dot"></span>SAMPLE REVIEWS</div>',
            unsafe_allow_html=True,
        )
        f_col, g_col, s_col, _ = st.columns([1.3, 1.6, 1.5, 2])
        with f_col:
            filter_mode = st.selectbox(
                "Show", ["Most Helpful", "Positive Only", "Negative Only", "Random"],
                label_visibility="visible",
            )
        with g_col:
            game_options = ["All Games"] + sorted(df["game_title"].unique().tolist())
            game_filter  = st.selectbox("Game", game_options, label_visibility="visible")
        with s_col:
            _has_vader = "vader_compound" in df.columns and df["vader_compound"].notna().any()
            sort_opts = ["Default", "Date (newest)", "Date (oldest)",
                         "Helpfulness", "Playtime (high→low)", "Playtime (low→high)"]
            if _has_vader:
                sort_opts += ["VADER (most positive)", "VADER (most negative)"]
            sort_by = st.selectbox("Sort by", sort_opts, label_visibility="visible")

        # Copy button CSS injected once
        st.markdown("""
<style>
.copy-btn > button {
    background: transparent !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    color: var(--muted) !important;
    font-size: .65rem !important;
    font-weight: 600 !important;
    letter-spacing: .08em !important;
    padding: .15rem .5rem !important;
    min-height: unset !important;
    height: auto !important;
    line-height: 1.5 !important;
    text-transform: uppercase !important;
    box-shadow: none !important;
    transform: none !important;
}
.copy-btn > button:hover {
    border-color: var(--blue) !important;
    color: var(--blue) !important;
    background: transparent !important;
    transform: none !important;
    box-shadow: none !important;
}
</style>""", unsafe_allow_html=True)

        sample = df.copy()
        if game_filter != "All Games":
            sample = sample[sample["game_title"] == game_filter]
        if filter_mode == "Positive Only":
            sample = sample[sample["voted_up"] == True]
        elif filter_mode == "Negative Only":
            sample = sample[sample["voted_up"] == False]
        elif filter_mode == "Most Helpful":
            sample = sample.nlargest(50, "votes_helpful")
        else:
            sample = sample.sample(min(50, len(sample)), random_state=42)

        sample = sample[sample["review_text"].str.len() > 30].copy()

        # Apply sort
        if sort_by == "Date (newest)" and "timestamp_created" in sample.columns:
            sample = sample.sort_values("timestamp_created", ascending=False)
        elif sort_by == "Date (oldest)" and "timestamp_created" in sample.columns:
            sample = sample.sort_values("timestamp_created", ascending=True)
        elif sort_by == "Helpfulness":
            sample = sample.sort_values("votes_helpful", ascending=False)
        elif sort_by == "Playtime (high→low)":
            sample = sample.sort_values("author_playtime_hrs", ascending=False)
        elif sort_by == "Playtime (low→high)":
            sample = sample.sort_values("author_playtime_hrs", ascending=True)
        elif sort_by == "VADER (most positive)" and _has_vader:
            sample = sample.sort_values("vader_compound", ascending=False)
        elif sort_by == "VADER (most negative)" and _has_vader:
            sample = sample.sort_values("vader_compound", ascending=True)

        sample = sample.head(15)

        if sample.empty:
            st.info("No reviews match the selected filters.")
        for _, row in sample.iterrows():
            is_pos    = bool(row["voted_up"])
            sentiment = "positive" if is_pos else "negative"
            icon      = "+" if is_pos else "-"
            # Strip BBCode tags ([h1], [b], [url=...], etc.) and escape for HTML
            _raw_text = row["review_text"] or ""
            _clean_text = re.sub(r"\[/?[a-zA-Z0-9_]+(?:=[^\]]*)?]", "", _raw_text)
            _clean_text = re.sub(r"\n{3,}", "\n\n", _clean_text.strip())
            import html as _html_mod
            _clean_html = _html_mod.escape(_clean_text).replace("\n", "<br>")
            snippet = _clean_html[:700] + ("…" if len(_clean_html) > 700 else "")
            _copy_plain = _clean_text[:700]  # plain text for clipboard
            ts        = row.get("timestamp_created")
            date_str  = ""
            if ts:
                try:
                    from datetime import datetime, UTC
                    date_str = datetime.fromtimestamp(int(ts), UTC).strftime("%b %d, %Y")
                except Exception:
                    pass

            steamid      = str(row.get("author_steamid", "") or "")
            rec_id       = str(row.get("recommendation_id", "") or "")
            app_id_r     = int(row.get("app_id", 0) or 0)
            num_reviews  = int(row.get("author_num_reviews", 0) or 0)
            num_games    = int(row.get("author_num_games_owned", 0) or 0)
            total_hrs    = float(row.get("author_playtime_total_hrs", 0) or 0)
            at_rev_hrs   = float(row.get("author_playtime_hrs", 0) or 0)
            helpful      = int(row.get("votes_helpful", 0) or 0)
            funny        = int(row.get("votes_funny", 0) or 0)

            profile_link = f"https://steamcommunity.com/profiles/{steamid}" if steamid else ""
            review_link  = (f"https://store.steampowered.com/app/{app_id_r}/#app_reviews_hash"
                            if app_id_r else "")

            profile_html = (
                f'<a href="{profile_link}" target="_blank" rel="noopener" '
                f'style="color:var(--blue);text-decoration:none;font-weight:600;">'
                f'Steam Profile ↗</a>' if profile_link else
                '<span style="color:var(--muted);">Anonymous</span>'
            )
            review_link_html = (
                f' &nbsp;·&nbsp; <a href="{review_link}" target="_blank" rel="noopener" '
                f'style="color:var(--muted);text-decoration:none;">View on Steam ↗</a>'
                if review_link else ""
            )
            games_str    = f"{num_games:,} games owned" if num_games else ""
            reviews_str  = f"{num_reviews:,} reviews written" if num_reviews else ""
            total_str    = f"{total_hrs:,.0f} hrs total on record" if total_hrs else ""
            helpful_str  = f"{helpful} helpful" if helpful else ""
            funny_str    = f"{funny} funny" if funny else ""

            author_meta = " &nbsp;·&nbsp; ".join(filter(None, [games_str, reviews_str, total_str]))
            react_meta  = " &nbsp;·&nbsp; ".join(filter(None, [helpful_str, funny_str]))

            border_color = "#20c65a" if is_pos else "#ff3d52"
            bg_color     = "rgba(32,198,90,.13)" if is_pos else "rgba(255,61,82,.13)"
            badge_color  = "#20c65a" if is_pos else "#ff3d52"
            badge_border = "rgba(32,198,90,.28)" if is_pos else "rgba(255,61,82,.28)"
            date_html    = f"<span>{date_str}</span>" if date_str else ""
            react_html   = f"<span>{react_meta}</span>" if react_meta else ""
            meta_html    = (" &nbsp;·&nbsp; " + author_meta) if author_meta else ""

            # VADER badge
            vader_val = row.get("vader_compound") if VADER_AVAILABLE else None
            if vader_val is not None and not pd.isna(vader_val):
                _vc = float(vader_val)
                _vc_col = "#20c65a" if _vc >= 0.05 else "#ff3d52" if _vc <= -0.05 else "#f0a500"
                _vc_sign = "+" if _vc >= 0 else ""
                vader_badge = (
                    f'<span style="background:rgba(0,0,0,.22);border:1px solid {_vc_col}44;'
                    f'color:{_vc_col};font-size:.64rem;font-weight:700;letter-spacing:.04em;'
                    f'padding:.1rem .38rem;border-radius:3px;font-family:Inter Tight,sans-serif;">'
                    f'VADER {_vc_sign}{_vc:.2f}</span>'
                )
            else:
                vader_badge = ""

            # Copy button — JSON.dumps produces a safe JS string literal
            import json as _json_mod
            _copy_json = _json_mod.dumps(_copy_plain)
            copy_btn = (
                f'<button onclick="navigator.clipboard.writeText({_copy_json}).catch(()={{}})" '
                f'style="flex-shrink:0;background:transparent;border:1px solid var(--border);'
                f'border-radius:4px;color:var(--muted);font-size:.62rem;font-weight:600;'
                f'letter-spacing:.06em;padding:.18rem .44rem;cursor:pointer;'
                f'text-transform:uppercase;font-family:Poppins,sans-serif;line-height:1.5;'
                f'transition:border-color .15s,color .15s;white-space:nowrap;" '
                f'onmouseover="this.style.borderColor=\'#4080ff\';this.style.color=\'#4080ff\';" '
                f'onmouseout="this.style.borderColor=\'var(--border)\';this.style.color=\'var(--muted)\';">'
                f'Copy</button>'
            )

            card_html = (
                f'<div style="background:var(--surface2);border:1px solid var(--border);'
                f'border-left:3px solid {border_color};border-radius:0 6px 6px 0;'
                f'padding:.9rem 1.1rem 1rem;margin-bottom:.8rem;">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:.75rem;">'
                f'<div style="font-size:.85rem;line-height:1.65;color:var(--text);">{snippet}</div>'
                f'{copy_btn}'
                f'</div>'
                f'<div style="border-top:1px solid var(--border);padding-top:.55rem;margin-top:.65rem;">'
                f'<div style="display:flex;flex-wrap:wrap;gap:.28rem .65rem;align-items:center;'
                f'font-size:.72rem;color:var(--muted);margin-bottom:.32rem;">'
                f'<span style="background:{bg_color};color:{badge_color};'
                f'border:1px solid {badge_border};'
                f'font-size:.66rem;font-weight:700;letter-spacing:.06em;'
                f'padding:.1rem .42rem;border-radius:3px;text-transform:uppercase;">'
                f'{icon} {sentiment}</span>'
                f'{vader_badge}'
                f'<strong style="color:var(--text);">{row["game_title"]}</strong>'
                f'<span>{at_rev_hrs:.0f} hrs at review</span>'
                f'{date_html}{react_html}'
                f'</div>'
                f'<div style="font-size:.71rem;color:var(--muted);">'
                f'Profile: {profile_html}{meta_html} {review_link_html}'
                f'</div></div></div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────
    # ──────────────────────────────────────────────────────────
    # TAB 5 — KEYWORD INSIGHTS
    # ──────────────────────────────────────────────────────────
    with tab5:
        # ── initialise session state keys for this tab ──
        if "kw_selected_term" not in st.session_state:
            st.session_state.kw_selected_term = None
        if "kw_selected_sentiment" not in st.session_state:
            st.session_state.kw_selected_sentiment = None   # "pos" | "neg"
        st.markdown(
            '<div class="section-header"><span class="dot"></span>WHAT ARE PEOPLE TALKING ABOUT?</div>',
            unsafe_allow_html=True,
        )
        st.markdown("""
        <div style="background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--blue);
                    border-radius:0 6px 6px 0;padding:.9rem 1.25rem;margin-bottom:1.5rem;
                    font-size:.83rem;color:var(--muted);line-height:1.7;">
          Keywords are extracted by tokenising every review, removing common stopwords, and counting
          the most frequent single words and two-word phrases. Positive and negative clouds
          are built from <strong style="color:#20c65a;">positive</strong> and
          <strong style="color:#ff3d52;">negative</strong> reviews respectively.
          <strong style="color:var(--text);">Click any keyword</strong> to see the reviews that mention it.
        </div>
        """, unsafe_allow_html=True)

        # ── keyword button CSS (override Streamlit's default button look) ──
        st.markdown("""
        <style>
        /* keyword chip buttons */
        div[data-testid="stHorizontalBlock"] .kw-btn-pos > button,
        .kw-btn-pos > button {
            background: rgba(32,198,90,0.12) !important;
            border: 1px solid rgba(32,198,90,0.35) !important;
            color: #20c65a !important;
            border-radius: 3px !important;
            font-size: .78rem !important;
            font-weight: 500 !important;
            padding: .18rem .6rem !important;
            margin: .15rem !important;
            min-height: unset !important;
            height: auto !important;
            line-height: 1.4 !important;
        }
        .kw-btn-pos > button:hover { background: rgba(32,198,90,0.22) !important; }
        .kw-btn-neg > button {
            background: rgba(255,61,82,0.12) !important;
            border: 1px solid rgba(255,61,82,0.35) !important;
            color: #ff3d52 !important;
            border-radius: 3px !important;
            font-size: .78rem !important;
            font-weight: 500 !important;
            padding: .18rem .6rem !important;
            margin: .15rem !important;
            min-height: unset !important;
            height: auto !important;
            line-height: 1.4 !important;
        }
        .kw-btn-neg > button:hover { background: rgba(255,61,82,0.22) !important; }
        .kw-btn-active-pos > button {
            background: rgba(32,198,90,0.3) !important;
            border: 1px solid #20c65a !important;
            color: #fff !important;
            font-weight: 700 !important;
        }
        .kw-btn-active-neg > button {
            background: rgba(255,61,82,0.3) !important;
            border: 1px solid #ff3d52 !important;
            color: #fff !important;
            font-weight: 700 !important;
        }
        </style>
        """, unsafe_allow_html=True)

        def render_keyword_buttons(kws, sentiment, key_prefix, active_term):
            """Render keyword buttons; clicking one shows matching reviews below."""
            if not kws:
                st.markdown('<span style="font-size:.8rem;color:var(--muted);">No data</span>',
                            unsafe_allow_html=True)
                return

            is_pos   = sentiment == "pos"
            max_c    = kws[0][1]
            n_cols   = 5
            rows     = [kws[i:i+n_cols] for i in range(0, len(kws), n_cols)]

            for row_kws in rows:
                btn_cols = st.columns(len(row_kws) + (n_cols - len(row_kws)))  # pad to n_cols
                for col, (word, count) in zip(btn_cols, row_kws):
                    is_active = (active_term == word)
                    css_class = (
                        f"kw-btn-active-{'pos' if is_pos else 'neg'}"
                        if is_active else
                        f"kw-btn-{'pos' if is_pos else 'neg'}"
                    )
                    with col:
                        st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
                        label = f"{word}  {count}"
                        if st.button(label, key=f"{key_prefix}_{sentiment}_{word.replace(' ','_')}"):
                            if is_active:
                                # clicking the active chip deselects it
                                st.session_state[f"{key_prefix}_term"] = None
                                st.session_state[f"{key_prefix}_sentiment"] = None
                            else:
                                st.session_state[f"{key_prefix}_term"]      = word
                                st.session_state[f"{key_prefix}_sentiment"] = sentiment
                        st.markdown('</div>', unsafe_allow_html=True)

        def render_matching_reviews(term, sentiment, df_source, game_filter=None):
            """Show reviews from df_source that contain term (case-insensitive)."""
            is_pos   = sentiment == "pos"
            voted    = True if is_pos else False
            colour   = "#20c65a" if is_pos else "#ff3d52"
            icon     = "+" if is_pos else "-"

            pool = df_source[df_source["voted_up"] == voted].copy()
            if game_filter:
                pool = pool[pool["game_title"] == game_filter]

            # Case-insensitive substring match
            mask    = pool["review_text"].str.contains(re.escape(term), case=False, na=False)
            matches = pool[mask].copy()

            # Sort: most helpful first, then longest
            matches = matches.sort_values(
                ["votes_helpful", "review_text"],
                ascending=[False, False],
                key=lambda s: s if s.name == "votes_helpful" else s.str.len()
            ).head(10)

            n = len(pool[mask])
            border_hex = colour
            st.markdown(
                f'<div style="background:var(--surface);border:1px solid var(--border);'
                f'border-left:3px solid {border_hex};border-radius:0 6px 6px 0;'
                f'padding:.75rem 1.1rem;margin:1rem 0 .75rem;">'
                f'<span style="font-size:.7rem;font-weight:700;letter-spacing:.15em;'
                f'text-transform:uppercase;color:{colour};">REVIEWS MENTIONING</span> '
                f'<span style="font-family:Inter Tight,sans-serif;font-weight:800;'
                f'font-size:1.05rem;color:var(--text);">"{term}"</span> '
                f'<span style="font-size:.75rem;color:var(--muted);">'
                f'— {n:,} {icon} {"positive" if is_pos else "negative"} reviews match'
                f'{"  ·  " + game_filter if game_filter else ""}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if matches.empty:
                st.info("No reviews matched.")
                return

            for _, row in matches.iterrows():
                text = row["review_text"]
                # Bold every occurrence of the keyword
                _snip = text[:500] + ("…" if len(text) > 500 else "")
                highlighted = re.sub(
                    re.escape(term),
                    lambda m: '<strong style="color:' + colour + ';font-weight:700;">' + m.group(0) + '</strong>',
                    _snip,
                    flags=re.IGNORECASE,
                )
                steamid   = str(row.get("author_steamid", "") or "")
                rec_id    = str(row.get("recommendation_id", "") or "")
                app_id_r  = int(row.get("app_id", 0) or 0)
                at_hrs    = float(row.get("author_playtime_hrs", 0) or 0)
                helpful   = int(row.get("votes_helpful", 0) or 0)
                profile_html = (
                    f'<a href="https://steamcommunity.com/profiles/{steamid}" target="_blank" '
                    f'rel="noopener" style="color:var(--blue);text-decoration:none;">Profile ↗</a>'
                    if steamid else ""
                )
                review_link_html = (
                    f'<a href="https://store.steampowered.com/app/{app_id_r}/#app_reviews_hash" '
                    f'target="_blank" rel="noopener" style="color:var(--muted);text-decoration:none;">'
                    f'View on Steam ↗</a>'
                    if app_id_r else ""
                )
                meta_parts = list(filter(None, [
                    f"{at_hrs:.0f} hrs at review",
                    f"{helpful} helpful" if helpful else "",
                    profile_html,
                    review_link_html,
                ]))
                meta_str = " &nbsp;·&nbsp; ".join(meta_parts)
                st.markdown(
                    f'<div style="background:var(--surface2);border:1px solid var(--border);'
                    f'border-left:3px solid {colour};border-radius:0 6px 6px 0;'
                    f'padding:.8rem 1rem .85rem;margin-bottom:.7rem;">'
                    f'<div style="font-size:.84rem;line-height:1.65;color:var(--text);margin-bottom:.5rem;">'
                    f'{highlighted}</div>'
                    f'<div style="font-size:.71rem;color:var(--muted);border-top:1px solid var(--border);'
                    f'padding-top:.4rem;">'
                    f'<strong style="color:var(--text);">{row["game_title"]}</strong>'
                    f' &nbsp;·&nbsp; {meta_str}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # ─── Unified keyword insights (single game selector) ────
        st.markdown(
            '<div class="section-header"><span class="dot"></span>'
            'KEYWORD INSIGHTS  '
            '<span style="color:var(--muted);font-size:.7rem;font-weight:400;">'
            '— filter by game, click any keyword to see matching reviews</span></div>',
            unsafe_allow_html=True,
        )

        # Single game selector drives everything below
        ki_game_options = ["All Games"] + sorted(df["game_title"].unique().tolist())
        ki_sel_col, ki_info_col = st.columns([2, 5])
        with ki_sel_col:
            ki_game = st.selectbox(
                "Game filter", ki_game_options,
                key="ki_game_filter",
                label_visibility="collapsed",
            )

        # Reset selected keyword when game changes
        if st.session_state.get("ki_last_game") != ki_game:
            st.session_state.ki_last_game   = ki_game
            st.session_state.kw_selected_term      = None
            st.session_state.kw_selected_sentiment = None

        ki_df   = df if ki_game == "All Games" else df[df["game_title"] == ki_game]
        pos_df  = ki_df[ki_df["voted_up"] == True]
        neg_df  = ki_df[ki_df["voted_up"] == False]
        top_pos = extract_keywords(pos_df["review_text"].fillna("").tolist(), top_n=60)
        top_neg = extract_keywords(neg_df["review_text"].fillna("").tolist(), top_n=60)

        with ki_info_col:
            pos_pct = len(pos_df) / max(len(ki_df), 1) * 100
            label   = ki_game if ki_game != "All Games" else "all games"
            st.markdown(
                f'<div style="font-size:.78rem;color:var(--muted);padding-top:.45rem;">'
                f'{len(ki_df):,} reviews for {label} &nbsp;·&nbsp; '
                f'<span style="color:#20c65a;">{pos_pct:.0f}% positive</span></div>',
                unsafe_allow_html=True,
            )

        # ── Word clouds ───────────────────────────────────────
        if WORDCLOUD_AVAILABLE and (top_pos or top_neg):
            wc_l, wc_r = st.columns(2)
            with wc_l:
                st.markdown(
                    '<div style="font-size:.7rem;font-weight:700;letter-spacing:.15em;'
                    'text-transform:uppercase;color:#20c65a;margin-bottom:.4rem;">Positive</div>',
                    unsafe_allow_html=True,
                )
                if top_pos:
                    img_pos = generate_wordcloud_img(
                        _json.dumps({w: c for w, c in top_pos[:60]}), positive=True
                    )
                    if img_pos:
                        st.image(img_pos, width="stretch", output_format="PNG")
                else:
                    st.info("No positive reviews.")
            with wc_r:
                st.markdown(
                    '<div style="font-size:.7rem;font-weight:700;letter-spacing:.15em;'
                    'text-transform:uppercase;color:#ff3d52;margin-bottom:.4rem;">Negative</div>',
                    unsafe_allow_html=True,
                )
                if top_neg:
                    img_neg = generate_wordcloud_img(
                        _json.dumps({w: c for w, c in top_neg[:60]}), positive=False
                    )
                    if img_neg:
                        st.image(img_neg, width="stretch", output_format="PNG")
                else:
                    st.info("No negative reviews.")
        elif not WORDCLOUD_AVAILABLE:
            st.info("`pip install wordcloud matplotlib` to enable word clouds.")
        else:
            st.info("No review text found for the selected filter.")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Clickable keyword chips ───────────────────────────
        chip_l, chip_r = st.columns(2)
        with chip_l:
            st.markdown(
                '<div class="section-header"><span class="dot"></span>'
                f'WHAT PEOPLE LIKED '
                f'<span style="color:var(--muted);font-size:.7rem;font-weight:400;">'
                f'— {len(pos_df):,} positive reviews</span></div>',
                unsafe_allow_html=True,
            )
            render_keyword_buttons(
                top_pos[:30], "pos", "kw_selected",
                active_term=st.session_state.kw_selected_term
                    if st.session_state.kw_selected_sentiment == "pos" else None,
            )
        with chip_r:
            st.markdown(
                '<div class="section-header"><span class="dot"></span>'
                f'WHAT PEOPLE DISLIKED '
                f'<span style="color:var(--muted);font-size:.7rem;font-weight:400;">'
                f'— {len(neg_df):,} negative reviews</span></div>',
                unsafe_allow_html=True,
            )
            render_keyword_buttons(
                top_neg[:30], "neg", "kw_selected",
                active_term=st.session_state.kw_selected_term
                    if st.session_state.kw_selected_sentiment == "neg" else None,
            )

        # ── Matching reviews panel ────────────────────────────
        if st.session_state.kw_selected_term:
            render_matching_reviews(
                st.session_state.kw_selected_term,
                st.session_state.kw_selected_sentiment,
                ki_df,
                game_filter=ki_game if ki_game != "All Games" else None,
            )

        # ── Bar charts: top 15 terms ──────────────────────────
        st.markdown(
            '<div class="section-header"><span class="dot"></span>'
            'TOP TERMS — POSITIVE vs NEGATIVE</div>',
            unsafe_allow_html=True,
        )
        bc_l, bc_r = st.columns(2)
        with bc_l:
            if top_pos:
                words_p  = [w for w, _ in top_pos[:15]][::-1]
                counts_p = [c for _, c in top_pos[:15]][::-1]
                fig_kp = go.Figure(go.Bar(
                    y=words_p, x=counts_p, orientation="h",
                    marker_color="#20c65a", marker_opacity=0.8,
                    text=counts_p, textposition="outside",
                    textfont=dict(color="#eef0fa", size=10),
                ))
                fig_kp.update_layout(
                    **PLOTLY_BASE, height=420,
                    xaxis=dict(showgrid=False, tickfont=dict(color="#5a5f82")),
                    yaxis=dict(showgrid=False, tickfont=dict(color="#eef0fa", size=11)),
                    title=dict(text="Top Positive Terms", font=dict(color="#eef0fa", size=12)),
                )
                st.plotly_chart(fig_kp, width='stretch', config={"displayModeBar": False})
        with bc_r:
            if top_neg:
                words_n  = [w for w, _ in top_neg[:15]][::-1]
                counts_n = [c for _, c in top_neg[:15]][::-1]
                fig_kn = go.Figure(go.Bar(
                    y=words_n, x=counts_n, orientation="h",
                    marker_color="#ff3d52", marker_opacity=0.8,
                    text=counts_n, textposition="outside",
                    textfont=dict(color="#eef0fa", size=10),
                ))
                fig_kn.update_layout(
                    **PLOTLY_BASE, height=420,
                    xaxis=dict(showgrid=False, tickfont=dict(color="#5a5f82")),
                    yaxis=dict(showgrid=False, tickfont=dict(color="#eef0fa", size=11)),
                    title=dict(text="Top Negative Terms", font=dict(color="#eef0fa", size=12)),
                )
                st.plotly_chart(fig_kn, width='stretch', config={"displayModeBar": False})

    # TAB 6 — AI ANALYSIS
    # ──────────────────────────────────────────────────────────
    with tab6:

        st.markdown(
            '<div class="section-header"><span class="dot"></span>AI-POWERED REPORT</div>',
            unsafe_allow_html=True,
        )
        if not ANTHROPIC_AVAILABLE:
            st.error("anthropic SDK not installed. Run: `pip install anthropic`")
        else:
            # Read key from environment variable
            _env_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if _env_key:
                st.session_state.anthropic_api_key = _env_key

            # ── Report options ─────────────────────────────────
            opt_left, opt_right = st.columns(2)
            with opt_left:
                report_focus = st.selectbox(
                    "Report focus",
                    [
                        "Full overview — all games, all themes",
                        "Sentiment deep-dive — what drives positive vs negative",
                        "Competitive comparison — how games stack up against each other",
                        "Player pain points — what's most criticised and why",
                        "Player praise — what's most celebrated and why",
                    ],
                    key="ai_report_focus",
                )
            with opt_right:
                report_tone = st.selectbox(
                    "Output tone",
                    ["Analytical & objective", "Executive summary (brief)", "Consumer research style"],
                    key="ai_report_tone",
                )

            model_col, gen_col, test_col = st.columns([1.5, 1.5, 1])
            with model_col:
                ai_model = st.selectbox(
                    "Model",
                    ["claude-sonnet-4-5", "claude-haiku-4-5-20251001", "claude-opus-4-5"],
                    key="ai_model",
                    label_visibility="visible",
                )
            with gen_col:
                st.markdown("<br>", unsafe_allow_html=True)
                generate_clicked = st.button(
                    "GENERATE REPORT",
                    width='stretch',
                )
            with test_col:
                st.markdown("<br>", unsafe_allow_html=True)
                test_clicked = st.button(
                    "Test connection",
                    width='stretch',
                )

            if test_clicked:
                import httpx as _httpx
                with st.spinner("Testing…"):
                    try:
                        r = _httpx.get("https://api.anthropic.com", timeout=10)
                        st.success(f"Reached api.anthropic.com (HTTP {r.status_code})")
                    except _httpx.ConnectError as e:
                        st.error(f"Cannot reach api.anthropic.com: {e}")
                    except Exception as e:
                        st.error(f"{type(e).__name__}: {e}")

            # ── Prompt builder ─────────────────────────────────
            def build_analysis_prompt(df_, sdf_, focus, tone) -> str:
                genre_label = st.session_state.get("last_genre", "unknown genre")
                n_games     = sdf_["game_title"].nunique()
                n_reviews   = len(df_)
                avg_pos     = sdf_["positive_pct"].mean()

                # ── Per-game deep stats ───────────────────────
                game_blocks = []
                for _, row in sdf_.sort_values("positive_pct", ascending=False).iterrows():
                    g       = row["game_title"]
                    g_df    = df_[df_["game_title"] == g]
                    g_pos   = g_df[g_df["voted_up"] == True]
                    g_neg   = g_df[g_df["voted_up"] == False]

                    # playtime distribution
                    pt      = g_df["author_playtime_hrs"]
                    pt_med  = pt.median()
                    pt_p90  = pt.quantile(0.90)

                    # VADER compound for this game (computed inline)
                    vader_str = ""
                    if VADER_AVAILABLE and "vader_compound" in df_.columns:
                        gv = df_[df_["game_title"] == g]["vader_compound"].mean()
                        if not pd.isna(gv):
                            vader_str = f", VADER compound {gv:+.3f}"

                    # top 8 keywords per sentiment for this game
                    pos_kw = extract_keywords(g_pos["review_text"].fillna("").tolist(), 8)
                    neg_kw = extract_keywords(g_neg["review_text"].fillna("").tolist(), 8)
                    pos_kw_str = ", ".join(f"{w}({c})" for w, c in pos_kw) or "—"
                    neg_kw_str = ", ".join(f"{w}({c})" for w, c in neg_kw) or "—"

                    block = (
                        f"### {g}\n"
                        f"- Sentiment: {row['positive_pct']}% positive "
                        f"({row['positive_reviews']} pos / {row['negative_reviews']} neg, "
                        f"{n_reviews and round(len(g_df)/n_reviews*100)}% of dataset){vader_str}\n"
                        f"- Playtime at review: avg {row['avg_playtime_hrs']}h, "
                        f"median {pt_med:.1f}h, 90th‑pct {pt_p90:.0f}h\n"
                        f"- Top positive keywords: {pos_kw_str}\n"
                        f"- Top negative keywords: {neg_kw_str}"
                    )
                    game_blocks.append(block)

                # ── Overall keyword frequencies (with counts) ─
                pos_texts   = df_[df_["voted_up"] == True]["review_text"].fillna("").tolist()
                neg_texts   = df_[df_["voted_up"] == False]["review_text"].fillna("").tolist()
                pos_kw_all  = extract_keywords(pos_texts, 30)
                neg_kw_all  = extract_keywords(neg_texts, 30)
                pos_kw_str  = ", ".join(f"{w}({c})" for w, c in pos_kw_all)
                neg_kw_str  = ", ".join(f"{w}({c})" for w, c in neg_kw_all)

                # Keywords that appear only in positive OR only in negative (differentiators)
                pos_words = {w for w, _ in pos_kw_all}
                neg_words = {w for w, _ in neg_kw_all}
                only_pos  = ", ".join(w for w, _ in pos_kw_all if w not in neg_words) or "—"
                only_neg  = ", ".join(w for w, _ in neg_kw_all if w not in pos_words) or "—"

                # ── Rich review samples ───────────────────────
                def sample_reviews(pool_df, voted, n=10):
                    sub = pool_df[pool_df["voted_up"] == voted].copy()
                    sub = sub[sub["review_text"].str.len() > 80]
                    # Mix: half most-helpful, half longest (catches detailed but less-voted reviews)
                    top_helpful = sub.nlargest(n // 2, "votes_helpful")
                    top_long    = sub.iloc[sub["review_text"].str.len().argsort()[::-1].values[: n // 2]]
                    combined    = pd.concat([top_helpful, top_long]).drop_duplicates()
                    lines = []
                    for _, r in combined.iterrows():
                        # Include full review up to 500 chars
                        snippet = r["review_text"][:500].replace("\n", " ").strip()
                        hrs     = r.get("author_playtime_hrs", 0)
                        helpful = r.get("votes_helpful", 0)
                        meta    = f"{hrs:.0f}h playtime"
                        if helpful > 0:
                            meta += f", {helpful} found helpful"
                        lines.append(f'  [{r["game_title"]}] ({meta})\n  "{snippet}"')
                    return "\n\n".join(lines) if lines else "  (none)"

                # ── Playtime insight ──────────────────────────
                overall_pt = df_["author_playtime_hrs"]
                pt_insight = (
                    f"Overall playtime at review: avg {overall_pt.mean():.1f}h, "
                    f"median {overall_pt.median():.1f}h. "
                    f"Reviewers with <2h: {(overall_pt < 2).sum():,} "
                    f"({(overall_pt < 2).mean()*100:.0f}%), "
                    f"10h+: {(overall_pt >= 10).sum():,} "
                    f"({(overall_pt >= 10).mean()*100:.0f}%), "
                    f"100h+: {(overall_pt >= 100).sum():,} "
                    f"({(overall_pt >= 100).mean()*100:.0f}%)."
                )

                # ── Sentiment polarity spread ─────────────────
                pos_pcts = sdf_["positive_pct"].tolist()
                spread   = max(pos_pcts) - min(pos_pcts) if len(pos_pcts) > 1 else 0
                best     = sdf_.iloc[0]["game_title"]
                worst    = sdf_.iloc[-1]["game_title"] if len(sdf_) > 1 else best

                focus_map = {
                    "Full overview — all games, all themes": """
Provide a comprehensive analysis covering:
1. Genre-level sentiment summary and what it signals about player satisfaction
2. Rankings and comparisons across all games with concrete reasoning
3. The 3-5 most important themes emerging from positive reviews — what players love and why
4. The 3-5 most important themes emerging from negative reviews — recurring pain points and what they signal
5. Playtime patterns and what they reveal about player engagement and review timing bias
6. Differentiating keywords (words that only appear on one side) and what they reveal
7. Specific actionable insights: what should a developer or publisher take away from this data?
Be specific. Name games. Quote or closely paraphrase actual review language. Avoid vague statements.""",

                    "Sentiment deep-dive — what drives positive vs negative": """
Analyse the specific drivers of positive and negative sentiment:
1. Identify the top 4-5 factors that correlate with positive reviews — go beyond keywords to infer underlying causes
2. Identify the top 4-5 factors that correlate with negative reviews — be specific about what players are reacting to
3. Compare the emotional language in positive vs negative reviews — tone, intensity, specificity
4. Look at playtime distribution for positive vs negative reviewers — does engagement time predict sentiment?
5. Are there keywords that appear in BOTH positive and negative reviews? What does that ambivalence signal?
6. Which games best exemplify each driver? Quote specific review language.
Be analytical. Avoid surface-level observations like "players liked the gameplay." Explain WHY.""",

                    "Competitive comparison — how games stack up against each other": """
Compare all games head-to-head:
1. Create a ranked leaderboard with specific reasoning for each position
2. For the top 2 games: what are they doing right that others aren't?
3. For the bottom 2 games: what specific issues are dragging their scores down?
4. Are there surprising patterns — games with high playtime but low sentiment, or vice versa?
5. Compare keyword profiles between games — what does each game's unique vocabulary reveal?
6. What does the spread between best and worst ({spread:.0f} percentage points) suggest about genre consistency?
Quote reviews. Name games. Be direct about which games have problems and why.""",

                    "Player pain points — what's most criticised and why": """
Deep-dive into negative sentiment:
1. Identify and group all major pain points into 4-6 distinct themes
2. For each theme: how prevalent is it (approximate % of negative reviews), which games are most affected, and quote specific review language
3. Distinguish between fixable issues (bugs, balance, pricing) vs fundamental design problems
4. Look at playtime of negative reviewers — are complaints coming from casual or invested players?
5. Are any pain points unique to specific games, or are they genre-wide problems?
6. What do the negative differentiator keywords reveal that the positive reviews obscure?
7. Prioritise: if a developer read this, what are the top 3 things to fix first?
Be specific and direct. Avoid vague summaries.""",

                    "Player praise — what's most celebrated and why": """
Deep-dive into positive sentiment:
1. Identify and group all major praise themes into 4-6 distinct categories
2. For each theme: how prevalent is it, which games exemplify it best, quote specific review language
3. What aspects of these games are generating genuine enthusiasm vs mild satisfaction?
4. Do high-playtime reviewers praise different things than low-playtime reviewers?
5. What do the positive differentiator keywords reveal about what this genre's audience uniquely values?
6. Which specific design or business decisions (pricing, updates, community, content) are being praised?
7. What does this praise data suggest about unmet needs in the genre that other games could capitalise on?
Be specific. Quote reviews. Identify what makes top performers genuinely stand out.""",
                }

                tone_map = {
                    "Analytical & objective":
                        "Write in a precise, analytical tone. Use data to support every claim. Avoid hedging language like 'may' or 'seems' — if the data shows it, state it confidently.",
                    "Executive summary (brief)":
                        "Write as a tight executive briefing. Use headers and bullets. Lead with the single most important finding. Total length: 350-500 words. Every sentence must earn its place.",
                    "Consumer research style":
                        "Write in a formal consumer research report style with numbered sections, clear headings, and a findings + implications structure for each major point.",
                }

                return f"""You are a senior games market analyst with deep expertise in player psychology and game design critique. You have been given Steam review data collected via the public Steam API.

Your task is to produce a genuinely insightful analysis — not a surface-level summary. Dig into the data. Find patterns. Make arguments. Quote reviews. Be specific about which games have which issues. A good analyst doesn't just describe the data; they interpret it.

═══════════════════════════════════════
DATASET OVERVIEW
═══════════════════════════════════════
Genre / search: {genre_label}
Total reviews: {n_reviews:,} across {n_games} games
Average positive sentiment: {avg_pos:.1f}%
Sentiment spread: {spread:.0f}pp (best: {best}, worst: {worst})
{pt_insight}

═══════════════════════════════════════
PER-GAME DATA (sorted best → worst)
═══════════════════════════════════════
{"".join(chr(10)*2 + b for b in game_blocks)}

═══════════════════════════════════════
CROSS-GAME KEYWORD FREQUENCIES
═══════════════════════════════════════
Positive reviews — top 30 terms (with mention counts):
{pos_kw_str}

Negative reviews — top 30 terms (with mention counts):
{neg_kw_str}

Differentiator keywords (positive only, not in top-30 negative): {only_pos}
Differentiator keywords (negative only, not in top-30 positive): {only_neg}

═══════════════════════════════════════
REVIEW SAMPLES — POSITIVE (most helpful + most detailed)
═══════════════════════════════════════
{sample_reviews(df_, True, 10)}

═══════════════════════════════════════
REVIEW SAMPLES — NEGATIVE (most helpful + most detailed)
═══════════════════════════════════════
{sample_reviews(df_, False, 10)}

═══════════════════════════════════════
YOUR TASK
═══════════════════════════════════════
{focus_map[focus]}

OUTPUT TONE: {tone_map[tone]}

HARD RULES:
- Every claim must reference specific data from this brief (game names, keywords, review quotes, numbers)
- Do not write generic observations that could apply to any game genre
- Do not pad with transitions or summaries — every paragraph must contain new analysis
- Max tokens will be used — write a thorough report, not a brief one
- Use markdown formatting with clear section headers"""

            # ── Generate ───────────────────────────────────────
            if generate_clicked:
                st.session_state.ai_report = ""
                prompt = build_analysis_prompt(df, sdf,
                                               report_focus, report_tone)
                report_placeholder = st.empty()
                status_placeholder = st.empty()
                full_text = ""

                try:
                    client = _anthropic.Anthropic(api_key=st.secrets["CLAUDE_KEY"])
                    status_placeholder.markdown(
                        '<div style="font-size:.78rem;color:var(--muted);">Connecting to Claude…</div>',
                        unsafe_allow_html=True,
                    )
                    with client.messages.stream(
                        model=ai_model,
                        max_tokens=4096,
                        system=(
                            "You are a senior games market analyst. "
                            "Respond only with your analysis report in well-structured markdown. "
                            "Do not add preamble or sign-off."
                        ),
                        messages=[{"role": "user", "content": prompt}],
                    ) as stream:
                        status_placeholder.empty()
                        for delta in stream.text_stream:
                            full_text += delta
                            report_placeholder.markdown(full_text + "▌")

                    report_placeholder.markdown(full_text)
                    st.session_state.ai_report = full_text

                except _anthropic.AuthenticationError:
                    st.error("Invalid API key — check it at console.anthropic.com/settings/keys.")
                except _anthropic.RateLimitError:
                    st.error("Rate limit reached. Wait a moment and try again.")
                except _anthropic.APIConnectionError as e:
                    st.error(f"Could not reach the Anthropic API. Check your internet connection.\nDetail: {e}")
                except _anthropic.APIStatusError as e:
                    st.error(f"Anthropic API error: {e.status_code} — {e.message}")
                except Exception as e:
                    st.error(f"Unexpected error: {type(e).__name__}: {e}")

            elif st.session_state.ai_report:
                st.markdown(st.session_state.ai_report)

            if st.session_state.ai_report:
                st.markdown("<br>", unsafe_allow_html=True)
                dl_col, _ = st.columns([1, 4])
                with dl_col:
                    st.download_button(
                        "Download report (.md)",
                        data=st.session_state.ai_report,
                        file_name=f"steam_analysis_{st.session_state.get('last_genre', 'report').replace(' ', '_')}.md",
                        mime="text/markdown",
                        width='stretch',
                    )

# ─────────────────────────────────────────────────────────────
# EMPTY STATE
# ─────────────────────────────────────────────────────────────

elif not st.session_state.found_games:
    st.markdown("""
    <div class="empty-state">
      <div class="empty-title">NO DATA YET</div>
      <div class="empty-sub">
        Enter a genre above and click <strong style="color:var(--blue);">Search Genre</strong>
        to find games on Steam and pull their reviews.
      </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="footer">
  <div class="footer-brand">SEGA STEAM LENS</div>
  <div class="footer-note">Data sourced from Steam public API · Internal analytics use only</div>
</div>
""", unsafe_allow_html=True)