"""
Reddit Game Sentiment Analyzer — SEGA-branded Streamlit App
============================================================
Run with:  streamlit run reddit_sentiment.py
Requires:  pip install -r requirements.txt
"""

import re, time, io
from collections import Counter

import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── Optional deps ─────────────────────────────────────────────
try:
    from wordcloud import WordCloud as _WC
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    WORDCLOUD_OK = True
except ImportError:
    WORDCLOUD_OK = False

try:
    import anthropic as _anthropic
    ANTHROPIC_OK = True
except ImportError:
    ANTHROPIC_OK = False

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer as _Vader
    VADER_OK = True
except ImportError:
    VADER_OK = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors as _rlc
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Preformatted
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="SEGA Reddit Lens", page_icon=":material/forum:",
                   layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;700;800;900&family=Poppins:wght@300;400;500;600&display=swap');
:root,html[data-theme="light"],html[data-theme="dark"],[data-theme="light"],[data-theme="dark"]{
  color-scheme:dark!important;
  --bg:#0a0c1a;--surface:#0f1120;--surface2:#141728;--surface3:#1a1e30;
  --border:#232640;--border-hi:#323760;
  --blue:#4080ff;--blue-lo:#1a3acc;
  --blue-glow:rgba(64,128,255,.16);--blue-glow-hi:rgba(64,128,255,.32);
  --text:#eef0fa;--text-dim:#b8bcd4;--muted:#5a5f82;
  --pos:#20c65a;--pos-dim:rgba(32,198,90,.14);
  --neg:#ff3d52;--neg-dim:rgba(255,61,82,.14);
}
html,body{background:var(--bg)!important;color:var(--text)!important;color-scheme:dark!important;}
.stApp,.stApp>div,section[data-testid="stAppViewContainer"],
section[data-testid="stAppViewContainer"]>div,div[data-testid="stMain"],
div[data-testid="stVerticalBlock"],div[data-testid="stHorizontalBlock"],
.main .block-container,.block-container{background-color:var(--bg)!important;color:var(--text)!important;}
*,*::before,*::after{font-family:'Poppins',sans-serif;box-sizing:border-box;}
p,span,div,li,td,th,label,h1,h2,h3,h4,h5,h6,
.stMarkdown,.stMarkdown p,.stMarkdown span,
[data-testid="stMarkdownContainer"],[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span,[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] strong,[data-testid="stMarkdownContainer"] em,
[class*="css"]{color:var(--text)!important;}
.stCaption,[data-testid="stCaptionContainer"] p{color:var(--muted)!important;}
code{background:var(--surface3)!important;color:var(--blue)!important;padding:.1em .4em;border-radius:3px;}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding:0 2.5rem 4rem!important;max-width:1440px!important;}
::-webkit-scrollbar{width:5px;height:5px;}
::-webkit-scrollbar-thumb{background:var(--border-hi);border-radius:4px;}

.topbar{background:var(--surface);border-bottom:1px solid var(--border);
  padding:.8rem 2.5rem;margin:0 -2.5rem 1.75rem;display:flex;align-items:center;gap:1.25rem;position:relative;}
.topbar::after{content:'';position:absolute;bottom:-1px;left:0;right:0;height:1px;
  background:linear-gradient(90deg,var(--blue) 0%,rgba(64,128,255,0) 55%);}
.topbar-logo{font-family:'Inter Tight',sans-serif;font-size:.95rem;font-weight:900;
  color:var(--text)!important;letter-spacing:.12em;text-transform:uppercase;}
.topbar-logo .seg{color:var(--blue);}
.topbar-div{width:1px;height:18px;background:var(--border-hi);flex-shrink:0;}
.topbar-label{font-size:.6rem;font-weight:600;color:var(--muted)!important;letter-spacing:.2em;text-transform:uppercase;}
.topbar-pill{margin-left:auto;background:var(--blue-glow);border:1px solid rgba(64,128,255,.28);
  border-radius:20px;padding:.18rem .7rem;font-size:.58rem;font-weight:700;
  letter-spacing:.14em;text-transform:uppercase;color:var(--blue)!important;}

.hero{padding:1.5rem 0 .75rem;}
.hero-title{font-family:'Inter Tight',sans-serif;font-size:2.4rem;font-weight:900;
  line-height:1.05;color:var(--text)!important;letter-spacing:-.03em;margin-bottom:.5rem;}
.hero-title .accent{color:var(--blue);}
.hero-sub{font-size:.87rem;font-weight:300;color:var(--muted)!important;max-width:560px;line-height:1.65;}

.search-block{background:var(--surface);border:1px solid var(--border);
  border-top:2px solid var(--blue);border-radius:0 0 10px 10px;padding:1.4rem 1.75rem 1.25rem;margin:.75rem 0 0;}
.field-label{font-size:.58rem;font-weight:700;letter-spacing:.22em;text-transform:uppercase;
  color:var(--muted)!important;margin-bottom:.3rem;}

.stTextInput>div>div>input,.stNumberInput>div>div>input{
  background:var(--bg)!important;border:1px solid var(--border)!important;border-radius:6px!important;
  color:var(--text)!important;font-family:'Poppins',sans-serif!important;font-size:.88rem!important;caret-color:var(--blue)!important;}
.stTextInput>div>div>input:focus,.stNumberInput>div>div>input:focus{
  border-color:var(--blue)!important;box-shadow:0 0 0 3px var(--blue-glow)!important;}
input::placeholder{color:var(--muted)!important;opacity:.6!important;}
.stNumberInput button{background:var(--surface2)!important;color:var(--text)!important;border-color:var(--border)!important;}
textarea{background:var(--bg)!important;border:1px solid var(--border)!important;border-radius:6px!important;
  color:var(--text)!important;font-family:'Poppins',sans-serif!important;font-size:.85rem!important;}
textarea:focus{border-color:var(--blue)!important;box-shadow:0 0 0 3px var(--blue-glow)!important;}

div[data-baseweb="select"]>div{background:var(--bg)!important;border-color:var(--border)!important;color:var(--text)!important;}
div[data-baseweb="select"] svg{fill:var(--muted)!important;}
div[data-baseweb="select"] span,div[data-baseweb="select"] input{color:var(--text)!important;}
div[data-baseweb="menu"],div[data-baseweb="popover"]{background:var(--surface2)!important;
  border:1px solid var(--border-hi)!important;box-shadow:0 8px 32px rgba(0,0,0,.5)!important;}
div[data-baseweb="menu"] li{color:var(--text)!important;background:transparent!important;}
div[data-baseweb="menu"] li:hover,[aria-selected="true"]{background:var(--surface3)!important;}
.stCheckbox>label,.stCheckbox>label>span,[data-testid="stCheckbox"] span{color:var(--text)!important;font-size:.84rem!important;}

.stButton>button{background:var(--blue)!important;color:#fff!important;border:none!important;
  border-radius:6px!important;font-family:'Inter Tight',sans-serif!important;
  font-size:.78rem!important;font-weight:800!important;letter-spacing:.12em!important;
  text-transform:uppercase!important;padding:.5rem 1.5rem!important;
  box-shadow:0 2px 10px rgba(64,128,255,.3)!important;transition:all .15s!important;}
.stButton>button:hover{background:var(--blue-lo)!important;box-shadow:0 4px 18px rgba(64,128,255,.45)!important;transform:translateY(-1px)!important;}
.stButton>button:disabled{background:var(--surface3)!important;color:var(--muted)!important;box-shadow:none!important;}
.stDownloadButton>button{background:transparent!important;color:var(--blue)!important;
  border:1px solid rgba(64,128,255,.35)!important;border-radius:6px!important;
  font-family:'Inter Tight',sans-serif!important;font-size:.72rem!important;font-weight:700!important;
  letter-spacing:.1em!important;text-transform:uppercase!important;transition:all .15s!important;}
.stDownloadButton>button:hover{background:var(--blue-glow)!important;border-color:var(--blue)!important;}

.metric-card{background:var(--surface);border:1px solid var(--border);border-radius:8px;
  padding:1.2rem 1.4rem;overflow:hidden;transition:border-color .2s,box-shadow .2s;height:100%;}
.metric-card.bt{border-top:2px solid var(--blue);}
.metric-card.pt{border-top:2px solid var(--pos);}
.metric-card.nt{border-top:2px solid var(--neg);}
.metric-card:hover{border-color:var(--border-hi);box-shadow:0 4px 24px rgba(0,0,0,.3);}
.metric-label{font-size:.58rem;font-weight:700;letter-spacing:.22em;text-transform:uppercase;color:var(--muted)!important;margin-bottom:.45rem;}
.metric-value{font-family:'Inter Tight',sans-serif;font-size:2.1rem;font-weight:900;color:var(--text)!important;line-height:1;margin-bottom:.25rem;}
.metric-sub{font-size:.69rem;color:var(--muted)!important;font-weight:300;}

.sh{font-family:'Inter Tight',sans-serif;font-size:.68rem;font-weight:800;letter-spacing:.24em;
  text-transform:uppercase;color:var(--text-dim)!important;margin:1.75rem 0 .9rem;
  padding-bottom:.55rem;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:.55rem;}
.sh .dot{width:5px;height:5px;background:var(--blue);border-radius:1px;display:inline-block;box-shadow:0 0 6px var(--blue);}

.stProgress>div>div>div>div{background:linear-gradient(90deg,var(--blue) 0%,#80aaff 100%)!important;border-radius:4px!important;}

.stTabs [data-baseweb="tab-list"]{gap:0!important;border-bottom:1px solid var(--border)!important;background:transparent!important;}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--muted)!important;
  font-family:'Inter Tight',sans-serif!important;font-weight:700!important;font-size:.68rem!important;
  letter-spacing:.16em!important;text-transform:uppercase!important;padding:.6rem 1.1rem!important;
  border-bottom:2px solid transparent!important;transition:color .15s!important;}
.stTabs [aria-selected="true"]{color:var(--text)!important;border-bottom-color:var(--blue)!important;}

[data-testid="stExpander"]{background:var(--surface)!important;border:1px solid var(--border)!important;border-radius:8px!important;}
[data-testid="stExpander"] summary,[data-testid="stExpander"] summary span{color:var(--text)!important;background:var(--surface)!important;}
[data-testid="stExpanderDetails"],[data-testid="stExpanderDetails"]>div{background:var(--surface)!important;}
[data-testid="stDataFrame"]{background:var(--surface)!important;border:1px solid var(--border)!important;border-radius:8px!important;}
[data-testid="stAlert"]{background:var(--surface2)!important;border:1px solid var(--border-hi)!important;border-radius:6px!important;}
[data-testid="stAlert"] p,[data-testid="stAlert"] span{color:var(--text)!important;}
[data-testid="stSpinner"] p{color:var(--text)!important;}

.post-card{background:var(--surface2);border:1px solid var(--border);
  border-left:3px solid var(--blue);border-radius:0 6px 6px 0;
  padding:.9rem 1.1rem;margin-bottom:.75rem;font-size:.84rem;line-height:1.65;}
.post-card.pos{border-left-color:var(--pos);}
.post-card.neg{border-left-color:var(--neg);}
.post-meta{font-size:.67rem;color:var(--muted);margin-top:.4rem;}

.sub-tag{display:inline-block;background:var(--blue-glow);border:1px solid rgba(64,128,255,.35);
  border-radius:4px;padding:.1rem .5rem;font-size:.68rem;font-weight:600;
  color:var(--blue)!important;margin:.15rem .2rem;}

.chip-row{display:flex;gap:.65rem;margin:.4rem 0 1.1rem;flex-wrap:wrap;}
.genre-chip>button{
  background:var(--surface)!important;color:var(--text-dim)!important;
  border:1px solid var(--border)!important;border-radius:6px!important;
  font-family:'Inter Tight',sans-serif!important;font-size:.78rem!important;
  font-weight:700!important;letter-spacing:.1em!important;text-transform:uppercase!important;
  padding:.4rem 1.1rem!important;min-height:unset!important;height:auto!important;
  line-height:1.5!important;transition:border-color .15s,color .15s,background .15s!important;
  box-shadow:none!important;width:100%!important;}
.genre-chip>button:hover{
  background:var(--surface2)!important;border-color:var(--blue)!important;
  color:var(--text)!important;transform:none!important;box-shadow:none!important;}

.empty-state{margin-top:3.5rem;text-align:center;padding:4rem 2rem;
  border:1px dashed var(--border-hi);border-radius:12px;
  background:radial-gradient(ellipse at 50% 0%,rgba(64,128,255,.05) 0%,transparent 65%);}
.empty-title{font-family:'Inter Tight',sans-serif;font-size:2rem;font-weight:900;
  color:var(--border-hi)!important;letter-spacing:-.02em;margin-bottom:.7rem;}
.empty-sub{font-size:.86rem;color:var(--muted)!important;max-width:420px;margin:0 auto;line-height:1.75;}

.footer{margin-top:4rem;padding-top:1.25rem;border-top:1px solid var(--border);
  display:flex;justify-content:space-between;align-items:center;}
.footer-brand{font-family:'Inter Tight',sans-serif;font-weight:900;font-size:.7rem;
  color:var(--border-hi)!important;letter-spacing:.14em;text-transform:uppercase;}
.footer-note{font-size:.63rem;color:var(--muted)!important;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────
PB = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Poppins, sans-serif", color="#eef0fa"),
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis=dict(gridcolor="#232640", zerolinecolor="#232640"),
    yaxis=dict(gridcolor="#232640", zerolinecolor="#232640"),
)

SW = {
    "the","a","an","and","or","but","in","on","at","to","for","of","with","is","it",
    "this","that","was","are","be","been","has","have","had","i","my","me","we","our",
    "you","your","he","she","they","their","its","not","no","so","if","as","by","from",
    "up","do","did","will","would","can","could","just","also","very","more","some",
    "like","get","got","one","two","what","when","how","who","which","any","all","there",
    "than","then","now","out","about","into","over","re","https","www","com","reddit",
    "r","u","post","comment","edit","deleted","removed","game","games","gaming","amp",
}

MODELS = ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5-20251001"]

# ── Curated genre → subreddit map ────────────────────────────
GENRE_SUBS: dict[str, list[str]] = {
    "fighting":       ["Tekken", "StreetFighter", "MortalKombat", "Kappa", "SF6"],
    "soulslike":      ["Eldenring", "darksouls3", "bloodborne", "sekiro", "DarkSouls2"],
    "rpg":            ["JRPG", "Persona5", "dragonquest", "finalfantasy", "tales"],
    "battle royale":  ["FortNiteBR", "apexlegends", "PUBGConsole", "CODWarzone"],
    "fps":            ["halo", "Overwatch", "Rainbow6", "battlefield", "valorant"],
    "open world":     ["GTA", "thewitcher3", "skyrim", "reddeadredemption", "cyberpunkgame"],
    "mmo":            ["ffxiv", "wow", "lostarkgame", "Guildwars2", "newworldgame"],
    "strategy":       ["totalwar", "civ", "CompanyOfHeroes", "aoe2", "Stellaris"],
    "roguelike":      ["HadesTheGame", "deadcells", "slay_the_spire", "EnterTheGungeon"],
    "platformer":     ["Mario", "SonicTheHedgehog", "Celeste", "metroidvania"],
    "racing":         ["granturismo", "forza", "F1Game", "iRacing", "NeedForSpeed"],
    "horror":         ["residentevil", "silenthill", "deadbydaylight", "outlast"],
}

QUICK_GENRES = list(GENRE_SUBS.keys())

# ─────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────
# ── Secrets (set in .streamlit/secrets.toml) ──────────────────────────────
_SECRET_KEY: str = st.secrets.get("CLAUDE_KEY", "")

for _k, _v in {
    "genre_subs":    [],      # subreddits loaded from genre chip
    "active_genre":  "",      # currently selected genre label
    "manual_subs":   [],      # list[dict] — manually added
    "posts_df":      None,
    "sub_stats":     None,
    "fetch_done":    False,
    "ai_report":     "",
    "chat_history":  [],
    "chat_pending":  False,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─────────────────────────────────────────────────────────────
# REDDIT HELPERS
# Uses OAuth2 client-credentials when REDDIT_CLIENT_ID is set
# (required on cloud hosts — Reddit blocks AWS/GCP IPs otherwise),
# falls back to bare requests for local use without credentials.
# ─────────────────────────────────────────────────────────────

_REDDIT_ID     = st.secrets.get("REDDIT_CLIENT_ID", "")
_REDDIT_SECRET = st.secrets.get("REDDIT_CLIENT_SECRET", "")
_REDDIT_UA     = st.secrets.get("REDDIT_USER_AGENT",
                                "SEGA-Reddit-Lens/2.0 (by /u/sega_analytics)")

@st.cache_resource
def _get_oauth_token() -> tuple[str | None, str | None]:
    """Fetch a client-credentials bearer token. Cached per process."""
    if not _REDDIT_ID or not _REDDIT_SECRET:
        return None, None   # no creds — caller will try unauthenticated
    try:
        r = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(_REDDIT_ID, _REDDIT_SECRET),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": _REDDIT_UA},
            timeout=12,
        )
        if r.status_code == 200:
            return r.json().get("access_token"), None
        return None, f"Token request failed: HTTP {r.status_code} — {r.text[:120]}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _rget(url: str, params=None, retries=3, backoff=1.5):
    """
    GET a Reddit endpoint, preferring OAuth when credentials are available.
    - With credentials : hits oauth.reddit.com with a bearer token (works on cloud)
    - Without credentials : bare request to www.reddit.com (works locally only)
    Returns (data_dict, None) on success, (None, error_str) on failure.
    """
    token, token_err = _get_oauth_token()

    if token:
        # Authenticated path — rewrite URL to oauth.reddit.com
        url = url.replace("https://www.reddit.com", "https://oauth.reddit.com")
        headers = {"Authorization": f"bearer {token}", "User-Agent": _REDDIT_UA}
    elif token_err:
        return None, token_err
    else:
        # No creds configured — bare request (local only)
        headers = {}

    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=14)
            if r.status_code == 429:
                time.sleep(backoff * 2 ** attempt)
                continue
            if r.status_code == 401:
                st.cache_resource.clear()
                return None, "OAuth token expired — please reload the page"
            if r.status_code == 200:
                return r.json(), None
            last_err = f"HTTP {r.status_code}"
            if r.status_code >= 500:
                time.sleep(backoff)
                continue
            return None, last_err
        except requests.exceptions.ConnectionError as e:
            last_err = f"Connection error: {e}"
            time.sleep(backoff)
        except requests.exceptions.Timeout:
            last_err = "Request timed out"
            time.sleep(backoff)
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(backoff)
    return None, last_err

def _sub_dict(d: dict) -> dict:
    name = d.get("display_name", "")
    return {
        "name": name,
        "title": d.get("title", name),
        "description": (d.get("public_description") or d.get("description") or "")[:180],
        "subscribers": d.get("subscribers", 0),
    }

def search_subreddits(game: str, limit=10) -> tuple[list[dict], str | None]:
    """
    Two-strategy subreddit discovery via public JSON — no API key needed.
    Returns (results, error_message). error_message is None on success.
    """
    seen: dict[str, dict] = {}
    first_err = None

    # Strategy 1 — /subreddits/search
    data, err = _rget("https://www.reddit.com/subreddits/search.json",
                      params={"q": game, "limit": 20, "include_over_18": "false"})
    if err and not first_err:
        first_err = err
    if data:
        for c in data.get("data", {}).get("children", []):
            d = c.get("data", {}); name = d.get("display_name", "")
            if name: seen[name.lower()] = _sub_dict(d)
    time.sleep(0.6)

    # Strategy 2 — post search, harvest subreddit names not yet seen
    data2, err2 = _rget("https://www.reddit.com/search.json",
                        params={"q": game, "sort": "relevance", "limit": 25, "type": "link"})
    if err2 and not first_err:
        first_err = err2
    new_names = []
    if data2:
        for c in data2.get("data", {}).get("children", []):
            sub = c.get("data", {}).get("subreddit", "")
            if sub and sub.lower() not in seen:
                new_names.append(sub)
    time.sleep(0.4)

    for sub in new_names[:10]:
        about, _ = _rget(f"https://www.reddit.com/r/{sub}/about.json")
        if about:
            d = about.get("data", {})
            seen[sub.lower()] = _sub_dict(d)
        time.sleep(0.3)

    results = sorted(seen.values(), key=lambda x: x["subscribers"], reverse=True)[:limit]
    # Only surface an error if we got nothing back at all
    return results, (first_err if not results else None)

def validate_subreddit(name: str) -> tuple[dict | None, str | None]:
    """
    Return (metadata_dict, None) on success,
           (None, error_str) on request failure,
           (None, None) if the subreddit genuinely doesn't exist / is private.
    """
    name = name.strip().lstrip("r/").lstrip("/")
    if not name:
        return None, None
    about, err = _rget(f"https://www.reddit.com/r/{name}/about.json")
    if err:
        return None, err          # network / HTTP error — not the subreddit's fault
    if not about:
        return None, None         # 200 but empty — truly missing
    d = about.get("data", {})
    if not d.get("display_name"):
        return None, None
    return _sub_dict(d), None

def _mk_post(d: dict, sub: str) -> dict:
    title = (d.get("title") or "").strip()
    text  = (d.get("selftext") or "").strip()
    return {
        "id": d.get("id",""), "subreddit": sub, "title": title, "text": text,
        "full_text": f"{title}. {text}".strip(". "),
        "score": d.get("score", 0), "upvote_ratio": d.get("upvote_ratio", 0.5),
        "num_comments": d.get("num_comments", 0), "created_utc": d.get("created_utc", 0),
        "author": d.get("author","[deleted]"),
        "permalink": "https://www.reddit.com" + d.get("permalink",""),
        "flair": d.get("link_flair_text") or "",
    }

# Reddit's API returns max 100 items per page.
# We paginate using the `after` cursor and sleep between pages to stay
# well within the 60-req/min OAuth rate limit (or ~10 req/min unauthenticated).
_PAGE_SLEEP   = 2.0   # seconds between paginated requests (same endpoint)
_SUB_SLEEP    = 3.0   # seconds between subreddits
_COMMENT_SLEEP = 1.5  # seconds between comment fetches


def fetch_top(sub: str, limit=100, time_filter="all") -> list[dict]:
    """Paginate /top until we have `limit` posts or run out."""
    posts, after, fetched = [], None, 0
    while fetched < limit:
        params = {"limit": min(100, limit - fetched), "t": time_filter}
        if after:
            params["after"] = after
        data, err = _rget(f"https://www.reddit.com/r/{sub}/top.json", params=params)
        if err or not data:
            break
        children = data.get("data", {}).get("children", [])
        if not children:
            break
        posts  += [_mk_post(c.get("data", {}), sub) for c in children]
        fetched += len(children)
        after   = data.get("data", {}).get("after")
        if not after:
            break
        time.sleep(_PAGE_SLEEP)
    return posts


def fetch_posts(sub: str, query: str, limit=100, sort="relevance") -> list[dict]:
    """Search within a subreddit, paginating until `limit` posts."""
    posts, after, fetched = [], None, 0
    while fetched < limit:
        params = {"q": query, "sort": sort, "limit": min(100, limit - fetched),
                  "restrict_sr": "true", "t": "all"}
        if after:
            params["after"] = after
        data, err = _rget(f"https://www.reddit.com/r/{sub}/search.json", params=params)
        if err or not data:
            break
        children = data.get("data", {}).get("children", [])
        if not children:
            break
        posts  += [_mk_post(c.get("data", {}), sub) for c in children]
        fetched += len(children)
        after   = data.get("data", {}).get("after")
        if not after:
            break
        time.sleep(_PAGE_SLEEP)
    return posts


def fetch_comments(post_id: str, sub: str, limit=50) -> list[dict]:
    """Fetch top-level comments for a post."""
    data, _ = _rget(f"https://www.reddit.com/r/{sub}/comments/{post_id}.json",
                    params={"limit": limit, "depth": 1, "sort": "top"})
    if not data or not isinstance(data, list) or len(data) < 2:
        return []
    comments = []
    for c in data[1].get("data", {}).get("children", []):
        d = c.get("data", {})
        body = (d.get("body") or "").strip()
        if not body or body in ("[deleted]", "[removed]"):
            continue
        comments.append({
            "id":           d.get("id", ""),
            "post_id":      post_id,
            "subreddit":    sub,
            "text":         body,
            "full_text":    body,
            "score":        d.get("score", 0),
            "author":       d.get("author", "[deleted]"),
            "created_utc":  d.get("created_utc", 0),
            "permalink":    "https://www.reddit.com" + d.get("permalink", ""),
            "title":        "",
            "num_comments": 0,
            "upvote_ratio": 0.5,
            "flair":        "",
        })
    return comments[:limit]

# ─────────────────────────────────────────────────────────────
# SENTIMENT
# ─────────────────────────────────────────────────────────────

def run_sentiment(texts: list[str]) -> list[tuple[str, float]]:
    if VADER_OK:
        a = _Vader()
        out = []
        for t in texts:
            c = a.polarity_scores(t)["compound"]
            out.append(("Positive" if c >= 0.05 else "Negative" if c <= -0.05 else "Neutral", round(c,4)))
        return out
    POS = {"good","great","love","amazing","best","excellent","fun","enjoy","awesome",
           "fantastic","perfect","brilliant","recommend","happy","solid","nice","worth"}
    NEG = {"bad","terrible","awful","hate","worst","broken","buggy","crash","disappointed",
           "poor","boring","trash","horrible","waste","refund","toxic","frustrating","lag","glitch"}
    out = []
    for t in texts:
        ws = re.findall(r"\b\w+\b", t.lower())
        p = sum(1 for w in ws if w in POS); n = sum(1 for w in ws if w in NEG)
        sc = (p-n)/(p+n or 1)
        out.append(("Positive" if sc>0 else "Negative" if sc<0 else "Neutral", round(sc,4)))
    return out

def keywords(texts: list[str], n=30) -> list[tuple[str,int]]:
    words = []
    for t in texts: words.extend(re.findall(r"\b[a-z]{3,}\b", t.lower()))
    return Counter(w for w in words if w not in SW).most_common(n)

# ─────────────────────────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────────────────────────

def donut(pos, neu, neg, title=""):
    fig = go.Figure(go.Pie(
        labels=["Positive","Neutral","Negative"], values=[pos,neu,neg], hole=0.62,
        marker_colors=["#20c65a","#5a5f82","#ff3d52"], textinfo="percent",
        hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
    ))
    fig.update_layout(**PB, showlegend=True, legend=dict(orientation="h",y=-0.15,font_size=10),
        annotations=[dict(text=f"<b>{pos+neu+neg}</b><br><span style='font-size:10px'>posts</span>",
                          x=0.5,y=0.5,font_size=16,showarrow=False,font_color="#eef0fa")],
        title=dict(text=title,font_size=12,x=0), height=280)
    return fig

def histogram(scores):
    fig = go.Figure(go.Histogram(x=scores, nbinsx=30, marker_color="#4080ff", opacity=0.85))
    fig.update_layout(**PB, title=dict(text="Score Distribution",font_size=12),
                      xaxis_title="Compound Score", yaxis_title="Posts", height=260)
    return fig

def hbar(labels, values, title, color):
    fig = go.Figure(go.Bar(x=values[::-1], y=labels[::-1], orientation="h",
                           marker_color=color, opacity=0.88))
    fig.update_layout(**PB, title=dict(text=title,font_size=12),
                      height=max(220,22*len(labels)), xaxis_title="Frequency")
    return fig

def sub_comparison(sdf):
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Positive %", x=sdf["subreddit"], y=sdf["positive_pct"],
                         marker_color="#20c65a", opacity=0.85))
    fig.add_trace(go.Bar(name="Negative %", x=sdf["subreddit"], y=sdf["negative_pct"],
                         marker_color="#ff3d52", opacity=0.85))
    fig.update_layout(**PB, barmode="group", title=dict(text="Sentiment by Subreddit",font_size=12),
                      height=310, xaxis_title="Subreddit", yaxis_title="%",
                      legend=dict(orientation="h",y=-0.22))
    return fig

def timeline(df):
    tmp = df.copy()
    tmp["week"] = pd.to_datetime(tmp["created_utc"],unit="s").dt.to_period("W").dt.start_time
    grp = tmp.groupby(["week","sentiment"]).size().unstack(fill_value=0).reset_index()
    fig = go.Figure()
    for col, col_ in [("Positive","#20c65a"),("Neutral","#5a5f82"),("Negative","#ff3d52")]:
        if col in grp.columns:
            fig.add_trace(go.Scatter(x=grp["week"],y=grp[col],name=col,mode="lines",
                                     stackgroup="one",line_color=col_,opacity=0.85))
    fig.update_layout(**PB, title=dict(text="Post Volume Over Time",font_size=12),
                      height=270, xaxis_title="Week", yaxis_title="Posts",
                      legend=dict(orientation="h",y=-0.22))
    return fig

# ─────────────────────────────────────────────────────────────
# WORD CLOUD
# ─────────────────────────────────────────────────────────────

def wordcloud(texts, cmap="YlOrRd"):
    if not WORDCLOUD_OK or not texts: return None
    wc = _WC(width=900,height=300,background_color="#0a0c1a",colormap=cmap,
             stopwords=SW,max_words=120,min_font_size=9).generate(" ".join(texts))
    fig, ax = plt.subplots(figsize=(9,3), facecolor="#0a0c1a")
    ax.imshow(wc,interpolation="bilinear"); ax.axis("off")
    plt.tight_layout(pad=0)
    buf = io.BytesIO()
    plt.savefig(buf,format="png",dpi=130,bbox_inches="tight",facecolor="#0a0c1a")
    plt.close(fig); buf.seek(0); return buf

# ─────────────────────────────────────────────────────────────
# EXPORTS
# ─────────────────────────────────────────────────────────────

def to_html(md):
    try:
        import markdown as _m
        body = _m.markdown(md, extensions=["tables","fenced_code"])
    except ImportError:
        body = f"<pre>{md}</pre>"
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        '<title>SEGA Reddit Lens</title><style>'
        'body{font-family:Segoe UI,Arial,sans-serif;max-width:860px;margin:40px auto;'
        'background:#0a0c1a;color:#eef0fa;padding:0 1.5rem;}'
        'h1,h2,h3{color:#4080ff;}a{color:#4080ff;}'
        'pre,code{background:#141728;padding:.3em .5em;border-radius:4px;font-size:.87em;}'
        'table{border-collapse:collapse;width:100%;}td,th{border:1px solid #232640;padding:.4em .7em;}'
        'th{background:#1a1e30;}'
        f'</style></head><body>{body}</body></html>'
    )

def to_pdf(md):
    if not REPORTLAB_OK: return None
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf,pagesize=A4,leftMargin=2*cm,rightMargin=2*cm,topMargin=2*cm,bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    H1 = ParagraphStyle("H1",parent=styles["Heading1"],fontSize=18,textColor=_rlc.HexColor("#4080ff"),spaceAfter=8,spaceBefore=14)
    H2 = ParagraphStyle("H2",parent=styles["Heading2"],fontSize=14,textColor=_rlc.HexColor("#1a3acc"),spaceAfter=6,spaceBefore=10)
    H3 = ParagraphStyle("H3",parent=styles["Heading3"],fontSize=12,spaceAfter=4,spaceBefore=8)
    BD = ParagraphStyle("BD",parent=styles["Normal"],fontSize=10,leading=15,spaceAfter=6)
    BU = ParagraphStyle("BU",parent=BD,leftIndent=16,bulletIndent=6,spaceAfter=3)
    CD = ParagraphStyle("CD",parent=styles["Code"],fontSize=8,leading=12,
                         backColor=_rlc.HexColor("#f0f0f8"),leftIndent=12,rightIndent=12,spaceAfter=6)
    story, in_code, code_lines = [], False, []
    for line in md.split("\n"):
        if line.startswith("```"):
            if in_code:
                story += [Preformatted("\n".join(code_lines),CD), Spacer(1,4)]
                code_lines, in_code = [], False
            else: in_code = True
            continue
        if in_code: code_lines.append(line); continue
        if   line.startswith("### "): story.append(Paragraph(line[4:],H3))
        elif line.startswith("## "):
            story += [HRFlowable(width="100%",thickness=0.5,color=_rlc.HexColor("#ccccdd"),spaceAfter=2),
                      Paragraph(line[3:],H2)]
        elif line.startswith("# "):  story.append(Paragraph(line[2:],H1))
        elif line.startswith(("- ","* ")): story.append(Paragraph(f"• {line[2:]}",BU))
        elif line.strip() in ("---","***"):
            story += [HRFlowable(width="100%",thickness=0.5,color=_rlc.HexColor("#ccccdd")),Spacer(1,4)]
        elif line.strip() == "": story.append(Spacer(1,6))
        else: story.append(Paragraph(line,BD))
    doc.build(story)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────────────────────

def kpi(col, label, val, sub, cls="bt"):
    col.markdown(
        f'<div class="metric-card {cls}"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{val}</div><div class="metric-sub">{sub}</div></div>',
        unsafe_allow_html=True)

def sh(text):
    st.markdown(f'<div class="sh"><span class="dot"></span>{text}</div>', unsafe_allow_html=True)

def stats_row(sub: str, sdf: pd.DataFrame) -> dict:
    n = len(sdf)
    pos = (sdf["sentiment"]=="Positive").sum()
    neu = (sdf["sentiment"]=="Neutral").sum()
    neg = (sdf["sentiment"]=="Negative").sum()
    return {"subreddit":sub,"post_count":n,
            "positive_pct":round(100*pos/n,1),"neutral_pct":round(100*neu/n,1),"negative_pct":round(100*neg/n,1),
            "avg_score":round(sdf["sent_score"].mean(),4),
            "avg_upvotes":round(sdf["score"].mean(),1),"avg_comments":round(sdf["num_comments"].mean(),1),
            "pos_count":int(pos),"neu_count":int(neu),"neg_count":int(neg)}

# ═════════════════════════════════════════════════════════════
# PAGE
# ═════════════════════════════════════════════════════════════

st.markdown("""
<div class="topbar">
  <div class="topbar-logo"><span class="seg">SEGA</span> REDDIT LENS</div>
  <div class="topbar-div"></div>
  <div class="topbar-label">Community Sentiment Intelligence</div>
  <div class="topbar-pill">Beta</div>
</div>
<div class="hero">
  <div class="hero-title">Reddit <span class="accent">Community</span><br>Sentiment Analyzer</div>
  <div class="hero-sub">
    Pick a genre to load its key subreddits, add your own manually,
    then run deep sentiment analysis.
  </div>
</div>
""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")

    # ── Reddit credentials ────────────────────────────────────
    st.markdown("**Reddit API**")
    if _REDDIT_ID and _REDDIT_SECRET:
        st.success("✓ Reddit credentials loaded — cloud mode active")
    else:
        st.warning("⚠ No Reddit credentials — local mode only")
        with st.expander("Setup instructions (required for Streamlit Cloud)"):
            st.markdown("""
**2-minute setup — no approval needed:**

1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Click **"create another app"**
3. Choose **script**, give it any name
4. Set redirect URI to `http://localhost`
5. Hit **create app**

Copy the two values and add to your Streamlit Cloud secrets
(or `.streamlit/secrets.toml` locally):

```toml
REDDIT_CLIENT_ID     = "the short ID under your app name"
REDDIT_CLIENT_SECRET = "the secret field"
REDDIT_USER_AGENT    = "MyApp/1.0 by /u/your_username"
```

> A **script** app never needs Reddit's approval.
> Client-credentials grants are read-only and free.
""")

    st.markdown("---")

    # ── Anthropic key ─────────────────────────────────────────
    st.markdown("**Anthropic API** *(optional)*")
    if _SECRET_KEY:
        st.success("✓ Anthropic key loaded")
    else:
        st.warning("⚠ CLAUDE_KEY not set — AI reports disabled")
        st.caption("Add `CLAUDE_KEY = 'sk-ant-…'` to secrets.toml")

    ai_model = st.selectbox("Claude Model", MODELS, index=1)

# ─────────────────────────────────────────────────────────────
# SECTION 1 — GENRE CHIPS
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="search-block">', unsafe_allow_html=True)
st.markdown('<div class="field-label">Step 1 — Select a genre to load its subreddits</div>',
            unsafe_allow_html=True)

# Render chips in rows of 6
_chip_clicked = None
CHIPS_PER_ROW = 6
_genre_rows = [QUICK_GENRES[i:i+CHIPS_PER_ROW] for i in range(0, len(QUICK_GENRES), CHIPS_PER_ROW)]
for _row in _genre_rows:
    st.markdown('<div class="chip-row">', unsafe_allow_html=True)
    _cols = st.columns(len(_row))
    for _ci, _label in enumerate(_row):
        with _cols[_ci]:
            st.markdown('<div class="genre-chip">', unsafe_allow_html=True)
            if st.button(_label.upper(), key=f"chip_{_label}"):
                _chip_clicked = _label
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# When a chip is clicked, load its curated subreddits into session state
if _chip_clicked:
    subs = GENRE_SUBS.get(_chip_clicked, [])
    st.session_state.genre_subs   = subs
    st.session_state.active_genre = _chip_clicked
    st.session_state.posts_df     = None
    st.session_state.sub_stats    = None
    st.session_state.fetch_done   = False
    st.session_state.ai_report    = ""
    st.session_state.chat_history = []

# ─────────────────────────────────────────────────────────────
# SECTION 2 — SUBREDDIT SELECTION  (genre chips + manual)
# ─────────────────────────────────────────────────────────────
sh("SUBREDDIT SELECTION")

col_genre, col_manual = st.columns([3, 2])

# ── Genre subreddits (multiselect) ────────────────────────────
with col_genre:
    active = st.session_state.get("active_genre", "")
    genre_subs = st.session_state.get("genre_subs", [])
    if active:
        st.markdown(f'<div class="field-label">{active.upper()} subreddits</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="field-label">Genre subreddits — pick a genre above</div>',
                    unsafe_allow_html=True)

    if genre_subs:
        chosen = st.multiselect(
            "_genre_ms_label",
            options=genre_subs,
            default=genre_subs,
            format_func=lambda x: f"r/{x}",
            label_visibility="collapsed",
            key="_genre_ms",
        )
        genre_selected = list(chosen)
    else:
        st.caption("Click a genre chip above to populate this list.")
        genre_selected = []

# ── Manual entry ──────────────────────────────────────────────
with col_manual:
    st.markdown('<div class="field-label">Add subreddits manually (one per line)</div>',
                unsafe_allow_html=True)
    st.text_area("_manual_area_label", key="_manual_area",
                 placeholder="gaming\nPS5\nJRPG\nnintendoswitch",
                 height=118, label_visibility="collapsed")
    validate_btn = st.button("✔ Add to List", use_container_width=True)

    if validate_btn:
        lines = [l.strip().lstrip("r/").lstrip("/")
                 for l in st.session_state.get("_manual_area", "").splitlines() if l.strip()]
        if lines:
            existing = {s["name"].lower() for s in st.session_state.manual_subs}
            ph = st.empty()
            added = 0
            for name in lines:
                if name.lower() in existing:
                    continue
                ph.caption(f"Checking r/{name}…")
                info, err = validate_subreddit(name)
                if info:
                    st.session_state.manual_subs.append(info)
                    existing.add(info["name"].lower())
                    added += 1
                elif err:
                    fallback = {"name": name, "title": name, "description": "", "subscribers": 0}
                    st.session_state.manual_subs.append(fallback)
                    existing.add(name.lower())
                    added += 1
                    st.caption(f"⚠ Could not verify r/{name} — added anyway.")
                else:
                    st.warning(f"r/{name} not found or private — skipped.")
            ph.empty()
            if added:
                st.success(f"Added {added} subreddit(s).")

    if st.session_state.manual_subs:
        st.markdown('<div class="field-label" style="margin-top:.6rem">Added manually</div>',
                    unsafe_allow_html=True)
        for idx, s in enumerate(list(st.session_state.manual_subs)):
            mc1, mc2 = st.columns([7, 1])
            with mc1:
                st.markdown(
                    f'<span class="sub-tag">r/{s["name"]}</span>',
                    unsafe_allow_html=True)
            with mc2:
                if st.button("✕", key=f"rm_{idx}_{s['name']}"):
                    st.session_state.manual_subs.pop(idx)
                    st.rerun()

# ── Combined deduplicated list ────────────────────────────────
all_subs: list[str] = list(dict.fromkeys(
    genre_selected + [s["name"] for s in st.session_state.manual_subs]
))

if all_subs:
    st.markdown(
        "**Selected:** " + " ".join(f'<span class="sub-tag">r/{s}</span>' for s in all_subs),
        unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SECTION 3 — FETCH SETTINGS
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="search-block">', unsafe_allow_html=True)
st.markdown('<div class="field-label">Step 2 — Fetch & analysis settings</div>',
            unsafe_allow_html=True)

fc1, fc2, fc3, fc4, fc5 = st.columns([2, 2, 2, 2, 1])
with fc1: posts_per  = st.number_input("Posts per subreddit", 25, 500, 100, 25)
with fc2: sort_mode  = st.selectbox("Post sort", ["top","relevance","new","comments"])
with fc3: time_filter = st.selectbox("Time period", ["all","year","month","week","day"],
                                     format_func=lambda x: {"all":"All time","year":"Past year",
                                         "month":"Past month","week":"Past week","day":"Past 24h"}[x])
with fc4: fetch_comments_opt = st.checkbox("Fetch top 50 comments per post", value=True)
with fc5:
    st.markdown("<br>", unsafe_allow_html=True)
    fetch_btn = st.button("📥 Fetch", use_container_width=True, disabled=(len(all_subs) == 0))

st.markdown('</div>', unsafe_allow_html=True)

if fetch_btn and all_subs:
    query = st.session_state.get("active_genre", "").strip() or "game"
    all_posts: list[dict] = []
    all_comments: list[dict] = []
    prog = st.progress(0.0, text="Starting…")
    status = st.empty()
    n = len(all_subs)

    for i, sub in enumerate(all_subs):
        base = i / n
        # ── Posts ───────────────────────────────────────────
        prog.progress(base, text=f"[{i+1}/{n}] Fetching posts from r/{sub}…")
        status.caption(f"r/{sub} — requesting top posts ({time_filter})…")
        posts = fetch_top(sub, limit=posts_per, time_filter=time_filter)
        if not posts:
            status.caption(f"r/{sub} — no top posts found, trying search…")
            posts = fetch_posts(sub, query=query, limit=posts_per, sort=sort_mode)
        all_posts += posts
        status.caption(f"r/{sub} — got {len(posts)} posts.")

        # ── Comments ────────────────────────────────────────
        if fetch_comments_opt and posts:
            posts_for_comments = posts[:30]
            for j, p in enumerate(posts_for_comments):
                prog.progress(base + (0.5/n) * (j / len(posts_for_comments)),
                              text=f"[{i+1}/{n}] Fetching comments from r/{sub} ({j+1}/{len(posts_for_comments)})…")
                all_comments += fetch_comments(p["id"], sub, limit=50)
                time.sleep(_COMMENT_SLEEP)

        # ── Sleep between subreddits ─────────────────────────
        if i < n - 1:
            prog.progress((i + 1) / n, text=f"[{i+1}/{n}] r/{sub} done — pausing before next…")
            time.sleep(_SUB_SLEEP)

    status.empty()
    prog.progress(0.95, text="Running sentiment analysis…")

    if all_posts:
        df_posts = pd.DataFrame(all_posts).drop_duplicates(subset="id").reset_index(drop=True)
        df_posts["source"] = "post"
        if all_comments:
            df_cmts = pd.DataFrame(all_comments).drop_duplicates(subset="id").reset_index(drop=True)
            df_cmts["source"] = "comment"
            df = pd.concat([df_posts, df_cmts], ignore_index=True)
        else:
            df = df_posts.copy()
            df["source"] = "post"
        sents = run_sentiment(df["full_text"].tolist())
        df["sentiment"]  = [s[0] for s in sents]
        df["sent_score"] = [s[1] for s in sents]
        df["date"] = pd.to_datetime(df["created_utc"], unit="s")
        posts_only = df[df["source"] == "post"]
        sdf = pd.DataFrame([stats_row(s, posts_only[posts_only["subreddit"] == s])
                            for s in posts_only["subreddit"].unique()])
        st.session_state.posts_df     = df
        st.session_state.sub_stats    = sdf
        st.session_state.fetch_done   = True
        st.session_state.ai_report    = ""
        st.session_state.chat_history = []
        prog.progress(1.0, text=f"Done — {len(df_posts):,} posts, {len(df_cmts) if all_comments else 0:,} comments.")
    else:
        st.warning("No posts retrieved — try different settings or fewer subreddits at once.")
    prog.empty()

# ─────────────────────────────────────────────────────────────
# RESULTS
# ─────────────────────────────────────────────────────────────
if st.session_state.fetch_done and st.session_state.posts_df is not None:
    df  = st.session_state.posts_df
    sdf = st.session_state.sub_stats
    df_posts = df[df["source"] == "post"]
    df_cmts  = df[df["source"] == "comment"]

    total  = len(df_posts)
    pos_n  = (df_posts["sentiment"]=="Positive").sum()
    neu_n  = (df_posts["sentiment"]=="Neutral").sum()
    neg_n  = (df_posts["sentiment"]=="Negative").sum()
    avg_s  = df_posts["sent_score"].mean()
    n_cmts = len(df_cmts)

    sh("OVERVIEW")
    k1,k2,k3,k4,k5 = st.columns(5)
    kpi(k1,"Posts",f"{total:,}",f"across {df_posts['subreddit'].nunique()} subreddits")
    kpi(k2,"Comments",f"{n_cmts:,}","fetched & analysed")
    kpi(k3,"Positive",f"{100*pos_n/max(total,1):.1f}%",f"{pos_n:,} posts","pt")
    kpi(k4,"Negative",f"{100*neg_n/max(total,1):.1f}%",f"{neg_n:,} posts","nt")
    kpi(k5,"Avg Score",f"{avg_s:+.3f}","VADER compound")

    sh("SENTIMENT BREAKDOWN")
    c1,c2 = st.columns(2)
    with c1: st.plotly_chart(donut(pos_n,neu_n,neg_n,"Posts — Overall Sentiment"), use_container_width=True)
    with c2: st.plotly_chart(histogram(df_posts["sent_score"].tolist()), use_container_width=True)

    if len(sdf) > 1:
        st.plotly_chart(sub_comparison(sdf), use_container_width=True)
    st.plotly_chart(timeline(df_posts), use_container_width=True)

    sh("DETAILED ANALYSIS")
    tab_ki, tab_wc, tab_sub, tab_posts_br, tab_cmts, tab_ai = st.tabs([
        "🔍 Keywords","☁ Word Cloud","📋 Per-Subreddit","📝 Posts","💬 Comments","🤖 AI Report"])

    # ══════════════════════════════════════════════════════════
    # KEYWORD INSIGHTS TAB
    # ══════════════════════════════════════════════════════════
    with tab_ki:
        st.markdown("""
<style>
.kw-btn-pos>button{background:rgba(32,198,90,.12)!important;border:1px solid rgba(32,198,90,.35)!important;
  color:#20c65a!important;border-radius:3px!important;font-size:.78rem!important;font-weight:500!important;
  padding:.18rem .6rem!important;margin:.15rem!important;min-height:unset!important;height:auto!important;line-height:1.4!important;}
.kw-btn-pos>button:hover{background:rgba(32,198,90,.22)!important;}
.kw-btn-neg>button{background:rgba(255,61,82,.12)!important;border:1px solid rgba(255,61,82,.35)!important;
  color:#ff3d52!important;border-radius:3px!important;font-size:.78rem!important;font-weight:500!important;
  padding:.18rem .6rem!important;margin:.15rem!important;min-height:unset!important;height:auto!important;line-height:1.4!important;}
.kw-btn-neg>button:hover{background:rgba(255,61,82,.22)!important;}
.kw-btn-active-pos>button{background:rgba(32,198,90,.3)!important;border:1px solid #20c65a!important;color:#fff!important;font-weight:700!important;}
.kw-btn-active-neg>button{background:rgba(255,61,82,.3)!important;border:1px solid #ff3d52!important;color:#fff!important;font-weight:700!important;}
</style>
""", unsafe_allow_html=True)

        # ── Source + subreddit filter ──────────────────────────
        ki_c1, ki_c2, ki_c3 = st.columns([2, 2, 3])
        with ki_c1:
            ki_source = st.selectbox("Source", ["Posts + Comments","Posts only","Comments only"],
                                     key="ki_source")
        with ki_c2:
            ki_sub_opts = ["All subreddits"] + sorted(df["subreddit"].unique().tolist())
            ki_sub = st.selectbox("Subreddit", ki_sub_opts, key="ki_sub",
                                  label_visibility="visible")
        with ki_c3:
            ki_pct = (df_posts["sentiment"]=="Positive").sum() / max(len(df_posts),1) * 100
            st.markdown(
                f'<div style="font-size:.78rem;color:var(--muted);padding-top:.55rem;">'
                f'{total:,} posts · {n_cmts:,} comments · '
                f'<span style="color:#20c65a;">{ki_pct:.0f}% positive posts</span></div>',
                unsafe_allow_html=True)

        # Reset keyword selection when filters change
        _ki_state = (ki_source, ki_sub)
        if st.session_state.get("_ki_last_state") != _ki_state:
            st.session_state._ki_last_state    = _ki_state
            st.session_state.kw_selected_term  = None
            st.session_state.kw_selected_sent  = None

        # Build filtered df
        if ki_source == "Posts only":       ki_df = df[df["source"]=="post"]
        elif ki_source == "Comments only":  ki_df = df[df["source"]=="comment"]
        else:                               ki_df = df.copy()
        if ki_sub != "All subreddits":
            ki_df = ki_df[ki_df["subreddit"]==ki_sub]

        ki_pos = ki_df[ki_df["sentiment"]=="Positive"]
        ki_neg = ki_df[ki_df["sentiment"]=="Negative"]
        top_pos = keywords(ki_pos["full_text"].tolist(), n=60)
        top_neg = keywords(ki_neg["full_text"].tolist(), n=60)

        # ── Word clouds inline ─────────────────────────────────
        if WORDCLOUD_OK and (top_pos or top_neg):
            wc_l, wc_r = st.columns(2)
            with wc_l:
                st.markdown('<div style="font-size:.7rem;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:#20c65a;margin-bottom:.4rem;">Positive</div>', unsafe_allow_html=True)
                buf = wordcloud(ki_pos["full_text"].tolist(), "Greens")
                if buf: st.image(buf, use_container_width=True)
            with wc_r:
                st.markdown('<div style="font-size:.7rem;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:#ff3d52;margin-bottom:.4rem;">Negative</div>', unsafe_allow_html=True)
                buf = wordcloud(ki_neg["full_text"].tolist(), "Reds")
                if buf: st.image(buf, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        def _kw_buttons(kws, sent, prefix, active):
            if not kws:
                st.markdown('<span style="font-size:.8rem;color:var(--muted);">No data</span>', unsafe_allow_html=True)
                return
            n_cols = 5
            rows = [kws[i:i+n_cols] for i in range(0, len(kws), n_cols)]
            for row_kws in rows:
                cols = st.columns(n_cols)
                for col, (word, count) in zip(cols, row_kws):
                    is_active = (active == word)
                    css = f"kw-btn-active-{sent}" if is_active else f"kw-btn-{sent}"
                    with col:
                        st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
                        if st.button(f"{word}  {count}", key=f"kw_{prefix}_{sent}_{word}"):
                            if is_active:
                                st.session_state.kw_selected_term = None
                                st.session_state.kw_selected_sent = None
                            else:
                                st.session_state.kw_selected_term = word
                                st.session_state.kw_selected_sent = sent
                        st.markdown('</div>', unsafe_allow_html=True)

        kl, kr = st.columns(2)
        with kl:
            sh(f"WHAT PEOPLE LIKED  — {len(ki_pos):,} positive")
            _kw_buttons(top_pos[:30], "pos", "ki",
                        active=st.session_state.get("kw_selected_term")
                        if st.session_state.get("kw_selected_sent")=="pos" else None)
        with kr:
            sh(f"WHAT PEOPLE DISLIKED  — {len(ki_neg):,} negative")
            _kw_buttons(top_neg[:30], "neg", "ki",
                        active=st.session_state.get("kw_selected_term")
                        if st.session_state.get("kw_selected_sent")=="neg" else None)

        # ── Matching posts/comments panel ──────────────────────
        kw_term = st.session_state.get("kw_selected_term")
        kw_sent = st.session_state.get("kw_selected_sent")
        if kw_term and kw_sent:
            colour  = "#20c65a" if kw_sent=="pos" else "#ff3d52"
            label   = "positive" if kw_sent=="pos" else "negative"
            voted   = (kw_sent == "pos")
            pool    = ki_df[ki_df["sentiment"]==("Positive" if voted else "Negative")]
            mask    = pool["full_text"].str.contains(re.escape(kw_term), case=False, na=False)
            matches = pool[mask].sort_values("score", ascending=False).head(10)
            st.markdown(
                f'<div style="background:var(--surface);border:1px solid var(--border);'
                f'border-left:3px solid {colour};border-radius:0 6px 6px 0;'
                f'padding:.75rem 1.1rem;margin:1rem 0 .75rem;">'
                f'<span style="font-size:.7rem;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:{colour};">MENTIONING</span> '
                f'<span style="font-family:Inter Tight,sans-serif;font-weight:800;font-size:1.05rem;color:var(--text);">"{kw_term}"</span> '
                f'<span style="font-size:.75rem;color:var(--muted);">— {mask.sum():,} {label} results</span>'
                f'</div>', unsafe_allow_html=True)
            if matches.empty:
                st.info("No matches.")
            for _, row in matches.iterrows():
                snip = row["full_text"][:500] + ("…" if len(row["full_text"])>500 else "")
                hi = re.sub(re.escape(kw_term),
                    lambda m: f'<strong style="color:{colour};font-weight:700;">' + m.group(0) + '</strong>',
                    snip, flags=re.IGNORECASE)
                src_icon = "💬" if row.get("source")=="comment" else "📝"
                title_html = f'<strong>{row["title"]}</strong><br>' if row.get("title") else ""
                st.markdown(
                    f'<div style="background:var(--surface2);border:1px solid var(--border);'
                    f'border-left:3px solid {colour};border-radius:0 6px 6px 0;'
                    f'padding:.8rem 1rem .85rem;margin-bottom:.7rem;">'
                    f'<div style="font-size:.84rem;line-height:1.65;color:var(--text);margin-bottom:.5rem;">{title_html}{hi}</div>'
                    f'<div style="font-size:.71rem;color:var(--muted);">'
                    f'{src_icon} r/{row["subreddit"]} · ▲{row["score"]:,} · '
                    f'<a href="{row["permalink"]}" target="_blank" style="color:var(--blue);">view ↗</a>'
                    f'</div></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # WORD CLOUD TAB — with per-subreddit filter
    # ══════════════════════════════════════════════════════════
    with tab_wc:
        wc_c1, wc_c2 = st.columns([2, 2])
        with wc_c1:
            wc_sent = st.selectbox("Sentiment", ["All","Positive","Neutral","Negative"], key="wc_sent")
        with wc_c2:
            wc_sub_opts = ["All subreddits"] + sorted(df["subreddit"].unique().tolist())
            wc_sub = st.selectbox("Subreddit", wc_sub_opts, key="wc_sub")
        wc_src = st.radio("Source", ["Posts + Comments","Posts only","Comments only"],
                          horizontal=True, key="wc_src")

        wc_df = df.copy()
        if wc_src == "Posts only":      wc_df = wc_df[wc_df["source"]=="post"]
        elif wc_src == "Comments only": wc_df = wc_df[wc_df["source"]=="comment"]
        if wc_sub != "All subreddits":  wc_df = wc_df[wc_df["subreddit"]==wc_sub]
        if wc_sent != "All":            wc_df = wc_df[wc_df["sentiment"]==wc_sent]

        cm_ = {"All":"Blues","Positive":"Greens","Neutral":"Greys","Negative":"Reds"}[wc_sent]
        buf = wordcloud(wc_df["full_text"].tolist(), cm_)
        if buf:   st.image(buf, use_container_width=True)
        elif not WORDCLOUD_OK: st.info("Install `wordcloud` and `matplotlib` to enable word clouds.")
        else:     st.info("No text found for the selected filters.")

    # ══════════════════════════════════════════════════════════
    # PER-SUBREDDIT TAB
    # ══════════════════════════════════════════════════════════
    with tab_sub:
        st.dataframe(sdf.sort_values("post_count",ascending=False).reset_index(drop=True),
                     use_container_width=True)
        for _, row in sdf.iterrows():
            with st.expander(f"r/{row['subreddit']}  —  {row['post_count']} posts  ·  {row['positive_pct']:.1f}% positive"):
                sc1, sc2 = st.columns(2)
                with sc1:
                    st.plotly_chart(donut(row["pos_count"],row["neu_count"],row["neg_count"],
                                         f"r/{row['subreddit']}"), use_container_width=True)
                with sc2:
                    st.markdown(f"""
| Metric | Value |
|---|---|
| Avg sentiment | {row['avg_score']:+.4f} |
| Avg upvotes | {row['avg_upvotes']:,.1f} |
| Avg comments | {row['avg_comments']:,.1f} |
| Positive | {row['pos_count']:,} ({row['positive_pct']:.1f}%) |
| Neutral | {row['neu_count']:,} ({row['neutral_pct']:.1f}%) |
| Negative | {row['neg_count']:,} ({row['negative_pct']:.1f}%) |
""")

    # ══════════════════════════════════════════════════════════
    # POSTS BROWSER TAB
    # ══════════════════════════════════════════════════════════
    with tab_posts_br:
        pf1,pf2,pf3,pf4 = st.columns(4)
        with pf1: sf  = st.selectbox("Sentiment","All,Positive,Neutral,Negative".split(","), key="pf_sent")
        with pf2: rf  = st.selectbox("Subreddit",["All"]+sorted(df_posts["subreddit"].unique().tolist()), key="pf_sub")
        with pf3: ps  = st.selectbox("Sort by",["score","num_comments","sent_score","date"], key="pf_sort")
        with pf4: kw_f = st.text_input("Keyword filter", placeholder="e.g. balance, lag, story…", key="pf_kw")
        vdf = df_posts.copy()
        if sf  != "All":  vdf = vdf[vdf["sentiment"]==sf]
        if rf  != "All":  vdf = vdf[vdf["subreddit"]==rf]
        if kw_f.strip():  vdf = vdf[vdf["full_text"].str.contains(re.escape(kw_f.strip()), case=False, na=False)]
        vdf = vdf.sort_values(ps, ascending=False)
        st.caption(f"{len(vdf):,} posts match filters — showing top 30.")
        for _, row in vdf.head(30).iterrows():
            cls = "pos" if row["sentiment"]=="Positive" else "neg" if row["sentiment"]=="Negative" else ""
            exc = (row["text"][:300]+"…") if len(row.get("text",""))>300 else (row.get("text","") or "<em>Link post</em>")
            title_hi = row["title"]
            if kw_f.strip():
                title_hi = re.sub(re.escape(kw_f.strip()),
                    lambda m: f'<mark style="background:rgba(64,128,255,.25);border-radius:2px;">'+m.group(0)+'</mark>',
                    title_hi, flags=re.IGNORECASE)
                exc = re.sub(re.escape(kw_f.strip()),
                    lambda m: f'<mark style="background:rgba(64,128,255,.25);border-radius:2px;">'+m.group(0)+'</mark>',
                    exc, flags=re.IGNORECASE)
            st.markdown(
                f'<div class="post-card {cls}"><strong>{title_hi}</strong><br>{exc}'
                f'<div class="post-meta">r/{row["subreddit"]} · ▲{row["score"]:,} · '
                f'💬{row["num_comments"]} · {row["sentiment"]} ({row["sent_score"]:+.3f}) · '
                f'<a href="{row["permalink"]}" target="_blank" style="color:var(--blue);">view ↗</a>'
                f'</div></div>', unsafe_allow_html=True)
        slug = st.session_state.get("active_genre","export").replace(" ","_")
        st.download_button("⬇ Download CSV", data=vdf.to_csv(index=False).encode(),
                           file_name=f"reddit_{slug}_posts.csv", mime="text/csv")

    # ══════════════════════════════════════════════════════════
    # COMMENTS BROWSER TAB
    # ══════════════════════════════════════════════════════════
    with tab_cmts:
        if df_cmts.empty:
            st.info("No comments fetched — enable 'Fetch top 50 comments per post' before running.")
        else:
            cc1,cc2,cc3,cc4 = st.columns(4)
            with cc1: cs  = st.selectbox("Sentiment","All,Positive,Neutral,Negative".split(","), key="cf_sent")
            with cc2: cr  = st.selectbox("Subreddit",["All"]+sorted(df_cmts["subreddit"].unique().tolist()), key="cf_sub")
            with cc3: cso = st.selectbox("Sort by",["score","sent_score"], key="cf_sort")
            with cc4: ckw = st.text_input("Keyword filter", placeholder="e.g. gameplay, story…", key="cf_kw")
            vcd = df_cmts.copy()
            if cs  != "All": vcd = vcd[vcd["sentiment"]==cs]
            if cr  != "All": vcd = vcd[vcd["subreddit"]==cr]
            if ckw.strip():  vcd = vcd[vcd["full_text"].str.contains(re.escape(ckw.strip()), case=False, na=False)]
            vcd = vcd.sort_values(cso, ascending=False)
            st.caption(f"{len(vcd):,} comments match — showing top 40.")
            for _, row in vcd.head(40).iterrows():
                cls = "pos" if row["sentiment"]=="Positive" else "neg" if row["sentiment"]=="Negative" else ""
                body = row["text"][:400] + ("…" if len(row["text"])>400 else "")
                if ckw.strip():
                    body = re.sub(re.escape(ckw.strip()),
                        lambda m: f'<mark style="background:rgba(64,128,255,.25);border-radius:2px;">'+m.group(0)+'</mark>',
                        body, flags=re.IGNORECASE)
                st.markdown(
                    f'<div class="post-card {cls}">{body}'
                    f'<div class="post-meta">💬 r/{row["subreddit"]} · ▲{row["score"]:,} · '
                    f'{row["sentiment"]} ({row["sent_score"]:+.3f}) · '
                    f'<a href="{row["permalink"]}" target="_blank" style="color:var(--blue);">view ↗</a>'
                    f'</div></div>', unsafe_allow_html=True)
            slug = st.session_state.get("active_genre","export").replace(" ","_")
            st.download_button("⬇ Download Comments CSV", data=vcd.to_csv(index=False).encode(),
                               file_name=f"reddit_{slug}_comments.csv", mime="text/csv")

    # ══════════════════════════════════════════════════════════
    # AI REPORT TAB
    # ══════════════════════════════════════════════════════════
    with tab_ai:
        if not ANTHROPIC_OK:
            st.warning("Install `anthropic` to enable AI reports.")
        elif not _SECRET_KEY:
            st.info("Add CLAUDE_KEY to secrets to enable AI reports.")
        else:
            if not st.session_state.ai_report:
                if st.button("✨ Generate AI Report", key="gen_rpt"):
                    gname  = st.session_state.get("active_genre","the genre").strip()
                    pk_s   = ", ".join(f"{w}({c})" for w,c in keywords(df_posts[df_posts["sentiment"]=="Positive"]["full_text"].tolist())[:20])
                    nk_s   = ", ".join(f"{w}({c})" for w,c in keywords(df_posts[df_posts["sentiment"]=="Negative"]["full_text"].tolist())[:20])
                    cpk_s  = ", ".join(f"{w}({c})" for w,c in keywords(df_cmts[df_cmts["sentiment"]=="Positive"]["full_text"].tolist())[:15]) if not df_cmts.empty else "n/a"
                    cnk_s  = ", ".join(f"{w}({c})" for w,c in keywords(df_cmts[df_cmts["sentiment"]=="Negative"]["full_text"].tolist())[:15]) if not df_cmts.empty else "n/a"
                    sub_s  = "\n".join(f"  - r/{r['subreddit']}: {r['post_count']} posts, {r['positive_pct']:.1f}% positive" for _,r in sdf.iterrows())
                    sp     = df_posts[df_posts["sentiment"]=="Positive"].nlargest(5,"score")["title"].tolist()
                    sn     = df_posts[df_posts["sentiment"]=="Negative"].nlargest(5,"score")["title"].tolist()
                    prompt = f"""You are a senior games market analyst at SEGA.
Write a structured executive sentiment analysis report from this Reddit data.

Genre / topic: {gname}
Posts analysed: {total:,} · Comments analysed: {n_cmts:,}
Subreddits: {", ".join("r/"+s for s in df_posts["subreddit"].unique())}
Date range: {df_posts["date"].min().strftime("%Y-%m-%d")} → {df_posts["date"].max().strftime("%Y-%m-%d")}
Overall posts: {100*pos_n/max(total,1):.1f}% positive · {100*neg_n/max(total,1):.1f}% negative
Avg VADER: {avg_s:+.4f}

Per-subreddit breakdown:
{sub_s}

Post positive keywords: {pk_s}
Post negative keywords: {nk_s}
Comment positive keywords: {cpk_s}
Comment negative keywords: {cnk_s}

Top positive post titles: {sp}
Top negative post titles: {sn}

Write a comprehensive report covering:
1. Executive Summary
2. Overall Sentiment Landscape
3. Subreddit-by-Subreddit Breakdown
4. Key Themes (posts vs comments where different)
5. Community Strengths & Pain Points
6. Competitor / Market Context
7. Actionable Recommendations for SEGA
8. Data Quality Notes

Use markdown. Be specific with numbers."""

                    client = _anthropic.Anthropic(api_key=_SECRET_KEY)
                    ph = st.empty(); txt = ""
                    try:
                        with client.messages.stream(model=ai_model, max_tokens=4096,
                                                    messages=[{"role":"user","content":prompt}]) as s:
                            for d in s.text_stream:
                                txt += d; ph.markdown(txt+"▌")
                        ph.markdown(txt)
                        st.session_state.ai_report = txt
                    except _anthropic.AuthenticationError: st.error("Invalid API key.")
                    except _anthropic.RateLimitError:      st.error("Rate limit — wait and retry.")
                    except Exception as e:                 st.error(f"{type(e).__name__}: {e}")
            else:
                st.markdown(st.session_state.ai_report)

            if st.session_state.ai_report:
                slug = st.session_state.get("active_genre","report").replace(" ","_")
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div style="font-size:.62rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);margin-bottom:.5rem;">DOWNLOAD REPORT</div>', unsafe_allow_html=True)
                d1,d2,d3 = st.columns(3)
                with d1: st.download_button("⬇ Markdown",data=st.session_state.ai_report,
                                            file_name=f"reddit_{slug}.md",mime="text/markdown",key="dl_md")
                with d2: st.download_button("⬇ HTML",data=to_html(st.session_state.ai_report).encode(),
                                            file_name=f"reddit_{slug}.html",mime="text/html",key="dl_html")
                with d3:
                    pdf = to_pdf(st.session_state.ai_report)
                    if pdf: st.download_button("⬇ PDF",data=pdf,file_name=f"reddit_{slug}.pdf",
                                               mime="application/pdf",key="dl_pdf")
                    else: st.caption("PDF: install `reportlab`")

                sh("FOLLOW-UP CHAT")
                for msg in st.session_state.chat_history:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

                if st.session_state.chat_pending:
                    st.session_state.chat_pending = False
                    sys_ = (f"You are a SEGA games market analyst. The user has a Reddit sentiment "
                            f"report for '{gname}'. Answer concisely, referencing real data.\n\n"
                            f"## Report\n{st.session_state.ai_report[:4000]}")
                    try:
                        cc = _anthropic.Anthropic(api_key=_SECRET_KEY)
                        with st.chat_message("assistant"):
                            rep=""; rph=st.empty()
                            with cc.messages.stream(model=ai_model,max_tokens=2048,system=sys_,
                                                    messages=[{"role":m["role"],"content":m["content"]} for m in st.session_state.chat_history]) as s:
                                for d in s.text_stream: rep+=d; rph.markdown(rep+"▌")
                            rph.markdown(rep)
                        st.session_state.chat_history.append({"role":"assistant","content":rep})
                    except Exception as e: st.error(f"Chat error: {e}")

                um = st.chat_input("Ask a follow-up…", key="chat_in")
                if um:
                    st.session_state.chat_history.append({"role":"user","content":um})
                    st.session_state.chat_pending = True
                    st.rerun()

                if st.session_state.chat_history:
                    if st.button("Clear chat", key="clr_chat"):
                        st.session_state.chat_history = []
                        st.session_state.chat_pending = False
                        st.rerun()

elif not st.session_state.fetch_done:
    st.markdown("""
<div class="empty-state">
  <div class="empty-title">NO DATA YET</div>
  <div class="empty-sub">
    Pick a genre above, select your subreddits,
    then click <strong style="color:var(--blue);">Fetch</strong> to begin.
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="footer">
  <div class="footer-brand">SEGA REDDIT LENS</div>
  <div class="footer-note">Data sourced from Reddit public JSON · No API key required · Internal analytics use only</div>
</div>
""", unsafe_allow_html=True)