"""
Reddit Game Sentiment Analyzer — SEGA-branded Streamlit App
============================================================
Run with:  streamlit run reddit_sentiment.py

No Reddit API key needed — uses Reddit's public JSON endpoints.

Required:
    pip install streamlit requests pandas plotly anthropic matplotlib wordcloud vaderSentiment reportlab
"""

import re
import time
import io
import json as _json
from collections import Counter
from datetime import datetime, timezone

import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── Optional deps ──────────────────────────────────────────────
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

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors as _rl_colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Preformatted
    )
    import io as _rl_io
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SEGA Reddit Lens",
    page_icon=":material/forum:",
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
    --orange:       #ff6b35;
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

/* TOP NAV */
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
    background: linear-gradient(90deg, var(--orange) 0%, rgba(255,107,53,0) 55%);
}
.topbar-logo { font-family: 'Inter Tight', sans-serif; font-size: 0.95rem; font-weight: 900; color: var(--text) !important; letter-spacing: 0.12em; text-transform: uppercase; }
.topbar-logo .seg { color: var(--orange); }
.topbar-divider { width: 1px; height: 18px; background: var(--border-hi); flex-shrink: 0; }
.topbar-label { font-size: 0.6rem; font-weight: 600; color: var(--muted) !important; letter-spacing: 0.2em; text-transform: uppercase; }
.topbar-pill { margin-left: auto; background: rgba(255,107,53,0.12); border: 1px solid rgba(255,107,53,0.28); border-radius: 20px; padding: 0.18rem 0.7rem; font-size: 0.58rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--orange) !important; }

/* HERO */
.hero { padding: 1.5rem 0 0.75rem; }
.hero-title { font-family: 'Inter Tight', sans-serif; font-size: 2.4rem; font-weight: 900; line-height: 1.05; color: var(--text) !important; letter-spacing: -0.03em; margin-bottom: 0.5rem; }
.hero-title .accent { color: var(--orange); }
.hero-sub { font-size: 0.87rem; font-weight: 300; color: var(--muted) !important; max-width: 560px; line-height: 1.65; }

/* SEARCH BLOCK */
.search-block {
    background: var(--surface);
    border: 1px solid var(--border);
    border-top: 2px solid var(--orange);
    border-radius: 0 0 10px 10px;
    padding: 1.4rem 1.75rem 1.25rem;
    margin: 1.25rem 0 0;
}
.field-label { font-size: 0.58rem; font-weight: 700; letter-spacing: 0.22em; text-transform: uppercase; color: var(--muted) !important; margin-bottom: 0.3rem; }

/* FORM CONTROLS */
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background: var(--bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    color: var(--text) !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.88rem !important;
    caret-color: var(--orange) !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: var(--orange) !important;
    box-shadow: 0 0 0 3px rgba(255,107,53,0.15) !important;
}
input::placeholder { color: var(--muted) !important; opacity: 0.6 !important; }
.stNumberInput button { background: var(--surface2) !important; color: var(--text) !important; border-color: var(--border) !important; }

/* Selectbox */
div[data-baseweb="select"] > div,
div[data-baseweb="select"] > div > div { background: var(--bg) !important; border-color: var(--border) !important; color: var(--text) !important; }
div[data-baseweb="select"] svg { fill: var(--muted) !important; }
div[data-baseweb="select"] span,
div[data-baseweb="select"] input { color: var(--text) !important; }
div[data-baseweb="menu"],
div[data-baseweb="popover"] { background: var(--surface2) !important; border: 1px solid var(--border-hi) !important; box-shadow: 0 8px 32px rgba(0,0,0,0.5) !important; }
div[data-baseweb="menu"] li,
div[data-baseweb="menu"] [role="option"] { color: var(--text) !important; background: transparent !important; }
div[data-baseweb="menu"] li:hover,
div[data-baseweb="menu"] [aria-selected="true"] { background: var(--surface3) !important; color: var(--text) !important; }

/* Checkbox */
.stCheckbox > label, .stCheckbox > label > span, .stCheckbox label p,
[data-testid="stCheckbox"] span, [data-testid="stCheckbox"] p { color: var(--text) !important; font-size: 0.84rem !important; }

/* BUTTONS */
.stButton > button {
    background: var(--orange) !important;
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
    box-shadow: 0 2px 10px rgba(255,107,53,0.3) !important;
}
.stButton > button:hover { background: #e05520 !important; box-shadow: 0 4px 18px rgba(255,107,53,0.45) !important; transform: translateY(-1px) !important; }
.stButton > button:active { transform: translateY(0px) !important; }

.stDownloadButton > button {
    background: transparent !important;
    color: var(--orange) !important;
    border: 1px solid rgba(255,107,53,0.35) !important;
    border-radius: 6px !important;
    font-family: 'Inter Tight', sans-serif !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    transition: all 0.15s !important;
    box-shadow: none !important;
}
.stDownloadButton > button:hover { background: rgba(255,107,53,0.12) !important; border-color: var(--orange) !important; transform: none !important; }

/* KPI CARDS */
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
.metric-card.orange-top { border-top: 2px solid var(--orange); }
.metric-card.pos-top  { border-top: 2px solid var(--pos);  }
.metric-card.neg-top  { border-top: 2px solid var(--neg);  }
.metric-card:hover { border-color: var(--border-hi); box-shadow: 0 4px 24px rgba(0,0,0,0.3); }
.metric-label { font-size: 0.58rem; font-weight: 700; letter-spacing: 0.22em; text-transform: uppercase; color: var(--muted) !important; margin-bottom: 0.45rem; }
.metric-value { font-family: 'Inter Tight', sans-serif; font-size: 2.1rem; font-weight: 900; color: var(--text) !important; line-height: 1; margin-bottom: 0.25rem; letter-spacing: -0.025em; }
.metric-sub { font-size: 0.69rem; color: var(--muted) !important; font-weight: 300; }

/* SECTION HEADER */
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
.section-header .dot { width: 5px; height: 5px; background: var(--orange); border-radius: 1px; display: inline-block; flex-shrink: 0; box-shadow: 0 0 5px var(--orange); }

/* PROGRESS BARS */
.stProgress > div > div > div > div { background: linear-gradient(90deg, var(--orange) 0%, #ffaa80 100%) !important; border-radius: 4px !important; }

/* TABS */
.stTabs [data-baseweb="tab-list"] { gap: 0 !important; border-bottom: 1px solid var(--border) !important; background: transparent !important; margin-bottom: 0.25rem !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: var(--muted) !important; font-family: 'Inter Tight', sans-serif !important; font-weight: 700 !important; font-size: 0.68rem !important; letter-spacing: 0.16em !important; text-transform: uppercase !important; padding: 0.6rem 1.1rem !important; border-bottom: 2px solid transparent !important; transition: color 0.15s !important; }
.stTabs [data-baseweb="tab"]:hover { color: var(--text-dim) !important; }
.stTabs [aria-selected="true"] { color: var(--text) !important; border-bottom-color: var(--orange) !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 0.5rem !important; }

/* EXPANDERS */
[data-testid="stExpander"], details[data-testid="stExpander"] { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; overflow: hidden; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary span, [data-testid="stExpander"] summary p, [data-testid="stExpander"] summary div { color: var(--text) !important; background: var(--surface) !important; }
[data-testid="stExpanderDetails"], [data-testid="stExpanderDetails"] > div { background: var(--surface) !important; color: var(--text) !important; }

/* DATA TABLE */
[data-testid="stDataFrame"] { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; overflow: hidden; }
[data-testid="stDataFrame"] iframe { background: var(--surface) !important; color: var(--text) !important; }

/* ALERTS */
[data-testid="stAlert"], div[data-baseweb="notification"] { background: var(--surface2) !important; border: 1px solid var(--border-hi) !important; border-radius: 6px !important; color: var(--text) !important; }
[data-testid="stAlert"] p, [data-testid="stAlert"] span { color: var(--text) !important; }

/* SPINNER */
[data-testid="stSpinner"] p { color: var(--text) !important; }

/* POST CARDS */
.post-card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-left: 3px solid var(--orange);
    border-radius: 0 6px 6px 0;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.75rem;
    font-size: 0.84rem;
    line-height: 1.65;
    color: var(--text);
}
.post-card.negative { border-left-color: var(--neg); }
.post-card.positive { border-left-color: var(--pos); }
.post-meta { font-size: 0.67rem; color: var(--muted); margin-top: 0.4rem; font-weight: 500; }

/* SUBREDDIT CHIP */
.sub-chip {
    display: inline-block;
    background: rgba(255,107,53,0.12);
    border: 1px solid rgba(255,107,53,0.3);
    border-radius: 20px;
    padding: 0.15rem 0.65rem;
    font-size: 0.65rem;
    font-weight: 700;
    color: var(--orange) !important;
    letter-spacing: 0.06em;
    margin: 0.15rem;
}

/* EMPTY STATE */
.empty-state { margin-top: 3.5rem; text-align: center; padding: 4rem 2rem; border: 1px dashed var(--border-hi); border-radius: 12px; background: radial-gradient(ellipse at 50% 0%, rgba(255,107,53,0.05) 0%, transparent 65%); }
.empty-title { font-family: 'Inter Tight', sans-serif; font-size: 2rem; font-weight: 900; color: var(--border-hi) !important; letter-spacing: -0.02em; margin-bottom: 0.7rem; }
.empty-sub { font-size: 0.86rem; color: var(--muted) !important; max-width: 380px; margin: 0 auto; line-height: 1.75; }

/* FOOTER */
.footer { margin-top: 4rem; padding-top: 1.25rem; border-top: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
.footer-brand { font-family: 'Inter Tight', sans-serif; font-weight: 900; font-size: 0.7rem; color: var(--border-hi) !important; letter-spacing: 0.14em; text-transform: uppercase; }
.footer-note { font-size: 0.63rem; color: var(--muted) !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────
REDDIT_HEADERS = {
    "User-Agent": "SEGA-Reddit-Lens/1.0 (internal analytics tool)"
}
REDDIT_SEARCH_URL = "https://www.reddit.com/search.json"
REDDIT_SUBREDDIT_SEARCH_URL = "https://www.reddit.com/r/{sub}/search.json"
REDDIT_SUBREDDIT_INFO_URL = "https://www.reddit.com/r/{sub}/about.json"
REDDIT_POST_COMMENTS_URL = "https://www.reddit.com/r/{sub}/comments/{pid}.json"

PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Poppins, sans-serif", color="#eef0fa"),
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis=dict(gridcolor="#232640", zerolinecolor="#232640"),
    yaxis=dict(gridcolor="#232640", zerolinecolor="#232640"),
)

STOP_WORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","with",
    "is","it","this","that","was","are","be","been","has","have","had",
    "i","my","me","we","our","you","your","he","she","they","their","its",
    "not","no","so","if","as","by","from","up","do","did","will","would",
    "can","could","just","also","very","more","some","like","get","got",
    "one","two","what","when","how","who","which","any","all","there",
    "than","then","now","out","about","into","over","re","https","www",
    "com","reddit","r","u","post","comment","edit","deleted","removed",
    "game","games","gaming",
}

AI_MODELS = [
    "claude-opus-4-5",
    "claude-sonnet-4-5",
    "claude-haiku-4-5-20251001",
]

# ─────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────
_defaults = {
    "posts_df": None,
    "subreddit_stats": None,
    "found_subreddits": [],
    "selected_subreddits": [],
    "search_game": "",
    "ai_report": "",
    "ai_chat_history": [],
    "ai_chat_pending": False,
    "claude_key": "",
    "fetch_done": False,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────
# REDDIT HELPERS  (no API key — public JSON)
# ─────────────────────────────────────────────────────────────

def _rget(url, params=None, retries=3, backoff=2.0):
    """GET wrapper with retry + polite rate-limiting."""
    for attempt in range(retries):
        try:
            r = requests.get(
                url,
                headers=REDDIT_HEADERS,
                params=params,
                timeout=12,
            )
            if r.status_code == 429:
                time.sleep(backoff * (attempt + 1))
                continue
            if r.status_code == 200:
                return r.json()
            return None
        except Exception:
            time.sleep(backoff)
    return None


def search_subreddits(game_name: str, limit: int = 8):
    """
    Find subreddits relevant to a game by:
    1. Searching Reddit's subreddit search for the game name.
    2. Doing a general post search and extracting unique subreddit names.
    Returns list of dicts: {name, title, description, subscribers}.
    """
    results = {}

    # ── 1. Subreddit search via /subreddits/search ──────────
    data = _rget(
        "https://www.reddit.com/subreddits/search.json",
        params={"q": game_name, "limit": 15, "include_over_18": "false"},
    )
    if data:
        for child in data.get("data", {}).get("children", []):
            d = child.get("data", {})
            sub = d.get("display_name", "")
            if not sub:
                continue
            results[sub.lower()] = {
                "name": sub,
                "title": d.get("title", sub),
                "description": (d.get("public_description") or d.get("description") or "")[:200],
                "subscribers": d.get("subscribers", 0),
                "url": f"https://www.reddit.com/r/{sub}/",
            }
    time.sleep(0.5)

    # ── 2. Post search — harvest subreddit names ────────────
    data2 = _rget(
        REDDIT_SEARCH_URL,
        params={
            "q": game_name,
            "sort": "relevance",
            "limit": 25,
            "type": "link",
        },
    )
    if data2:
        for child in data2.get("data", {}).get("children", []):
            d = child.get("data", {})
            sub = d.get("subreddit", "")
            if not sub or sub.lower() in results:
                continue
            # fetch subreddit about
            about = _rget(REDDIT_SUBREDDIT_INFO_URL.format(sub=sub))
            if about:
                ad = about.get("data", {})
                results[sub.lower()] = {
                    "name": ad.get("display_name", sub),
                    "title": ad.get("title", sub),
                    "description": (ad.get("public_description") or "")[:200],
                    "subscribers": ad.get("subscribers", 0),
                    "url": f"https://www.reddit.com/r/{sub}/",
                }
            time.sleep(0.35)

    # Sort by subscriber count, return top N
    sorted_subs = sorted(results.values(), key=lambda x: x["subscribers"], reverse=True)
    return sorted_subs[:limit]


def fetch_posts(subreddit: str, query: str, limit: int = 100, sort: str = "relevance"):
    """
    Fetch posts from a subreddit matching a query using Reddit's public
    search endpoint. Returns list of post dicts.
    """
    posts = []
    after = None
    fetched = 0

    while fetched < limit:
        batch = min(100, limit - fetched)
        params = {
            "q": query,
            "sort": sort,
            "limit": batch,
            "restrict_sr": "true",
            "t": "all",
        }
        if after:
            params["after"] = after

        url = REDDIT_SUBREDDIT_SEARCH_URL.format(sub=subreddit)
        data = _rget(url, params=params)
        if not data:
            break

        children = data.get("data", {}).get("children", [])
        if not children:
            break

        for child in children:
            d = child.get("data", {})
            text = (d.get("selftext") or "").strip()
            title = (d.get("title") or "").strip()
            full_text = f"{title}. {text}".strip(". ")
            posts.append({
                "id": d.get("id", ""),
                "subreddit": subreddit,
                "title": title,
                "text": text,
                "full_text": full_text,
                "score": d.get("score", 0),
                "upvote_ratio": d.get("upvote_ratio", 0.5),
                "num_comments": d.get("num_comments", 0),
                "created_utc": d.get("created_utc", 0),
                "author": d.get("author", "[deleted]"),
                "permalink": "https://www.reddit.com" + d.get("permalink", ""),
                "flair": d.get("link_flair_text") or "",
            })

        fetched += len(children)
        after = data.get("data", {}).get("after")
        if not after:
            break
        time.sleep(0.5)

    return posts


def fetch_top_posts(subreddit: str, limit: int = 50, sort: str = "top"):
    """Fetch top/hot/new posts from a subreddit (no query filter)."""
    posts = []
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    data = _rget(url, params={"limit": limit, "t": "all"})
    if not data:
        return posts
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        text = (d.get("selftext") or "").strip()
        title = (d.get("title") or "").strip()
        full_text = f"{title}. {text}".strip(". ")
        posts.append({
            "id": d.get("id", ""),
            "subreddit": subreddit,
            "title": title,
            "text": text,
            "full_text": full_text,
            "score": d.get("score", 0),
            "upvote_ratio": d.get("upvote_ratio", 0.5),
            "num_comments": d.get("num_comments", 0),
            "created_utc": d.get("created_utc", 0),
            "author": d.get("author", "[deleted]"),
            "permalink": "https://www.reddit.com" + d.get("permalink", ""),
            "flair": d.get("link_flair_text") or "",
        })
    return posts

# ─────────────────────────────────────────────────────────────
# SENTIMENT
# ─────────────────────────────────────────────────────────────

def score_sentiment(texts: list[str]):
    """
    Returns list of (label, compound_score) per text.
    Uses VADER if available, else a simple keyword approach.
    """
    if VADER_AVAILABLE:
        analyzer = _VaderAnalyzer()
        results = []
        for t in texts:
            sc = analyzer.polarity_scores(t)
            c = sc["compound"]
            label = "Positive" if c >= 0.05 else ("Negative" if c <= -0.05 else "Neutral")
            results.append((label, round(c, 4)))
        return results
    else:
        # Simple fallback
        POS = {"good","great","love","amazing","best","excellent","fun","enjoy",
               "awesome","fantastic","perfect","brilliant","recommend","happy",
               "pleased","impressive","fantastic","solid","well","nice"}
        NEG = {"bad","terrible","awful","hate","worst","broken","buggy","crash",
               "disappointed","poor","boring","trash","horrible","waste","refund",
               "toxic","frustrating","annoying","lag","glitch","fix","problem"}
        results = []
        for t in texts:
            words = re.findall(r"\b\w+\b", t.lower())
            pos_n = sum(1 for w in words if w in POS)
            neg_n = sum(1 for w in words if w in NEG)
            total = pos_n + neg_n or 1
            score = (pos_n - neg_n) / total
            label = "Positive" if score > 0 else ("Negative" if score < 0 else "Neutral")
            results.append((label, round(score, 4)))
        return results

# ─────────────────────────────────────────────────────────────
# KEYWORD EXTRACTION
# ─────────────────────────────────────────────────────────────

def extract_keywords(texts, n=30):
    words = []
    for t in texts:
        words.extend(re.findall(r"\b[a-z]{3,}\b", t.lower()))
    return Counter(w for w in words if w not in STOP_WORDS).most_common(n)

# ─────────────────────────────────────────────────────────────
# CHART HELPERS
# ─────────────────────────────────────────────────────────────

def sentiment_donut(pos, neu, neg, title="Sentiment"):
    colors = ["#20c65a", "#5a5f82", "#ff3d52"]
    fig = go.Figure(go.Pie(
        labels=["Positive", "Neutral", "Negative"],
        values=[pos, neu, neg],
        hole=0.62,
        marker_colors=colors,
        textinfo="percent",
        hovertemplate="%{label}: %{value} posts (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_BASE,
        showlegend=True,
        legend=dict(orientation="h", y=-0.15, font_size=10),
        annotations=[dict(
            text=f"<b>{pos+neu+neg}</b><br><span style='font-size:10px'>posts</span>",
            x=0.5, y=0.5, font_size=16, showarrow=False,
            font_color="#eef0fa",
        )],
        title=dict(text=title, font_size=12, x=0),
        height=280,
    )
    return fig


def score_histogram(scores, title="Score Distribution"):
    fig = go.Figure(go.Histogram(
        x=scores,
        nbinsx=30,
        marker_color="#ff6b35",
        opacity=0.85,
    ))
    fig.update_layout(
        **PLOTLY_BASE,
        title=dict(text=title, font_size=12),
        xaxis_title="Compound Score",
        yaxis_title="Posts",
        height=260,
    )
    return fig


def bar_chart(labels, values, title="", color="#ff6b35"):
    fig = go.Figure(go.Bar(
        x=values[::-1],
        y=labels[::-1],
        orientation="h",
        marker_color=color,
        opacity=0.88,
    ))
    fig.update_layout(
        **PLOTLY_BASE,
        title=dict(text=title, font_size=12),
        height=max(220, 22 * len(labels)),
        xaxis_title="Frequency",
    )
    return fig


def subreddit_bar(sdf):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Positive %",
        x=sdf["subreddit"],
        y=sdf["positive_pct"],
        marker_color="#20c65a",
        opacity=0.85,
    ))
    fig.add_trace(go.Bar(
        name="Negative %",
        x=sdf["subreddit"],
        y=sdf["negative_pct"],
        marker_color="#ff3d52",
        opacity=0.85,
    ))
    fig.update_layout(
        **PLOTLY_BASE,
        barmode="group",
        title=dict(text="Sentiment by Subreddit", font_size=12),
        height=310,
        xaxis_title="Subreddit",
        yaxis_title="%",
        legend=dict(orientation="h", y=-0.22),
    )
    return fig


def timeline_chart(df):
    df = df.copy()
    df["date"] = pd.to_datetime(df["created_utc"], unit="s").dt.to_period("W").dt.start_time
    grp = df.groupby(["date", "sentiment"]).size().unstack(fill_value=0).reset_index()
    fig = go.Figure()
    color_map = {"Positive": "#20c65a", "Neutral": "#5a5f82", "Negative": "#ff3d52"}
    for col in ["Positive", "Neutral", "Negative"]:
        if col in grp.columns:
            fig.add_trace(go.Scatter(
                x=grp["date"], y=grp[col], name=col,
                mode="lines", stackgroup="one",
                line_color=color_map[col], opacity=0.85,
            ))
    fig.update_layout(
        **PLOTLY_BASE,
        title=dict(text="Post Volume Over Time", font_size=12),
        height=270,
        xaxis_title="Week",
        yaxis_title="Posts",
        legend=dict(orientation="h", y=-0.22),
    )
    return fig

# ─────────────────────────────────────────────────────────────
# WORD CLOUD
# ─────────────────────────────────────────────────────────────

def make_wordcloud(texts, colormap="YlOrRd", bg="#0a0c1a"):
    if not WORDCLOUD_AVAILABLE or not texts:
        return None
    joined = " ".join(texts)
    wc = _WC(
        width=900, height=340,
        background_color=bg,
        colormap=colormap,
        stopwords=STOP_WORDS,
        max_words=120,
        min_font_size=9,
    ).generate(joined)
    fig, ax = plt.subplots(figsize=(9, 3.4), facecolor=bg)
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    plt.tight_layout(pad=0)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=bg)
    plt.close(fig)
    buf.seek(0)
    return buf

# ─────────────────────────────────────────────────────────────
# REPORT EXPORT HELPERS
# ─────────────────────────────────────────────────────────────

def report_to_html(md_text):
    try:
        import markdown as _md_lib
        body = _md_lib.markdown(md_text, extensions=["tables", "fenced_code"])
    except ImportError:
        body = f"<pre>{md_text}</pre>"
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8">
<title>SEGA Reddit Lens Report</title>
<style>
  body{{font-family:Segoe UI,Arial,sans-serif;max-width:860px;margin:40px auto;
       background:#0a0c1a;color:#eef0fa;padding:0 1.5rem;}}
  h1,h2,h3{{color:#ff6b35;}} a{{color:#ff6b35;}}
  pre,code{{background:#141728;padding:.3em .5em;border-radius:4px;font-size:.87em;}}
  table{{border-collapse:collapse;width:100%;}}
  td,th{{border:1px solid #232640;padding:.4em .7em;}}
  th{{background:#1a1e30;}}
</style>
</head>
<body>{body}</body>
</html>"""


def report_to_pdf(md_text):
    if not REPORTLAB_AVAILABLE:
        return None
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    _h1 = ParagraphStyle("h1", parent=styles["Heading1"],
                         fontSize=18, textColor=_rl_colors.HexColor("#ff6b35"),
                         spaceAfter=8, spaceBefore=14)
    _h2 = ParagraphStyle("h2", parent=styles["Heading2"],
                         fontSize=14, textColor=_rl_colors.HexColor("#cc4400"),
                         spaceAfter=6, spaceBefore=10)
    _h3 = ParagraphStyle("h3", parent=styles["Heading3"],
                         fontSize=12, textColor=_rl_colors.HexColor("#333366"),
                         spaceAfter=4, spaceBefore=8)
    _body = ParagraphStyle("body", parent=styles["Normal"],
                           fontSize=10, leading=15, spaceAfter=6)
    _bullet = ParagraphStyle("bullet", parent=_body,
                             leftIndent=16, bulletIndent=6, spaceAfter=3)
    _code_style = ParagraphStyle("code", parent=styles["Code"],
                                 fontSize=8, leading=12,
                                 backColor=_rl_colors.HexColor("#f0f0f8"),
                                 leftIndent=12, rightIndent=12, spaceAfter=6)
    story = []
    in_code = False
    code_lines = []
    for line in md_text.split("\n"):
        if line.startswith("```"):
            if in_code:
                story.append(Preformatted("\n".join(code_lines), _code_style))
                story.append(Spacer(1, 4))
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if line.startswith("### "):
            story.append(Paragraph(line[4:], _h3))
        elif line.startswith("## "):
            story.append(HRFlowable(width="100%", thickness=0.5,
                                    color=_rl_colors.HexColor("#ccccdd"), spaceAfter=2))
            story.append(Paragraph(line[3:], _h2))
        elif line.startswith("# "):
            story.append(Paragraph(line[2:], _h1))
        elif line.startswith("- ") or line.startswith("* "):
            story.append(Paragraph(f"• {line[2:]}", _bullet))
        elif line.strip() in ("---", "***"):
            story.append(HRFlowable(width="100%", thickness=0.5,
                                    color=_rl_colors.HexColor("#ccccdd")))
            story.append(Spacer(1, 4))
        elif line.strip() == "":
            story.append(Spacer(1, 6))
        else:
            story.append(Paragraph(line, _body))
    doc.build(story)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────
# TOP NAV
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="topbar">
  <div class="topbar-logo"><span class="seg">SEGA</span> REDDIT LENS</div>
  <div class="topbar-divider"></div>
  <div class="topbar-label">Community Sentiment Intelligence</div>
  <div class="topbar-pill">NO API KEY REQUIRED</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-title">Reddit <span class="accent">Community</span><br>Sentiment Analyzer</div>
  <div class="hero-sub">
    Search for any game, discover its subreddits, and run sentiment analysis
    on community posts — no Reddit API key needed.
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SIDEBAR — API key + model
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    _key_in = st.text_input(
        "Anthropic API Key (optional)",
        value=st.session_state.claude_key,
        type="password",
        placeholder="sk-ant-…",
        help="Required for AI-generated report. Leave blank for stats-only mode.",
    )
    if _key_in != st.session_state.claude_key:
        st.session_state.claude_key = _key_in

    ai_model = st.selectbox("Claude Model", AI_MODELS, index=1)

    st.markdown("---")
    st.markdown("""
**How it works**

Reddit exposes public JSON endpoints for any page. This app uses:
- `reddit.com/subreddits/search.json` — find subreddits
- `reddit.com/r/{sub}/search.json` — fetch posts
- No OAuth or API key required
- Please limit requests to avoid rate-limiting
""")

# ─────────────────────────────────────────────────────────────
# STEP 1 — GAME SEARCH → SUBREDDIT DISCOVERY
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="search-block">', unsafe_allow_html=True)

st.markdown('<div class="field-label">Step 1 — Game Name</div>', unsafe_allow_html=True)
col_game, col_btn1 = st.columns([4, 1])
with col_game:
    game_input = st.text_input(
        "game_name",
        value=st.session_state.search_game,
        placeholder="e.g. Sonic Frontiers, Persona 5, Like a Dragon…",
        label_visibility="collapsed",
    )
with col_btn1:
    find_subs_btn = st.button("🔍 Find Subreddits", use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

if find_subs_btn and game_input.strip():
    st.session_state.search_game = game_input.strip()
    st.session_state.found_subreddits = []
    st.session_state.selected_subreddits = []
    st.session_state.posts_df = None
    st.session_state.subreddit_stats = None
    st.session_state.fetch_done = False
    st.session_state.ai_report = ""
    st.session_state.ai_chat_history = []

    with st.spinner(f"Searching Reddit for subreddits related to **{game_input.strip()}**…"):
        subs = search_subreddits(game_input.strip(), limit=10)
    st.session_state.found_subreddits = subs

# ─────────────────────────────────────────────────────────────
# STEP 2 — SUBREDDIT SELECTION
# ─────────────────────────────────────────────────────────────
if st.session_state.found_subreddits:
    st.markdown(
        '<div class="section-header"><span class="dot"></span>'
        f'SUBREDDITS FOUND FOR "{st.session_state.search_game.upper()}"</div>',
        unsafe_allow_html=True,
    )

    sub_names = [s["name"] for s in st.session_state.found_subreddits]
    sub_labels = [
        f"r/{s['name']}  ({s['subscribers']:,} members) — {s['description'][:80] or s['title']}"
        for s in st.session_state.found_subreddits
    ]

    selected_labels = st.multiselect(
        "Select subreddits to analyse",
        options=sub_labels,
        default=sub_labels[:3],
        help="Choose one or more subreddits. The top ones are pre-selected.",
    )
    selected_subs = [sub_names[sub_labels.index(l)] for l in selected_labels]
    st.session_state.selected_subreddits = selected_subs

    # ── Fetch config ──────────────────────────────────────────
    st.markdown('<div class="search-block">', unsafe_allow_html=True)
    st.markdown('<div class="field-label">Step 2 — Fetch Settings</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    with c1:
        posts_per_sub = st.number_input("Posts per subreddit", 25, 500, 100, 25)
    with c2:
        sort_mode = st.selectbox("Post sort", ["relevance", "top", "new", "comments"])
    with c3:
        include_top = st.checkbox(
            "Also include top posts (no query filter)",
            value=True,
            help="Fetches top-voted posts from each subreddit in addition to the game-query search.",
        )
    with c4:
        st.markdown("<br>", unsafe_allow_html=True)
        fetch_btn = st.button("📥 Fetch & Analyse", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if fetch_btn and selected_subs:
        all_posts = []
        prog = st.progress(0.0, text="Fetching posts…")
        for i, sub in enumerate(selected_subs):
            prog.progress((i) / len(selected_subs), text=f"Fetching r/{sub}…")
            # Query-filtered search
            posts = fetch_posts(
                sub,
                query=st.session_state.search_game,
                limit=posts_per_sub,
                sort=sort_mode,
            )
            all_posts.extend(posts)
            # Top posts
            if include_top:
                top = fetch_top_posts(sub, limit=50, sort="top")
                all_posts.extend(top)
            time.sleep(0.5)
        prog.progress(1.0, text="Running sentiment analysis…")

        if all_posts:
            df = pd.DataFrame(all_posts)
            # De-duplicate by post id
            df = df.drop_duplicates(subset="id").reset_index(drop=True)
            # Sentiment
            sentiments = score_sentiment(df["full_text"].tolist())
            df["sentiment"] = [s[0] for s in sentiments]
            df["sent_score"] = [s[1] for s in sentiments]
            # Date
            df["date"] = pd.to_datetime(df["created_utc"], unit="s")

            # Per-subreddit stats
            rows = []
            for sub in df["subreddit"].unique():
                sdf = df[df["subreddit"] == sub]
                n = len(sdf)
                pos = (sdf["sentiment"] == "Positive").sum()
                neu = (sdf["sentiment"] == "Neutral").sum()
                neg = (sdf["sentiment"] == "Negative").sum()
                rows.append({
                    "subreddit": sub,
                    "post_count": n,
                    "positive_pct": round(100 * pos / n, 1),
                    "neutral_pct": round(100 * neu / n, 1),
                    "negative_pct": round(100 * neg / n, 1),
                    "avg_score": round(sdf["sent_score"].mean(), 4),
                    "avg_upvotes": round(sdf["score"].mean(), 1),
                    "avg_comments": round(sdf["num_comments"].mean(), 1),
                    "pos_count": int(pos),
                    "neu_count": int(neu),
                    "neg_count": int(neg),
                })
            sub_stats = pd.DataFrame(rows)

            st.session_state.posts_df = df
            st.session_state.subreddit_stats = sub_stats
            st.session_state.fetch_done = True
            st.session_state.ai_report = ""
            st.session_state.ai_chat_history = []
        else:
            st.warning("No posts retrieved. Try a different game name or subreddit selection.")
        prog.empty()

# ─────────────────────────────────────────────────────────────
# RESULTS
# ─────────────────────────────────────────────────────────────
if st.session_state.fetch_done and st.session_state.posts_df is not None:
    df = st.session_state.posts_df
    sdf = st.session_state.subreddit_stats

    total = len(df)
    pos_n = (df["sentiment"] == "Positive").sum()
    neu_n = (df["sentiment"] == "Neutral").sum()
    neg_n = (df["sentiment"] == "Negative").sum()
    avg_score = df["sent_score"].mean()

    # ── KPI CARDS ─────────────────────────────────────────────
    st.markdown(
        '<div class="section-header"><span class="dot"></span>OVERVIEW</div>',
        unsafe_allow_html=True,
    )
    k1, k2, k3, k4, k5 = st.columns(5)
    def _kpi(col, label, value, sub, cls="orange-top"):
        col.markdown(
            f'<div class="metric-card {cls}">'
            f'<div class="metric-label">{label}</div>'
            f'<div class="metric-value">{value}</div>'
            f'<div class="metric-sub">{sub}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    _kpi(k1, "Total Posts", f"{total:,}", f"across {df['subreddit'].nunique()} subreddits")
    _kpi(k2, "Positive", f"{100*pos_n/total:.1f}%", f"{pos_n:,} posts", "pos-top")
    _kpi(k3, "Negative", f"{100*neg_n/total:.1f}%", f"{neg_n:,} posts", "neg-top")
    _kpi(k4, "Avg Sentiment", f"{avg_score:+.3f}", "VADER compound score")
    _kpi(k5, "Avg Upvotes", f"{df['score'].mean():.0f}", f"max {df['score'].max():,.0f}")

    # ── CHARTS ROW 1 ──────────────────────────────────────────
    st.markdown(
        '<div class="section-header"><span class="dot"></span>SENTIMENT BREAKDOWN</div>',
        unsafe_allow_html=True,
    )
    ch1, ch2 = st.columns(2)
    with ch1:
        st.plotly_chart(
            sentiment_donut(pos_n, neu_n, neg_n, "Overall Sentiment"),
            use_container_width=True,
        )
    with ch2:
        st.plotly_chart(
            score_histogram(df["sent_score"].tolist(), "Sentiment Score Distribution"),
            use_container_width=True,
        )

    # Subreddit comparison
    if len(sdf) > 1:
        st.plotly_chart(subreddit_bar(sdf), use_container_width=True)

    # Timeline
    st.plotly_chart(timeline_chart(df), use_container_width=True)

    # ── TABS ──────────────────────────────────────────────────
    st.markdown(
        '<div class="section-header"><span class="dot"></span>DETAILED ANALYSIS</div>',
        unsafe_allow_html=True,
    )
    tab_kw, tab_wc, tab_sub, tab_posts, tab_ai = st.tabs([
        "📊 Keywords",
        "☁ Word Cloud",
        "📋 Per-Subreddit",
        "📝 Posts",
        "🤖 AI Report",
    ])

    # ── KEYWORDS TAB ──────────────────────────────────────────
    with tab_kw:
        ck1, ck2 = st.columns(2)
        with ck1:
            pos_texts = df[df["sentiment"] == "Positive"]["full_text"].tolist()
            pos_kw = extract_keywords(pos_texts)
            if pos_kw:
                labels, vals = zip(*pos_kw)
                st.plotly_chart(
                    bar_chart(list(labels[:20]), list(vals[:20]),
                              title="Top Positive Keywords", color="#20c65a"),
                    use_container_width=True,
                )
        with ck2:
            neg_texts = df[df["sentiment"] == "Negative"]["full_text"].tolist()
            neg_kw = extract_keywords(neg_texts)
            if neg_kw:
                labels, vals = zip(*neg_kw)
                st.plotly_chart(
                    bar_chart(list(labels[:20]), list(vals[:20]),
                              title="Top Negative Keywords", color="#ff3d52"),
                    use_container_width=True,
                )

        # Top posts by engagement
        st.markdown('<div class="section-header"><span class="dot"></span>HIGH-ENGAGEMENT POSTS</div>', unsafe_allow_html=True)
        for _, row in df.nlargest(5, "score").iterrows():
            sent_cls = "positive" if row["sentiment"] == "Positive" else (
                "negative" if row["sentiment"] == "Negative" else "")
            st.markdown(
                f'<div class="post-card {sent_cls}">'
                f'<strong>{row["title"]}</strong><br>'
                f'{row["text"][:280] + "…" if len(row["text"]) > 280 else row["text"]}'
                f'<div class="post-meta">'
                f'r/{row["subreddit"]} · ▲ {row["score"]:,} · '
                f'💬 {row["num_comments"]} · {row["sentiment"]} ({row["sent_score"]:+.3f})'
                f' · <a href="{row["permalink"]}" target="_blank" style="color:var(--orange);">view</a>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

    # ── WORD CLOUD TAB ────────────────────────────────────────
    with tab_wc:
        wc_filter = st.selectbox(
            "Filter by sentiment",
            ["All", "Positive", "Neutral", "Negative"],
            index=0,
        )
        wc_texts = (
            df["full_text"].tolist() if wc_filter == "All"
            else df[df["sentiment"] == wc_filter]["full_text"].tolist()
        )
        cmap = {"All": "YlOrRd", "Positive": "Greens", "Neutral": "Blues", "Negative": "Reds"}
        buf = make_wordcloud(wc_texts, colormap=cmap[wc_filter])
        if buf:
            st.image(buf, use_container_width=True)
        else:
            st.info("Install `wordcloud` and `matplotlib` for word clouds.")

    # ── PER-SUBREDDIT TAB ─────────────────────────────────────
    with tab_sub:
        st.dataframe(
            sdf.sort_values("post_count", ascending=False).reset_index(drop=True),
            use_container_width=True,
        )
        for _, row in sdf.iterrows():
            with st.expander(f"r/{row['subreddit']}  —  {row['post_count']} posts  ·  {row['positive_pct']:.1f}% positive"):
                sub_df = df[df["subreddit"] == row["subreddit"]]
                c_a, c_b = st.columns(2)
                with c_a:
                    st.plotly_chart(
                        sentiment_donut(
                            row["pos_count"], row["neu_count"], row["neg_count"],
                            f"r/{row['subreddit']}",
                        ),
                        use_container_width=True,
                    )
                with c_b:
                    st.markdown(f"""
| Metric | Value |
|--------|-------|
| Avg sentiment score | {row['avg_score']:+.4f} |
| Avg upvotes | {row['avg_upvotes']:,.1f} |
| Avg comments | {row['avg_comments']:,.1f} |
| Positive | {row['pos_count']:,} ({row['positive_pct']:.1f}%) |
| Neutral | {row['neu_count']:,} ({row['neutral_pct']:.1f}%) |
| Negative | {row['neg_count']:,} ({row['negative_pct']:.1f}%) |
""")

    # ── POSTS TAB ─────────────────────────────────────────────
    with tab_posts:
        pf1, pf2, pf3 = st.columns(3)
        with pf1:
            sent_filter = st.selectbox("Sentiment", ["All", "Positive", "Neutral", "Negative"])
        with pf2:
            sub_filter = st.selectbox("Subreddit", ["All"] + sorted(df["subreddit"].unique().tolist()))
        with pf3:
            post_sort = st.selectbox("Sort by", ["score", "num_comments", "sent_score", "date"])

        view_df = df.copy()
        if sent_filter != "All":
            view_df = view_df[view_df["sentiment"] == sent_filter]
        if sub_filter != "All":
            view_df = view_df[view_df["subreddit"] == sub_filter]
        sort_col = "score" if post_sort == "score" else (
            "num_comments" if post_sort == "num_comments" else (
            "sent_score" if post_sort == "sent_score" else "date"))
        view_df = view_df.sort_values(sort_col, ascending=False).head(200)

        for _, row in view_df.head(30).iterrows():
            sent_cls = "positive" if row["sentiment"] == "Positive" else (
                "negative" if row["sentiment"] == "Negative" else "")
            st.markdown(
                f'<div class="post-card {sent_cls}">'
                f'<strong>{row["title"]}</strong><br>'
                f'{row["text"][:300] + "…" if len(row["text"]) > 300 else row["text"] or "<em>Link post</em>"}'
                f'<div class="post-meta">'
                f'r/{row["subreddit"]} · ▲ {row["score"]:,} · 💬 {row["num_comments"]} · '
                f'{row["sentiment"]} ({row["sent_score"]:+.3f}) · '
                f'<a href="{row["permalink"]}" target="_blank" style="color:var(--orange);">view on Reddit</a>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

        st.caption(f"Showing 30 of {len(view_df):,} filtered posts.")
        st.download_button(
            "⬇ Download filtered posts (CSV)",
            data=view_df.to_csv(index=False).encode("utf-8"),
            file_name=f"reddit_{st.session_state.search_game.replace(' ','_')}_posts.csv",
            mime="text/csv",
        )

    # ── AI REPORT TAB ─────────────────────────────────────────
    with tab_ai:
        if not ANTHROPIC_AVAILABLE:
            st.warning("Install `anthropic` to enable AI reports.")
        elif not st.session_state.claude_key:
            st.info("Enter your Anthropic API key in the sidebar to generate an AI report.")
        else:
            if not st.session_state.ai_report:
                gen_btn = st.button("✨ Generate AI Report", key="gen_report")
            else:
                gen_btn = False

            if gen_btn:
                pos_kw_str = ", ".join(f"{w}({c})" for w, c in extract_keywords(
                    df[df["sentiment"]=="Positive"]["full_text"].tolist())[:20])
                neg_kw_str = ", ".join(f"{w}({c})" for w, c in extract_keywords(
                    df[df["sentiment"]=="Negative"]["full_text"].tolist())[:20])
                sub_summary = "\n".join(
                    f"  - r/{r['subreddit']}: {r['post_count']} posts, "
                    f"{r['positive_pct']:.1f}% positive, avg score {r['avg_score']:+.4f}"
                    for _, r in sdf.iterrows()
                )
                sample_pos = df[df["sentiment"]=="Positive"].nlargest(5,"score")["title"].tolist()
                sample_neg = df[df["sentiment"]=="Negative"].nlargest(5,"score")["title"].tolist()

                prompt = f"""You are a senior games market analyst at SEGA. Produce a structured
executive-style sentiment analysis report based on the Reddit community data below.

## Dataset
- Game searched: {st.session_state.search_game}
- Total posts analysed: {total:,}
- Subreddits: {", ".join("r/" + s for s in df["subreddit"].unique())}
- Date range: {df["date"].min().strftime("%Y-%m-%d")} → {df["date"].max().strftime("%Y-%m-%d")}
- Overall: {100*pos_n/total:.1f}% positive, {100*neu_n/total:.1f}% neutral, {100*neg_n/total:.1f}% negative
- Avg VADER score: {avg_score:+.4f}

## Per-Subreddit
{sub_summary}

## Top Positive Keywords
{pos_kw_str}

## Top Negative Keywords
{neg_kw_str}

## Sample High-Scoring Positive Titles
{chr(10).join("- " + t for t in sample_pos)}

## Sample High-Scoring Negative Titles
{chr(10).join("- " + t for t in sample_neg)}

---
Write a comprehensive report with these sections:
1. Executive Summary
2. Overall Sentiment Landscape
3. Subreddit-by-Subreddit Breakdown
4. Key Themes (positive and negative)
5. Community Strengths & Pain Points
6. Competitor / Market Context (inferred from discussions)
7. Actionable Recommendations for the SEGA team
8. Data Quality Notes

Use markdown. Be specific with numbers. Focus on strategic insights."""

                client = _anthropic.Anthropic(api_key=st.session_state.claude_key)
                report_placeholder = st.empty()
                report_text = ""
                try:
                    with client.messages.stream(
                        model=ai_model,
                        max_tokens=4096,
                        messages=[{"role": "user", "content": prompt}],
                    ) as stream:
                        for delta in stream.text_stream:
                            report_text += delta
                            report_placeholder.markdown(report_text + "▌")
                    report_placeholder.markdown(report_text)
                    st.session_state.ai_report = report_text
                except _anthropic.AuthenticationError:
                    st.error("Invalid API key.")
                except _anthropic.RateLimitError:
                    st.error("Rate limit reached. Please wait and try again.")
                except Exception as e:
                    st.error(f"Error: {type(e).__name__}: {e}")

            elif st.session_state.ai_report:
                st.markdown(st.session_state.ai_report)

            if st.session_state.ai_report:
                fname = f"reddit_{st.session_state.search_game.replace(' ','_')}_report"
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(
                    '<div style="font-size:.62rem;font-weight:700;letter-spacing:.18em;'
                    'text-transform:uppercase;color:var(--muted);margin-bottom:.5rem;">'
                    'DOWNLOAD REPORT</div>',
                    unsafe_allow_html=True,
                )
                d1, d2, d3 = st.columns(3)
                with d1:
                    st.download_button(
                        "⬇ Markdown (.md)",
                        data=st.session_state.ai_report,
                        file_name=f"{fname}.md",
                        mime="text/markdown",
                        width="stretch",
                        key="dl_md",
                    )
                with d2:
                    st.download_button(
                        "⬇ HTML (.html)",
                        data=report_to_html(st.session_state.ai_report).encode("utf-8"),
                        file_name=f"{fname}.html",
                        mime="text/html",
                        width="stretch",
                        key="dl_html",
                    )
                with d3:
                    pdf = report_to_pdf(st.session_state.ai_report)
                    if pdf:
                        st.download_button(
                            "⬇ PDF (.pdf)",
                            data=pdf,
                            file_name=f"{fname}.pdf",
                            mime="application/pdf",
                            width="stretch",
                            key="dl_pdf",
                        )
                    else:
                        st.caption("PDF unavailable — install `reportlab`")

                # ── Chat ──────────────────────────────────────
                st.markdown(
                    '<div class="section-header"><span class="dot"></span>'
                    'FOLLOW-UP CHAT</div>',
                    unsafe_allow_html=True,
                )
                st.caption("Ask follow-up questions about the report or dataset.")

                for msg in st.session_state.ai_chat_history:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

                if st.session_state.ai_chat_pending:
                    st.session_state.ai_chat_pending = False
                    system_ctx = (
                        f"You are a senior games market analyst. The user has just received "
                        f"the following Reddit sentiment report for '{st.session_state.search_game}'. "
                        f"Answer follow-up questions concisely, referencing real data.\n\n"
                        f"## Report\n{st.session_state.ai_report[:4000]}"
                    )
                    try:
                        chat_client = _anthropic.Anthropic(api_key=st.session_state.claude_key)
                        with st.chat_message("assistant"):
                            reply_text = ""
                            ph = st.empty()
                            with chat_client.messages.stream(
                                model=ai_model,
                                max_tokens=2048,
                                system=system_ctx,
                                messages=[
                                    {"role": m["role"], "content": m["content"]}
                                    for m in st.session_state.ai_chat_history
                                ],
                            ) as stream:
                                for delta in stream.text_stream:
                                    reply_text += delta
                                    ph.markdown(reply_text + "▌")
                            ph.markdown(reply_text)
                        st.session_state.ai_chat_history.append(
                            {"role": "assistant", "content": reply_text}
                        )
                    except Exception as e:
                        st.error(f"Chat error: {e}")

                user_msg = st.chat_input("Ask a follow-up question…", key="ai_chat_input")
                if user_msg:
                    st.session_state.ai_chat_history.append({"role": "user", "content": user_msg})
                    st.session_state.ai_chat_pending = True
                    st.rerun()

                if st.session_state.ai_chat_history:
                    if st.button("Clear chat", key="clear_chat"):
                        st.session_state.ai_chat_history = []
                        st.session_state.ai_chat_pending = False
                        st.rerun()

# ─────────────────────────────────────────────────────────────
# EMPTY STATE
# ─────────────────────────────────────────────────────────────
elif not st.session_state.found_subreddits:
    st.markdown("""
<div class="empty-state">
  <div class="empty-title">NO DATA YET</div>
  <div class="empty-sub">
    Enter a game name above and click <strong style="color:var(--orange);">Find Subreddits</strong>
    to discover relevant communities and analyse their sentiment.
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
  <div class="footer-brand">SEGA REDDIT LENS</div>
  <div class="footer-note">Data sourced from Reddit public JSON API · No API key required · Internal analytics use only</div>
</div>
""", unsafe_allow_html=True)