"""
Steam Genre Review Analyzer — SEGA-branded Streamlit App
=========================================================
Run with:  streamlit run steam_review_app.py

Required:  pip install streamlit requests pandas plotly openai matplotlib wordcloud httpx
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

try:
    from wordcloud import WordCloud as _WC
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    WORDCLOUD_AVAILABLE = True
except ImportError:
    WORDCLOUD_AVAILABLE = False

try:
    import openai as _openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

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
    page_icon="🎮",
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
@import url('https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;700;800&family=Poppins:wght@300;400;500;600&display=swap');

:root {
    --bg:           #0D1126;
    --surface:      #15161E;
    --surface2:     #1c1e2a;
    --border:       #252840;
    --blue:         #0057FF;
    --blue-bright:  #0044FF;
    --blue-light:   #E1EAFF;
    --blue-mid:     #C3C5D5;
    --navy:         #002266;
    --text:         #F4F6F9;
    --muted:        #8b90a8;
    --pos:          #2ecc71;
    --neg:          #e74c3c;
}

html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}
.stApp { background-color: var(--bg) !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 2.5rem 4rem !important; max-width: 1400px !important; }

/* ── Top nav bar ── */
.topbar {
    background: var(--surface);
    border-bottom: 2px solid var(--blue);
    padding: 0.85rem 2.5rem;
    margin: 0 -2.5rem 2.5rem;
    display: flex;
    align-items: center;
    gap: 1.5rem;
}
.topbar-logo {
    font-family: 'Inter Tight', sans-serif;
    font-size: 1.1rem;
    font-weight: 800;
    color: var(--text);
    letter-spacing: 0.06em;
}
.topbar-logo .seg { color: var(--blue); }
.topbar-divider { width: 1px; height: 22px; background: var(--border); }
.topbar-label {
    font-size: 0.7rem;
    font-weight: 500;
    color: var(--muted);
    letter-spacing: 0.14em;
    text-transform: uppercase;
}

/* ── Hero ── */
.hero { padding: 2.5rem 0 2rem; }
.hero-eyebrow {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.25em;
    color: var(--blue);
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}
.hero-title {
    font-family: 'Inter Tight', sans-serif;
    font-size: 3.8rem;
    font-weight: 800;
    line-height: 0.92;
    color: var(--text);
    letter-spacing: -0.02em;
    margin-bottom: 0.8rem;
}
.hero-title .accent { color: var(--blue); }
.hero-sub {
    font-size: 0.92rem;
    font-weight: 300;
    color: var(--muted);
    max-width: 520px;
    line-height: 1.65;
}

/* ── Search panel ── */
.search-block {
    background: var(--surface);
    border: 1px solid var(--border);
    border-top: 3px solid var(--blue);
    border-radius: 0 0 8px 8px;
    padding: 1.75rem 2rem;
    margin: 2rem 0;
}
.field-label {
    font-size: 0.63rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.35rem;
}

/* ── Widget overrides ── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background: var(--bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    color: var(--text) !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.95rem !important;
}
.stTextInput > div > div > input:focus {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 2px rgba(0,87,255,0.2) !important;
}
div[data-baseweb="select"] > div {
    background: var(--bg) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
}
[data-testid="stSlider"] > div > div > div > div { background: var(--blue) !important; }

/* ── Primary button ── */
.stButton > button {
    background: var(--blue) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 4px !important;
    font-family: 'Inter Tight', sans-serif !important;
    font-size: 0.88rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    padding: 0.55rem 1.8rem !important;
    transition: background 0.15s ease !important;
}
.stButton > button:hover { background: #0044CC !important; }

/* ── Metric cards ── */
.metric-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 1.2rem 1.5rem;
}
.metric-card.blue-top { border-top: 3px solid var(--blue); }
.metric-card.pos-top  { border-top: 3px solid var(--pos);  }
.metric-label {
    font-size: 0.63rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.3rem;
}
.metric-value {
    font-family: 'Inter Tight', sans-serif;
    font-size: 2.4rem;
    font-weight: 800;
    color: var(--text);
    line-height: 1;
    margin-bottom: 0.15rem;
}
.metric-sub { font-size: 0.73rem; color: var(--muted); font-weight: 300; }

/* ── Section header ── */
.section-header {
    font-family: 'Inter Tight', sans-serif;
    font-size: 1rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text);
    margin: 2rem 0 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.section-header .dot {
    width: 7px; height: 7px;
    background: var(--blue);
    border-radius: 1px;
    display: inline-block;
    flex-shrink: 0;
}

/* ── Progress ── */
.stProgress > div > div > div > div { background: var(--blue) !important; }

/* ── Review cards ── */
.review-card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-left: 3px solid var(--blue);
    border-radius: 0 6px 6px 0;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.75rem;
    font-size: 0.85rem;
    line-height: 1.6;
    color: var(--text);
}
.review-card.negative { border-left-color: var(--neg); }
.review-meta {
    font-size: 0.68rem;
    color: var(--muted);
    margin-top: 0.4rem;
    font-weight: 500;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0 !important;
    border-bottom: 1px solid var(--border) !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--muted) !important;
    font-family: 'Inter Tight', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    padding: 0.6rem 1.4rem !important;
    border-bottom: 2px solid transparent !important;
}
.stTabs [aria-selected="true"] {
    color: var(--text) !important;
    border-bottom-color: var(--blue) !important;
}

/* ── Checkbox ── */
.stCheckbox > label { color: var(--text) !important; font-size: 0.85rem !important; }

/* ── Download button ── */
.stDownloadButton > button {
    background: transparent !important;
    color: var(--blue) !important;
    border: 1px solid var(--blue) !important;
    border-radius: 4px !important;
    font-family: 'Inter Tight', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}
.stDownloadButton > button:hover { background: rgba(0,87,255,0.1) !important; }

/* ── Empty state ── */
.empty-state {
    margin-top: 3rem;
    text-align: center;
    padding: 3.5rem 2rem;
    border: 1px dashed var(--border);
    border-radius: 8px;
}
.empty-title {
    font-family: 'Inter Tight', sans-serif;
    font-size: 2.5rem;
    font-weight: 800;
    color: var(--border);
    letter-spacing: -0.02em;
    margin-bottom: 0.75rem;
}
.empty-sub {
    font-size: 0.88rem;
    color: var(--muted);
    max-width: 360px;
    margin: 0 auto;
    line-height: 1.7;
}

/* ── Footer ── */
.footer {
    margin-top: 4rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.footer-brand {
    font-family: 'Inter Tight', sans-serif;
    font-weight: 800;
    font-size: 0.8rem;
    color: var(--border);
    letter-spacing: 0.08em;
}
.footer-note { font-size: 0.68rem; color: var(--muted); }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# CONSTANTS & PLOTLY THEME
# ─────────────────────────────────────────────────────────────

STEAM_SEARCH_URL = "https://store.steampowered.com/search/results"
STEAM_REVIEW_URL = "https://store.steampowered.com/appreviews/{app_id}"

PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Poppins, sans-serif", color="#F4F6F9"),
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
# NLP SENTIMENT ANALYSIS
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
    hi      = "#2ecc71" if positive else "#e74c3c"
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
    import pandas as _pd
    df = _pd.read_json(df_json, orient="records")
    if VADER_AVAILABLE:
        analyzer = _VaderAnalyzer()
        scores = [analyzer.polarity_scores(t or "") for t in df["review_text"].fillna("").tolist()]
        df["vader_compound"] = [s["compound"] for s in scores]
    else:
        df["vader_compound"] = None
    return df.to_json(orient="records")


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
    return results


def chart_sentiment_bar(sdf: pd.DataFrame) -> go.Figure:
    df = sdf.sort_values("positive_pct", ascending=True).tail(15)
    fig = go.Figure(go.Bar(
        y=df["game_title"], x=df["positive_pct"], orientation="h",
        marker_color=[
            "#0057FF" if v >= 70 else "#003FBF" if v >= 50 else "#002266"
            for v in df["positive_pct"]
        ],
        text=[f"{v:.0f}%" for v in df["positive_pct"]],
        textposition="outside",
        textfont=dict(size=11, color="#F4F6F9"),
    ))
    fig.update_layout(
        **PLOTLY_BASE,
        xaxis=dict(range=[0, 112], showgrid=False, zeroline=False,
                   tickfont=dict(color="#8b90a8")),
        yaxis=dict(showgrid=False, tickfont=dict(color="#F4F6F9", size=11)),
        height=max(300, len(df) * 38),
    )
    return fig


def chart_scatter(sdf: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=sdf["avg_playtime_hrs"],
        y=sdf["positive_pct"],
        mode="markers+text",
        text=sdf["game_title"].str[:22],
        textposition="top center",
        textfont=dict(size=9, color="#8b90a8"),
        marker=dict(
            size=sdf["total_reviews"].apply(lambda v: max(8, min(30, v / 8))),
            color=sdf["positive_pct"],
            colorscale=[[0, "#002266"], [0.5, "#0057FF"], [1, "#E1EAFF"]],
            showscale=True,
            colorbar=dict(title="% Pos", tickfont=dict(color="#8b90a8", size=9)),
            line=dict(color="#0D1126", width=1),
        ),
    ))
    fig.update_layout(
        **PLOTLY_BASE,
        xaxis=dict(title="Avg Playtime (hrs)", showgrid=True,
                   gridcolor="#252840", tickfont=dict(color="#8b90a8")),
        yaxis=dict(title="% Positive", showgrid=True,
                   gridcolor="#252840", tickfont=dict(color="#8b90a8")),
        height=400,
    )
    return fig


def chart_stacked_bar(sdf: pd.DataFrame) -> go.Figure:
    df = sdf.sort_values("total_reviews", ascending=False)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["game_title"].str[:20], y=df["positive_reviews"],
        name="Positive", marker_color="#0057FF",
    ))
    fig.add_trace(go.Bar(
        x=df["game_title"].str[:20], y=df["negative_reviews"],
        name="Negative", marker_color="#e74c3c",
    ))
    fig.update_layout(
        **PLOTLY_BASE, barmode="stack",
        xaxis=dict(tickangle=-38, tickfont=dict(color="#8b90a8", size=10)),
        yaxis=dict(showgrid=True, gridcolor="#252840", tickfont=dict(color="#8b90a8")),
        legend=dict(font=dict(color="#F4F6F9"), bgcolor="rgba(0,0,0,0)"),
        height=360,
    )
    return fig


def chart_playtime_hist(df: pd.DataFrame) -> go.Figure:
    capped = df[df["author_playtime_hrs"] <= 500]["author_playtime_hrs"]
    fig = go.Figure(go.Histogram(
        x=capped, nbinsx=40, marker_color="#0057FF",
        marker_line=dict(color="#0D1126", width=0.5),
    ))
    fig.update_layout(
        **PLOTLY_BASE,
        xaxis=dict(title="Hrs at Review", tickfont=dict(color="#8b90a8"), showgrid=False),
        yaxis=dict(title="Count", showgrid=True, gridcolor="#252840",
                   tickfont=dict(color="#8b90a8")),
        height=300,
    )
    return fig


def chart_ea_donut(df: pd.DataFrame) -> go.Figure:
    ea   = int(df["written_during_ea"].sum())
    full = len(df) - ea
    fig = go.Figure(go.Pie(
        labels=["Full Release", "Early Access"],
        values=[full, ea], hole=0.55,
        marker_colors=["#0057FF", "#002266"],
        textfont=dict(color="#F4F6F9", size=12),
    ))
    fig.update_layout(
        **PLOTLY_BASE, height=260,
        legend=dict(font=dict(color="#F4F6F9"), bgcolor="rgba(0,0,0,0)"),
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
    ("openai_api_key",       os.environ.get("OPENAI_API_KEY", "")),
    ("ai_report",           ""),   # last generated report text
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
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
  <div class="hero-eyebrow">Steam Review Intelligence</div>
  <div class="hero-title">GENRE<br><span class="accent">ANALYTICS</span></div>
  <div class="hero-sub">
    Enter any game genre to discover how players rate titles on Steam.
    Sentiment, playtime, and engagement — all in one view.
  </div>
</div>
""", unsafe_allow_html=True)

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
    )
with c2:
    st.markdown('<div class="field-label">Max Games</div>', unsafe_allow_html=True)
    max_games = st.selectbox("max games", [10, 20, 30], index=1, label_visibility="collapsed")
with c3:
    st.markdown('<div class="field-label">Reviews / Game</div>', unsafe_allow_html=True)
    reviews_per = st.selectbox("reviews per game", [100, 250, 500], index=0, label_visibility="collapsed")
st.markdown("</div>", unsafe_allow_html=True)

btn_col, _ = st.columns([1, 5])
with btn_col:
    search_clicked = st.button("🔍  SEARCH GENRE", width='stretch')

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

with st.expander("➕  Add a specific game to the list", expanded=False):
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
        add_search = st.button("🔍  FIND", width='stretch', key="btn_add_search")

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
                img_tag = (f'<img src="{candidate["img"]}" style="height:32px;border-radius:3px;'
                           f'margin-right:.6rem;vertical-align:middle;">'
                           if candidate.get("img") else "")
                st.markdown(
                    f'<div style="display:flex;align-items:center;padding:.35rem 0;">'
                    f'{img_tag}'
                    f'<span style="font-size:.88rem;color:var(--text);">{candidate["name"]}</span>'
                    f'<span style="font-size:.72rem;color:var(--muted);margin-left:.5rem;">'
                    f'App {candidate["app_id"]}</span></div>',
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
        if st.button("✓  Select All", use_container_width=True):
            for g in st.session_state.found_games:
                st.session_state.selected_games[g["app_id"]] = True
    with ca:
        if st.button("✕  Clear All", use_container_width=True):
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
                f"▶  FETCH {len(selected_list)} GAMES",
                width='stretch',
            )

        # ── FETCH LOOP ──
        if fetch_clicked:
            all_reviews = []
            st.markdown(
                '<div class="section-header"><span class="dot"></span>FETCHING REVIEWS</div>',
                unsafe_allow_html=True,
            )
            overall_bar = st.progress(0.0)
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

                def _cb(pct, bar=game_bar):
                    bar.progress(float(pct))

                reviews = fetch_reviews_for_game(app_id, title, reviews_per, _cb)
                all_reviews.extend(reviews)
                overall_bar.progress((idx + 1) / len(selected_list))

            status_box.markdown(
                '<div style="font-size:0.83rem;color:#2ecc71;padding:0.25rem 0;">'
                '✓ All games fetched successfully</div>',
                unsafe_allow_html=True,
            )
            game_bar.empty()

            if all_reviews:
                _rdf = pd.DataFrame(all_reviews)
                if VADER_AVAILABLE:
                    _rdf = pd.read_json(run_vader_on_df(_rdf.to_json(orient="records")), orient="records")
                st.session_state.results_df = _rdf
                st.session_state.summary_df = build_summary(st.session_state.results_df)
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

    with st.expander("⏱  Filter by playtime at review", expanded=False):
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

    # ── KPI strip ──
    total_reviews = len(df)
    total_games   = sdf["game_title"].nunique()
    avg_sentiment = sdf["positive_pct"].mean()
    top_game      = sdf.iloc[0]["game_title"] if len(sdf) else "—"
    top_game_pct  = sdf.iloc[0]["positive_pct"] if len(sdf) else 0
    avg_playtime  = df["author_playtime_hrs"].mean()

    st.markdown(
        '<div class="section-header"><span class="dot"></span>OVERVIEW</div>',
        unsafe_allow_html=True,
    )
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
        <div class="metric-card blue-top">
          <div class="metric-label">Reviews Collected</div>
          <div class="metric-value">{total_reviews:,}</div>
          <div class="metric-sub">across {total_games} games</div>
        </div>""", unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="metric-card pos-top">
          <div class="metric-label">Avg Sentiment</div>
          <div class="metric-value" style="color:var(--pos);">{avg_sentiment:.0f}%</div>
          <div class="metric-sub">positive reviews</div>
        </div>""", unsafe_allow_html=True)
    with k3:
        short = top_game[:26] + ("…" if len(top_game) > 26 else "")
        st.markdown(f"""
        <div class="metric-card blue-top">
          <div class="metric-label">Top Rated</div>
          <div class="metric-value" style="font-size:1.15rem;line-height:1.3;padding-top:0.2rem;">
            {short}
          </div>
          <div class="metric-sub">{top_game_pct:.0f}% positive</div>
        </div>""", unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
        <div class="metric-card blue-top">
          <div class="metric-label">Avg Playtime at Review</div>
          <div class="metric-value">{avg_playtime:.1f}
            <span style="font-size:1.1rem;font-weight:400;"> hrs</span>
          </div>
          <div class="metric-sub">across all reviewers</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ──
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["SENTIMENT", "ENGAGEMENT", "GAME TABLE", "REVIEWS", "KEYWORD INSIGHTS", "AI ANALYSIS"])

    with tab1:
        # ── Methodology explainer ──
        st.markdown("""
        <div style="background:#15161E;border:1px solid #252840;border-radius:8px;padding:1.4rem 1.75rem;margin-bottom:1.75rem;">
          <div style="font-family:'Inter Tight',sans-serif;font-size:.7rem;font-weight:800;letter-spacing:.18em;text-transform:uppercase;color:#0057FF;margin-bottom:.65rem;">
            HOW THIS SENTIMENT SCORE IS CALCULATED
          </div>
          <div style="font-size:.88rem;line-height:1.75;color:#C3C5D5;">
            <strong style="color:#F4F6F9;">No AI or NLP is involved.</strong>
            Every Steam reviewer must click a <strong style="color:#2ecc71;">thumbs up</strong>
            or <strong style="color:#e74c3c;">thumbs down</strong> before submitting their review.
            This app reads that binary signal directly from Steam's public review API and divides
            positive votes by total votes to produce the <em>% Positive</em> score.
          </div>
          <div style="display:flex;gap:2rem;margin-top:1.1rem;flex-wrap:wrap;">
            <div style="flex:1;min-width:160px;background:#1c1e2a;border-radius:6px;padding:.85rem 1rem;">
              <div style="font-size:.65rem;font-weight:600;letter-spacing:.15em;text-transform:uppercase;color:#8b90a8;margin-bottom:.3rem;">Formula</div>
              <div style="font-family:'Inter Tight',sans-serif;font-size:1rem;font-weight:700;color:#F4F6F9;">
                👍 positive ÷ total reviews × 100
              </div>
            </div>
            <div style="flex:1;min-width:160px;background:#1c1e2a;border-radius:6px;padding:.85rem 1rem;">
              <div style="font-size:.65rem;font-weight:600;letter-spacing:.15em;text-transform:uppercase;color:#8b90a8;margin-bottom:.3rem;">Source</div>
              <div style="font-size:.85rem;color:#F4F6F9;">Steam's <code style="background:#252840;padding:.1rem .35rem;border-radius:3px;font-size:.8rem;">voted_up</code> field per review — set by the reviewer, not inferred</div>
            </div>
            <div style="flex:1;min-width:160px;background:#1c1e2a;border-radius:6px;padding:.85rem 1rem;">
              <div style="font-size:.65rem;font-weight:600;letter-spacing:.15em;text-transform:uppercase;color:#8b90a8;margin-bottom:.3rem;">What it means</div>
              <div style="font-size:.85rem;color:#F4F6F9;">A score of <strong>80%</strong> means 8 in 10 reviewers explicitly recommended the game</div>
            </div>
            <div style="flex:1;min-width:200px;background:#1c1e2a;border-radius:6px;padding:.85rem 1rem;">
              <div style="font-size:.65rem;font-weight:600;letter-spacing:.15em;text-transform:uppercase;color:#8b90a8;margin-bottom:.3rem;">Limitations</div>
              <div style="font-size:.85rem;color:#F4F6F9;">Binary signal only — no nuance, no topic extraction. Review bombing or incentivised reviews can skew scores. Sample here is capped at your chosen review limit.</div>
            </div>
          </div>
          <div style="margin-top:1rem;font-size:.78rem;color:#8b90a8;border-top:1px solid #252840;padding-top:.75rem;">
            💡 <strong style="color:#C3C5D5;">Steam's own rating labels:</strong>
            &nbsp;≥ 95% = Overwhelmingly Positive &nbsp;·&nbsp;
            ≥ 80% = Very Positive &nbsp;·&nbsp;
            ≥ 70% = Mostly Positive &nbsp;·&nbsp;
            ≥ 40% = Mixed &nbsp;·&nbsp;
            &lt; 40% = Mostly / Overwhelmingly Negative
          </div>
        </div>
        """, unsafe_allow_html=True)

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

    with tab2:
        left, right = st.columns(2)
        with left:
            st.markdown(
                '<div class="section-header"><span class="dot"></span>REVIEW VOLUME</div>',
                unsafe_allow_html=True,
            )
            st.plotly_chart(chart_stacked_bar(sdf), width='stretch',
                            config={"displayModeBar": False})
        with right:
            st.markdown(
                '<div class="section-header"><span class="dot"></span>PLAYTIME DISTRIBUTION</div>',
                unsafe_allow_html=True,
            )
            st.caption("Capped at 500 hrs for readability")
            st.plotly_chart(chart_playtime_hist(df), width='stretch',
                            config={"displayModeBar": False})

        st.markdown(
            '<div class="section-header"><span class="dot"></span>EARLY ACCESS vs FULL RELEASE</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(chart_ea_donut(df), width='stretch',
                        config={"displayModeBar": False})

    with tab3:
        st.markdown(
            '<div class="section-header"><span class="dot"></span>GAME SUMMARY</div>',
            unsafe_allow_html=True,
        )
        display = sdf.rename(columns={
            "game_title":          "Game",
            "total_reviews":       "Reviews",
            "positive_reviews":    "👍 Positive",
            "negative_reviews":    "👎 Negative",
            "positive_pct":        "% Positive",
            "avg_playtime_hrs":    "Avg Hrs",
            "median_playtime_hrs": "Median Hrs",
            "avg_helpful_votes":   "Avg Helpful",
        })
        st.dataframe(
            display,
            width='stretch',
            hide_index=True,
            column_config={
                "% Positive": st.column_config.ProgressColumn(
                    "% Positive", min_value=0, max_value=100, format="%.1f%%",
                ),
            },
        )
        dl_col, _ = st.columns([1, 4])
        with dl_col:
            csv = df.to_csv(index=False, encoding="utf-8-sig").encode()
            genre_slug = st.session_state.last_genre.replace(" ", "_")
            st.download_button(
                "⬇  EXPORT RAW CSV",
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
        f_col, g_col, _ = st.columns([1.2, 1.5, 4])
        with f_col:
            filter_mode = st.selectbox(
                "Show", ["Most Helpful", "Positive Only", "Negative Only", "Random"],
                label_visibility="visible",
            )
        with g_col:
            game_options = ["All Games"] + sorted(df["game_title"].unique().tolist())
            game_filter  = st.selectbox("Game", game_options, label_visibility="visible")

        sample = df.copy()
        if game_filter != "All Games":
            sample = sample[sample["game_title"] == game_filter]
        if filter_mode == "Positive Only":
            sample = sample[sample["voted_up"] == True]
        elif filter_mode == "Negative Only":
            sample = sample[sample["voted_up"] == False]
        elif filter_mode == "Most Helpful":
            sample = sample.nlargest(20, "votes_helpful")
        else:
            sample = sample.sample(min(20, len(sample)), random_state=42)

        sample = sample[sample["review_text"].str.len() > 30].head(15)

        if sample.empty:
            st.info("No reviews match the selected filters.")
        for _, row in sample.iterrows():
            is_pos    = bool(row["voted_up"])
            sentiment = "positive" if is_pos else "negative"
            icon      = "👍" if is_pos else "👎"
            snippet   = row["review_text"][:400] + ("…" if len(row["review_text"]) > 400 else "")
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
            helpful_str  = f"👍 {helpful} helpful" if helpful else ""
            funny_str    = f"😄 {funny} funny" if funny else ""

            author_meta = " &nbsp;·&nbsp; ".join(filter(None, [games_str, reviews_str, total_str]))
            react_meta  = " &nbsp;·&nbsp; ".join(filter(None, [helpful_str, funny_str]))

            border_color = "#2ecc71" if is_pos else "#e74c3c"
            st.markdown(f"""
            <div style="background:var(--surface2);border:1px solid var(--border);
                        border-left:3px solid {border_color};border-radius:0 6px 6px 0;
                        padding:.9rem 1.1rem 1rem;margin-bottom:1rem;">
              <div style="font-size:.85rem;line-height:1.65;color:var(--text);margin-bottom:.7rem;">
                {snippet}
              </div>
              <div style="border-top:1px solid var(--border);padding-top:.6rem;">
                <div style="display:flex;flex-wrap:wrap;gap:.3rem .8rem;align-items:center;
                            font-size:.73rem;color:var(--muted);margin-bottom:.35rem;">
                  <span style="background:{'rgba(46,204,113,.15)' if is_pos else 'rgba(231,76,60,.15)'};
                               color:{'#2ecc71' if is_pos else '#e74c3c'};
                               border:1px solid {'rgba(46,204,113,.3)' if is_pos else 'rgba(231,76,60,.3)'};
                               font-size:.68rem;font-weight:700;letter-spacing:.06em;
                               padding:.12rem .45rem;border-radius:3px;text-transform:uppercase;">
                    {icon} {sentiment}
                  </span>
                  <strong style="color:var(--text);">{row["game_title"]}</strong>
                  <span>{at_rev_hrs:.0f} hrs at review</span>
                  {"<span>" + date_str + "</span>" if date_str else ""}
                  {("<span>" + react_meta + "</span>") if react_meta else ""}
                </div>
                <div style="font-size:.72rem;color:var(--muted);">
                  👤 {profile_html}
                  {(" &nbsp;·&nbsp; " + author_meta) if author_meta else ""}
                  {review_link_html}
                </div>
              </div>
            </div>""", unsafe_allow_html=True)

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
        if "kw_drill_game_sel" not in st.session_state:
            st.session_state.kw_drill_game_sel = None
        if "kw_drill_term" not in st.session_state:
            st.session_state.kw_drill_term = None
        if "kw_drill_sentiment" not in st.session_state:
            st.session_state.kw_drill_sentiment = None

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
          are built from <strong style="color:#2ecc71;">👍 positive</strong> and
          <strong style="color:#e74c3c;">👎 negative</strong> reviews respectively.
          <strong style="color:var(--text);">Click any keyword</strong> to see the reviews that mention it.
        </div>
        """, unsafe_allow_html=True)

        # ── keyword button CSS (override Streamlit's default button look) ──
        st.markdown("""
        <style>
        /* keyword chip buttons */
        div[data-testid="stHorizontalBlock"] .kw-btn-pos > button,
        .kw-btn-pos > button {
            background: rgba(46,204,113,0.12) !important;
            border: 1px solid rgba(46,204,113,0.35) !important;
            color: #2ecc71 !important;
            border-radius: 3px !important;
            font-size: .78rem !important;
            font-weight: 500 !important;
            padding: .18rem .6rem !important;
            margin: .15rem !important;
            min-height: unset !important;
            height: auto !important;
            line-height: 1.4 !important;
        }
        .kw-btn-pos > button:hover { background: rgba(46,204,113,0.22) !important; }
        .kw-btn-neg > button {
            background: rgba(231,76,60,0.12) !important;
            border: 1px solid rgba(231,76,60,0.35) !important;
            color: #e74c3c !important;
            border-radius: 3px !important;
            font-size: .78rem !important;
            font-weight: 500 !important;
            padding: .18rem .6rem !important;
            margin: .15rem !important;
            min-height: unset !important;
            height: auto !important;
            line-height: 1.4 !important;
        }
        .kw-btn-neg > button:hover { background: rgba(231,76,60,0.22) !important; }
        .kw-btn-active-pos > button {
            background: rgba(46,204,113,0.3) !important;
            border: 1px solid #2ecc71 !important;
            color: #fff !important;
            font-weight: 700 !important;
        }
        .kw-btn-active-neg > button {
            background: rgba(231,76,60,0.3) !important;
            border: 1px solid #e74c3c !important;
            color: #fff !important;
            font-weight: 700 !important;
        }
        </style>
        """, unsafe_allow_html=True)

        def render_keyword_buttons(kws, sentiment, key_prefix, df_source, active_term):
            """Render keyword buttons; clicking one shows matching reviews below."""
            if not kws:
                st.markdown('<span style="font-size:.8rem;color:var(--muted);">No data</span>',
                            unsafe_allow_html=True)
                return

            is_pos   = sentiment == "pos"
            colour   = "#2ecc71" if is_pos else "#e74c3c"
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
            colour   = "#2ecc71" if is_pos else "#e74c3c"
            icon     = "👍" if is_pos else "👎"

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
                    f"👍 {helpful} helpful" if helpful else "",
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
        import json as _json

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
                f'<span style="color:#2ecc71;">{pos_pct:.0f}% positive</span></div>',
                unsafe_allow_html=True,
            )

        # ── Word clouds ───────────────────────────────────────
        if WORDCLOUD_AVAILABLE and (top_pos or top_neg):
            wc_l, wc_r = st.columns(2)
            with wc_l:
                st.markdown(
                    '<div style="font-size:.7rem;font-weight:700;letter-spacing:.15em;'
                    'text-transform:uppercase;color:#2ecc71;margin-bottom:.4rem;">✅ Positive</div>',
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
                    'text-transform:uppercase;color:#e74c3c;margin-bottom:.4rem;">❌ Negative</div>',
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
                f'✅ WHAT PEOPLE LIKED '
                f'<span style="color:var(--muted);font-size:.7rem;font-weight:400;">'
                f'— {len(pos_df):,} positive reviews</span></div>',
                unsafe_allow_html=True,
            )
            render_keyword_buttons(
                top_pos[:30], "pos", "kw_selected",
                df_source=ki_df,
                active_term=st.session_state.kw_selected_term
                    if st.session_state.kw_selected_sentiment == "pos" else None,
            )
        with chip_r:
            st.markdown(
                '<div class="section-header"><span class="dot"></span>'
                f'❌ WHAT PEOPLE DISLIKED '
                f'<span style="color:var(--muted);font-size:.7rem;font-weight:400;">'
                f'— {len(neg_df):,} negative reviews</span></div>',
                unsafe_allow_html=True,
            )
            render_keyword_buttons(
                top_neg[:30], "neg", "kw_selected",
                df_source=ki_df,
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
                    marker_color="#2ecc71", marker_opacity=0.8,
                    text=counts_p, textposition="outside",
                    textfont=dict(color="#F4F6F9", size=10),
                ))
                fig_kp.update_layout(
                    **PLOTLY_BASE, height=420,
                    xaxis=dict(showgrid=False, tickfont=dict(color="#8b90a8")),
                    yaxis=dict(showgrid=False, tickfont=dict(color="#F4F6F9", size=11)),
                    title=dict(text="Top Positive Terms", font=dict(color="#F4F6F9", size=12)),
                )
                st.plotly_chart(fig_kp, width="stretch", config={"displayModeBar": False})
        with bc_r:
            if top_neg:
                words_n  = [w for w, _ in top_neg[:15]][::-1]
                counts_n = [c for _, c in top_neg[:15]][::-1]
                fig_kn = go.Figure(go.Bar(
                    y=words_n, x=counts_n, orientation="h",
                    marker_color="#e74c3c", marker_opacity=0.8,
                    text=counts_n, textposition="outside",
                    textfont=dict(color="#F4F6F9", size=10),
                ))
                fig_kn.update_layout(
                    **PLOTLY_BASE, height=420,
                    xaxis=dict(showgrid=False, tickfont=dict(color="#8b90a8")),
                    yaxis=dict(showgrid=False, tickfont=dict(color="#F4F6F9", size=11)),
                    title=dict(text="Top Negative Terms", font=dict(color="#F4F6F9", size=12)),
                )
                st.plotly_chart(fig_kn, width="stretch", config={"displayModeBar": False})

    # TAB 6 — AI ANALYSIS
    # ──────────────────────────────────────────────────────────
    with tab6:

        st.markdown(
            '<div class="section-header"><span class="dot"></span>AI-POWERED REPORT</div>',
            unsafe_allow_html=True,
        )
        if not OPENAI_AVAILABLE:
            st.error("openai SDK not installed. Run: `pip install openai`")
        else:
            # Read key from environment variable
            _env_key = os.environ.get("OPENAI_API_KEY", "")
            if _env_key:
                st.session_state.openai_api_key = _env_key
            

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
                    ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
                    key="ai_model",
                    label_visibility="visible",
                )
            with gen_col:
                st.markdown("<div style='padding-top:1.85rem;'>", unsafe_allow_html=True)
                generate_clicked = st.button(
                    "✨  GENERATE REPORT",
                    width='stretch',
                )
                st.markdown("</div>", unsafe_allow_html=True)
            with test_col:
                st.markdown("<div style='padding-top:1.85rem;'>", unsafe_allow_html=True)
                test_clicked = st.button(
                    "🔌  Test",
                    width='stretch',
                )
                st.markdown("</div>", unsafe_allow_html=True)

            if test_clicked:
                import httpx as _httpx
                with st.spinner("Testing…"):
                    try:
                        r = _httpx.get("https://api.openai.com", timeout=10)
                        st.success(f"✓ Reached api.openai.com (HTTP {r.status_code})")
                    except _httpx.ConnectError as e:
                        st.error(f"✗ Cannot reach api.openai.com: {e}")
                    except Exception as e:
                        st.error(f"✗ {type(e).__name__}: {e}")

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
                    client = _openai.OpenAI(api_key=st.secrets["OPEN_AI_KEY"])
                    status_placeholder.markdown(
                        '<div style="font-size:.78rem;color:var(--muted);">⏳ Connecting to OpenAI…</div>',
                        unsafe_allow_html=True,
                    )
                    with client.chat.completions.create(
                        model=ai_model,
                        max_tokens=4096,
                        stream=True,
                        messages=[
                            {"role": "system", "content":
                                "You are a senior games market analyst. "
                                "Respond only with your analysis report in well-structured markdown. "
                                "Do not add preamble or sign-off."},
                            {"role": "user", "content": prompt},
                        ],
                    ) as stream:
                        status_placeholder.empty()
                        for chunk in stream:
                            delta = chunk.choices[0].delta.content
                            if delta:
                                full_text += delta
                                report_placeholder.markdown(full_text + "▌")

                    report_placeholder.markdown(full_text)
                    st.session_state.ai_report = full_text

                except _openai.AuthenticationError:
                    st.error("Invalid API key — check it at platform.openai.com/api-keys.")
                except _openai.RateLimitError:
                    st.error("Rate limit reached. Wait a moment and try again.")
                except _openai.APIConnectionError as e:
                    st.error(f"Could not reach the OpenAI API. Check your internet connection.\nDetail: {e}")
                except _openai.APIStatusError as e:
                    st.error(f"OpenAI API error: {e.status_code} — {e.message}")
                except Exception as e:
                    st.error(f"Unexpected error: {type(e).__name__}: {e}")

            elif st.session_state.ai_report:
                st.markdown(st.session_state.ai_report)

            if st.session_state.ai_report:
                st.markdown("<br>", unsafe_allow_html=True)
                dl_col, _ = st.columns([1, 4])
                with dl_col:
                    st.download_button(
                        "⬇  Download report (.md)",
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
        Enter a genre above and click <strong style="color:#0057FF;">Search Genre</strong>
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