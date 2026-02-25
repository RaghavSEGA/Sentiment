"""
Twitter / X Sentiment Analyzer — SEGA-branded Streamlit App
============================================================
Run with:  streamlit run twitter_sentiment.py

Required:  pip install streamlit tweepy pandas plotly anthropic matplotlib wordcloud
"""

import re
import os
import html as _html
from collections import Counter
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

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
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="SEGA Twitter Lens",
    page_icon=":material/tag:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# SEGA BRAND STYLES (identical to Steam app)
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
    background: linear-gradient(90deg, var(--blue) 0%, rgba(64,128,255,0) 55%);
}
.topbar-logo { font-family: 'Inter Tight', sans-serif; font-size: 0.95rem; font-weight: 900; color: var(--text) !important; letter-spacing: 0.12em; text-transform: uppercase; }
.topbar-logo .seg { color: var(--blue); }
.topbar-divider { width: 1px; height: 18px; background: var(--border-hi); flex-shrink: 0; }
.topbar-label { font-size: 0.6rem; font-weight: 600; color: var(--muted) !important; letter-spacing: 0.2em; text-transform: uppercase; }
.topbar-pill { margin-left: auto; background: var(--blue-glow); border: 1px solid rgba(64,128,255,0.28); border-radius: 20px; padding: 0.18rem 0.7rem; font-size: 0.58rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--blue) !important; }

/* HERO */
.hero { padding: 1.5rem 0 0.75rem; }
.hero-title { font-family: 'Inter Tight', sans-serif; font-size: 2.4rem; font-weight: 900; line-height: 1.05; color: var(--text) !important; letter-spacing: -0.03em; margin-bottom: 0.5rem; }
.hero-title .accent { color: var(--blue); }
.hero-sub { font-size: 0.87rem; font-weight: 300; color: var(--muted) !important; max-width: 520px; line-height: 1.65; }

/* SEARCH BLOCK */
.search-block { background: var(--surface); border: 1px solid var(--border); border-top: 2px solid var(--blue); border-radius: 0 0 10px 10px; padding: 1.4rem 1.75rem 1.25rem; margin: 1.25rem 0 0; }
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
    caret-color: var(--blue) !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 3px var(--blue-glow) !important;
}
input::placeholder { color: var(--muted) !important; opacity: 0.6 !important; }

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
div[data-baseweb="popover"] { background: var(--surface2) !important; border: 1px solid var(--border-hi) !important; box-shadow: 0 8px 32px rgba(0,0,0,0.5) !important; }
div[data-baseweb="menu"] li,
div[data-baseweb="menu"] [role="option"] { color: var(--text) !important; background: transparent !important; }
div[data-baseweb="menu"] li:hover,
div[data-baseweb="menu"] [aria-selected="true"] { background: var(--surface3) !important; color: var(--text) !important; }

.stCheckbox > label, .stCheckbox > label > span, .stCheckbox label p,
[data-testid="stCheckbox"] span, [data-testid="stCheckbox"] p {
    color: var(--text) !important; font-size: 0.84rem !important;
}

/* BUTTONS */
.stButton > button {
    background: var(--blue) !important; color: #fff !important; border: none !important;
    border-radius: 6px !important; font-family: 'Inter Tight', sans-serif !important;
    font-size: 0.78rem !important; font-weight: 800 !important; letter-spacing: 0.12em !important;
    text-transform: uppercase !important; padding: 0.5rem 1.5rem !important;
    transition: background 0.15s, box-shadow 0.15s, transform 0.1s !important;
    box-shadow: 0 2px 10px rgba(64,128,255,0.3) !important;
}
.stButton > button:hover { background: #2d6aee !important; box-shadow: 0 4px 18px rgba(64,128,255,0.45) !important; transform: translateY(-1px) !important; }
.stButton > button:active { transform: translateY(0px) !important; }

.stDownloadButton > button {
    background: transparent !important; color: var(--blue) !important;
    border: 1px solid rgba(64,128,255,0.35) !important; border-radius: 6px !important;
    font-family: 'Inter Tight', sans-serif !important; font-size: 0.72rem !important;
    font-weight: 700 !important; letter-spacing: 0.1em !important; text-transform: uppercase !important;
    transition: all 0.15s !important; box-shadow: none !important;
}
.stDownloadButton > button:hover { background: var(--blue-glow) !important; border-color: var(--blue) !important; transform: none !important; }

/* SECTION HEADER */
.section-header {
    display: flex; align-items: center; gap: 0.55rem;
    font-family: 'Inter Tight', sans-serif; font-size: 0.72rem; font-weight: 800;
    letter-spacing: 0.18em; text-transform: uppercase; color: var(--text-dim) !important;
    margin: 1.6rem 0 0.9rem;
}
.section-header .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--blue); flex-shrink: 0; }

/* TWEET CARD */
.tweet-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.65rem;
    transition: border-color 0.2s;
}
.tweet-card:hover { border-color: var(--border-hi); }
.tweet-card.pos { border-left: 3px solid var(--pos); }
.tweet-card.neg { border-left: 3px solid var(--neg); }
.tweet-card.neu { border-left: 3px solid var(--muted); }
.tweet-meta { font-size: 0.68rem; color: var(--muted) !important; margin-bottom: 0.4rem; display: flex; gap: 1rem; }
.tweet-text { font-size: 0.88rem; color: var(--text) !important; line-height: 1.55; }
.tweet-badge { display: inline-block; font-size: 0.6rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; padding: 0.15rem 0.5rem; border-radius: 4px; margin-left: auto; }
.tweet-badge.pos { background: var(--pos-dim); color: var(--pos) !important; }
.tweet-badge.neg { background: var(--neg-dim); color: var(--neg) !important; }
.tweet-badge.neu { background: rgba(90,95,130,0.2); color: var(--muted) !important; }

/* CHIP ROW */
.chip-row { display:flex; gap:.65rem; margin:.4rem 0 1.1rem; }
.query-chip > button {
    background: var(--surface) !important; color: var(--text-dim) !important;
    border: 1px solid var(--border) !important; border-radius: 6px !important;
    font-family: 'Inter Tight', sans-serif !important; font-size: .78rem !important;
    font-weight: 700 !important; letter-spacing: .1em !important; text-transform: uppercase !important;
    padding: .4rem 1.1rem !important; min-height: unset !important; height: auto !important;
    line-height: 1.5 !important; transition: border-color .15s, color .15s, background .15s !important;
    box-shadow: none !important; width: 100% !important;
}
.query-chip > button:hover { background: var(--surface2) !important; border-color: var(--blue) !important; color: var(--text) !important; transform: none !important; box-shadow: none !important; }

/* FOOTER */
.footer { margin-top: 4rem; padding: 1.5rem 0; border-top: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
.footer-brand { font-family: 'Inter Tight', sans-serif; font-size: 0.72rem; font-weight: 900; letter-spacing: 0.18em; color: var(--muted) !important; }
.footer-note { font-size: 0.65rem; color: var(--muted) !important; }

/* EMPTY STATE */
.empty-state { text-align: center; padding: 5rem 2rem; }
.empty-title { font-family: 'Inter Tight', sans-serif; font-size: 1.6rem; font-weight: 900; letter-spacing: -0.02em; color: var(--border-hi) !important; margin-bottom: 0.75rem; }
.empty-sub { font-size: 0.88rem; color: var(--muted) !important; max-width: 400px; margin: 0 auto; line-height: 1.65; }

/* PROGRESS / SPINNER */
.stProgress > div > div { background: var(--blue) !important; }

/* TABS */
button[data-baseweb="tab"] {
    font-family: 'Inter Tight', sans-serif !important;
    font-size: 0.72rem !important; font-weight: 800 !important;
    letter-spacing: 0.14em !important; text-transform: uppercase !important;
    color: var(--muted) !important; background: transparent !important;
}
button[data-baseweb="tab"][aria-selected="true"] { color: var(--blue) !important; }
div[data-baseweb="tab-highlight"] { background: var(--blue) !important; }
div[data-baseweb="tab-border"] { background: var(--border) !important; }

/* DATAFRAME */
.stDataFrame { border: 1px solid var(--border) !important; border-radius: 6px !important; }
[data-testid="stDataFrameResizable"] { background: var(--surface) !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# PLOTLY BASE THEME (identical to Steam app)
# ─────────────────────────────────────────────────────────────

PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Poppins", color="#b8bcd4"),
    margin=dict(l=12, r=12, t=28, b=12),
    hoverlabel=dict(
        bgcolor="#1a1e30",
        bordercolor="#323760",
        font=dict(family="Poppins", size=12, color="#eef0fa"),
    ),
)

# ─────────────────────────────────────────────────────────────
# KEYWORD EXTRACTION (same STOPWORDS approach as Steam app)
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
    "played","playing","https","http","rt","amp","via","co","com","www",
    "twitter","tweet","tweets","retweet","follow","dm","lol","im","ive","dont",
    "doesnt","didnt","isnt","wasnt","thats","its","hes","shes","were","theyre",
    "actually","pretty","bit","lot","things","thing","too","now","since",
    "little","every","other","same","most","many","few","already","always",
    "never","ever","maybe","probably","quite","sure","while","without",
    "through","around","against","between","off","over","here","where","why",
    "something","someone","nothing","everything","anything","people","going",
    "know","think","make","made","makes","say","said","says","just","new","one",
    "got","get","re","ll","ve","m","t","s","d","ur","u","r","w",
}

def extract_keywords(texts: list[str], top_n: int = 30) -> list[tuple[str, int]]:
    words_all, bigrams_all = [], []
    for text in texts:
        # Strip URLs and mentions first
        clean = re.sub(r"https?://\S+|@\w+|#", " ", text)
        tokens = re.findall(r"[a-z]{3,}", clean.lower())
        tokens = [t for t in tokens if t not in STOPWORDS]
        words_all.extend(tokens)
        bigrams_all.extend(f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens)-1))
    counter = Counter(words_all) + Counter(bigrams_all)
    return counter.most_common(top_n)


@st.cache_data(show_spinner=False)
def generate_wordcloud_img(freq_json: str, positive: bool) -> bytes:
    import json as _json
    freqs = _json.loads(freq_json)
    if not freqs:
        return b""

    bg = "#0d0f1a"
    hi = "#20c65a" if positive else "#ff3d52"
    lo = "#1a4a2e" if positive else "#4a1a1a"

    def colour_fn(word, font_size, position, orientation, random_state=None, **kw):
        t = min(font_size / 120, 1.0)
        hi_rgb = tuple(int(hi[i:i+2], 16) for i in (1,3,5))
        lo_rgb = tuple(int(lo[i:i+2], 16) for i in (1,3,5))
        r = int(lo_rgb[0] + t*(hi_rgb[0]-lo_rgb[0]))
        g = int(lo_rgb[1] + t*(hi_rgb[1]-lo_rgb[1]))
        b = int(lo_rgb[2] + t*(hi_rgb[2]-lo_rgb[2]))
        return f"rgb({r},{g},{b})"

    wc = _WC(
        width=800, height=380, background_color=bg, max_words=60,
        font_path=None, collocations=False, prefer_horizontal=0.85,
        min_font_size=10, max_font_size=120, color_func=colour_fn, margin=6,
    ).generate_from_frequencies(freqs)

    fig, ax = plt.subplots(figsize=(8, 3.8), facecolor=bg)
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    fig.tight_layout(pad=0)

    buf = __import__("io").BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=bg)
    plt.close(fig)
    buf.seek(0)
    return buf.read()

# ─────────────────────────────────────────────────────────────
# CHART HELPERS
# ─────────────────────────────────────────────────────────────

def chart_sentiment_bar(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar: sentiment % per query/hashtag."""
    srt = df.sort_values("positive_pct", ascending=True)
    colours = [
        "#20c65a" if v >= 60 else "#f0a500" if v >= 40 else "#ff3d52"
        for v in srt["positive_pct"]
    ]
    fig = go.Figure(go.Bar(
        x=srt["positive_pct"], y=srt["query"],
        orientation="h",
        marker=dict(color=colours, opacity=0.88, line=dict(color="rgba(0,0,0,0)", width=0)),
        text=[f"{v:.1f}%" for v in srt["positive_pct"]],
        textposition="outside",
        textfont=dict(color="#b8bcd4", size=11),
        hovertemplate="<b>%{y}</b><br>%{x:.1f}% positive<extra></extra>",
    ))
    fig.add_vline(x=50, line=dict(color="rgba(64,128,255,0.25)", width=1, dash="dot"))
    fig.update_layout(
        **PLOTLY_BASE,
        xaxis=dict(range=[0, 115], showgrid=False, tickfont=dict(color="#5a5f82"), ticksuffix="%"),
        yaxis=dict(showgrid=False, tickfont=dict(color="#b8bcd4", size=11)),
        height=max(260, len(srt) * 44 + 60),
    )
    return fig


def chart_sentiment_scatter(sdf: pd.DataFrame) -> go.Figure:
    """Scatter: positive % vs avg engagement (likes), bubble = tweet count."""
    fig = go.Figure(go.Scatter(
        x=sdf["avg_likes"],
        y=sdf["positive_pct"],
        mode="markers+text",
        text=sdf["query"],
        textposition="top center",
        textfont=dict(color="#b8bcd4", size=10),
        marker=dict(
            size=sdf["tweet_count"].clip(lower=5) ** 0.5 * 4,
            color=sdf["positive_pct"],
            colorscale=[[0, "#ff3d52"], [0.5, "#f0a500"], [1, "#20c65a"]],
            cmin=0, cmax=100,
            showscale=True,
            colorbar=dict(
                title=dict(text="% Pos", font=dict(color="#5a5f82", size=10)),
                tickfont=dict(color="#5a5f82", size=9),
                thickness=10, len=0.7,
            ),
            line=dict(color="rgba(0,0,0,0.4)", width=1),
            opacity=0.9,
        ),
        hovertemplate=(
            "<b>%{text}</b><br>"
            "%{y:.1f}% positive<br>"
            "Avg likes: %{x:.1f}<br>"
            "<extra></extra>"
        ),
    ))
    fig.update_layout(
        **PLOTLY_BASE,
        xaxis=dict(title=dict(text="Avg Likes per Tweet", font=dict(color="#5a5f82", size=11)),
                   showgrid=True, gridcolor="#1a1d2e", zeroline=False, tickfont=dict(color="#5a5f82")),
        yaxis=dict(title=dict(text="% Positive", font=dict(color="#5a5f82", size=11)),
                   showgrid=True, gridcolor="#1a1d2e", zeroline=False,
                   tickfont=dict(color="#5a5f82"), range=[0, 105]),
        height=420,
    )
    return fig


def chart_volume_bar(sdf: pd.DataFrame) -> go.Figure:
    """Grouped bar: positive vs negative tweet count per query."""
    srt = sdf.sort_values("tweet_count", ascending=False)
    short = srt["query"].str[:20]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Positive", x=short, y=srt["positive_count"],
        marker=dict(color="#4080ff", opacity=0.9, line=dict(color="rgba(0,0,0,0)", width=0)),
        hovertemplate="%{x}<br>%{y:,} positive<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Negative", x=short, y=srt["negative_count"],
        marker=dict(color="#ff3d52", opacity=0.75, line=dict(color="rgba(0,0,0,0)", width=0)),
        hovertemplate="%{x}<br>%{y:,} negative<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Neutral", x=short, y=srt["neutral_count"],
        marker=dict(color="#5a5f82", opacity=0.6, line=dict(color="rgba(0,0,0,0)", width=0)),
        hovertemplate="%{x}<br>%{y:,} neutral<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_BASE, barmode="group",
        xaxis=dict(tickangle=-32, tickfont=dict(color="#6b7194", size=10), showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#1a1d2e", tickfont=dict(color="#5a5f82")),
        legend=dict(font=dict(color="#b8bcd4", size=11), bgcolor="rgba(0,0,0,0)",
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        bargap=0.22, bargroupgap=0.06, height=380,
    )
    return fig


def chart_score_hist(df: pd.DataFrame) -> go.Figure:
    """Score distribution histogram across all tweets."""
    fig = go.Figure(go.Histogram(
        x=df["score"], nbinsx=25,
        marker=dict(
            color=df["score"],
            colorscale=[[0, "#ff3d52"], [0.5, "#5a5f82"], [1, "#20c65a"]],
            line=dict(color="#0a0c1a", width=0.3),
        ),
        hovertemplate="Score ~%{x:.1f}: %{y} tweets<extra></extra>",
    ))
    med = df["score"].median()
    fig.add_vline(x=med, line=dict(color="#f0a500", width=1.5, dash="dash"),
                  annotation=dict(text=f"median {med:+.2f}", font=dict(color="#f0a500", size=10), yanchor="top"))
    fig.add_vline(x=0, line=dict(color="rgba(90,95,130,0.4)", width=1, dash="dot"))
    fig.update_layout(
        **PLOTLY_BASE,
        xaxis=dict(title=dict(text="Sentiment Score (−1 to +1)", font=dict(color="#5a5f82", size=11)),
                   tickfont=dict(color="#5a5f82"), showgrid=False),
        yaxis=dict(title=dict(text="Tweets", font=dict(color="#5a5f82", size=11)),
                   showgrid=True, gridcolor="#1a1d2e", tickfont=dict(color="#5a5f82")),
        height=340,
    )
    return fig


def chart_engagement_scatter(df: pd.DataFrame) -> go.Figure:
    """Sentiment score vs likes, sized by retweets."""
    colours = {"Positive": "#20c65a", "Neutral": "#5a5f82", "Negative": "#ff3d52"}
    fig = go.Figure()
    for sentiment, grp in df.groupby("sentiment"):
        fig.add_trace(go.Scatter(
            x=grp["score"],
            y=grp["likes"],
            mode="markers",
            name=sentiment,
            marker=dict(
                color=colours.get(sentiment, "#b8bcd4"),
                size=(grp["retweets"].clip(lower=0) ** 0.5 * 3 + 6).clip(upper=30),
                opacity=0.75,
                line=dict(color="rgba(0,0,0,0.3)", width=0.5),
            ),
            customdata=grp[["username", "reason", "text"]].values,
            hovertemplate=(
                "<b>@%{customdata[0]}</b><br>"
                "Score: %{x:.2f}<br>"
                "Likes: %{y:,}<br>"
                "%{customdata[1]}<br>"
                "<extra></extra>"
            ),
        ))
    fig.update_layout(
        **PLOTLY_BASE,
        xaxis=dict(title=dict(text="Sentiment Score", font=dict(color="#5a5f82", size=11)),
                   showgrid=True, gridcolor="#1a1d2e", zeroline=True, zerolinecolor="#323760",
                   tickfont=dict(color="#5a5f82")),
        yaxis=dict(title=dict(text="Likes", font=dict(color="#5a5f82", size=11)),
                   showgrid=True, gridcolor="#1a1d2e", zeroline=False, tickfont=dict(color="#5a5f82")),
        legend=dict(font=dict(color="#b8bcd4", size=11), bgcolor="rgba(0,0,0,0)"),
        height=420,
    )
    return fig

# ─────────────────────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────────────────────

def fetch_tweets(bearer_token: str, query: str, max_results: int,
                 exclude_rt: bool, exclude_reply: bool, lang: str,
                 start_time=None, end_time=None,
                 sort_by_engagement: bool = False) -> list[dict]:
    """
    Fetch tweets for query.
    If sort_by_engagement=True, over-fetches then returns the top
    max_results sorted by likes + retweets*2 descending.
    start_time / end_time: timezone-aware datetime objects (UTC).
    """
    client = tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=True)

    filters = []
    if exclude_rt:    filters.append("-is:retweet")
    if exclude_reply: filters.append("-is:reply")
    if lang != "any": filters.append(f"lang:{lang}")

    full_query = f"{query} {' '.join(filters)}".strip()
    fetch_count = min(100, max(max_results * 2 if sort_by_engagement else max_results, 10))

    response = client.search_recent_tweets(
        query=full_query,
        max_results=fetch_count,
        tweet_fields=["created_at", "public_metrics", "text", "author_id"],
        expansions=["author_id"],
        user_fields=["username"],
        start_time=start_time,
        end_time=end_time,
    )

    if not response.data:
        return []

    users = {u.id: u.username for u in (response.includes.get("users") or [])}
    tweets = []
    for t in response.data:
        tweets.append({
            "id":         str(t.id),
            "query":      query,
            "text":       t.text,
            "created_at": t.created_at,
            "likes":      t.public_metrics["like_count"],
            "retweets":   t.public_metrics["retweet_count"],
            "replies":    t.public_metrics["reply_count"],
            "username":   users.get(t.author_id, "unknown"),
        })

    if sort_by_engagement:
        tweets.sort(key=lambda t: t["likes"] + t["retweets"] * 2, reverse=True)
        tweets = tweets[:max_results]

    return tweets


def analyze_sentiment_batch(ac, tweets: list[dict]) -> list[dict]:
    numbered = "\n".join(
        f"{i+1}. [{t['username']}]: {t['text']}"
        for i, t in enumerate(tweets)
    )
    prompt = f"""Analyze the sentiment of each tweet below.
For EACH tweet respond with ONLY a line in this exact format:
<n>: <sentiment> | <score> | <brief reason>

Where:
- n         = tweet number
- sentiment = Positive, Negative, or Neutral
- score     = float from -1.0 (most negative) to 1.0 (most positive)
- reason    = ≤10 words explaining the sentiment

Tweets:
{numbered}"""

    message = ac.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    results = []
    for line in message.content[0].text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"(\d+):\s*(Positive|Negative|Neutral)\s*\|\s*([-\d.]+)\s*\|(.*)", line, re.I)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(tweets):
                results.append({
                    **tweets[idx],
                    "sentiment": m.group(2).capitalize(),
                    "score":     float(m.group(3)),
                    "reason":    m.group(4).strip(),
                })
    return results

# ─────────────────────────────────────────────────────────────
# SUMMARY BUILDER
# ─────────────────────────────────────────────────────────────

def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for query, grp in df.groupby("query"):
        pos = (grp["sentiment"] == "Positive").sum()
        neg = (grp["sentiment"] == "Negative").sum()
        neu = (grp["sentiment"] == "Neutral").sum()
        total = len(grp)
        rows.append({
            "query":          query,
            "tweet_count":    total,
            "positive_count": int(pos),
            "negative_count": int(neg),
            "neutral_count":  int(neu),
            "positive_pct":   round(pos / total * 100, 1) if total else 0,
            "avg_score":      round(grp["score"].mean(), 3),
            "avg_likes":      round(grp["likes"].mean(), 1),
            "avg_retweets":   round(grp["retweets"].mean(), 1),
        })
    return pd.DataFrame(rows).sort_values("positive_pct", ascending=False)

# ─────────────────────────────────────────────────────────────
# CURATED TOPIC LISTS
# Each topic maps to a list of targeted search queries.
# Mirrors the Steam app's CURATED_GENRES structure.
# ─────────────────────────────────────────────────────────────

CURATED_TOPICS: dict[str, list[str]] = {
    "fighting games": [
        "Street Fighter 6",
        "Tekken 8",
        "Mortal Kombat 1",
        "Guilty Gear Strive",
        "Dragon Ball FighterZ",
        "King of Fighters XV",
        "Granblue Fantasy Versus Rising",
        "Under Night In-Birth II",
        "Melty Blood Type Lumina",
        "Skullgirls 2nd Encore",
    ],
    "soulslike": [
        "Elden Ring",
        "Elden Ring DLC",
        "Sekiro Shadows Die Twice",
        "Dark Souls",
        "Lies of P",
        "Remnant 2",
        "Hollow Knight Silksong",
        "Lords of the Fallen",
        "Nine Sols",
        "Steelrising",
    ],
    "roguelike": [
        "Hades 2",
        "Balatro",
        "Slay the Spire",
        "Vampire Survivors",
        "Dead Cells",
        "Risk of Rain 2",
        "Binding of Isaac Repentance",
        "Enter the Gungeon",
        "Loop Hero",
        "Cult of the Lamb",
    ],
    "rpg": [
        "Baldurs Gate 3",
        "Cyberpunk 2077",
        "Elden Ring",
        "Witcher 3",
        "Divinity Original Sin 2",
        "Disco Elysium",
        "Starfield",
        "Pathfinder Wrath of the Righteous",
        "Final Fantasy VII Rebirth",
        "Like a Dragon Infinite Wealth",
    ],
    "battle royale": [
        "PUBG",
        "Apex Legends",
        "Warzone",
        "Fortnite",
        "Naraka Bladepoint",
        "Fall Guys",
        "BattleBit Remastered",
        "Realm Royale",
        "Spellbreak",
        "Super People game",
    ],
    "metroidvania": [
        "Hollow Knight Silksong",
        "Blasphemous 2",
        "Prince of Persia Lost Crown",
        "Bloodstained Ritual of the Night",
        "Ori Will of the Wisps",
        "Aeterna Noctis",
        "Deaths Gambit Afterlife",
        "Islets game",
        "Nine Sols",
        "Ghost Song game",
    ],
    "platformer": [
        "Hollow Knight",
        "Celeste",
        "Cuphead",
        "Pizza Tower",
        "Hi-Fi Rush",
        "Sonic Mania",
        "Baba Is You",
        "Psychonauts 2",
        "It Takes Two",
        "GRIS game",
    ],
    "shooter": [
        "Counter-Strike 2",
        "Apex Legends",
        "Rainbow Six Siege",
        "Helldivers 2",
        "Deep Rock Galactic",
        "DOOM Eternal",
        "Warhammer Space Marine 2",
        "BattleBit Remastered",
        "Turbo Overkill",
        "Severed Steel",
    ],
}

TOPIC_ALIASES: dict[str, str] = {
    "fight":         "fighting games",
    "fighter":       "fighting games",
    "fighting":      "fighting games",
    "souls":         "soulslike",
    "souls-like":    "soulslike",
    "soulsborne":    "soulslike",
    "br":            "battle royale",
    "royale":        "battle royale",
    "rogue":         "roguelike",
    "roguelite":     "roguelike",
    "metroid":       "metroidvania",
    "vania":         "metroidvania",
    "action rpg":    "rpg",
    "fps":           "shooter",
    "platform":      "platformer",
}

QUICK_TOPICS = ["fighting games", "soulslike", "roguelike", "metroidvania", "battle royale", "rpg"]


def resolve_topic(term: str) -> str | None:
    """Return canonical topic key for a search term, or None if not found."""
    key = term.lower().strip()
    key = TOPIC_ALIASES.get(key, key)
    return key if key in CURATED_TOPICS else None


# ─────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────

for key, default in [
    ("results_df",       None),
    ("summary_df",       None),
    ("last_queries",     []),
    ("ai_report",        ""),
    ("found_queries",    []),       # list of query strings from topic lookup
    ("selected_queries", {}),      # {query: bool} toggle state
    ("last_topic",       ""),
    ("twitter_key",      st.secrets.get("TWITTER_BEARER_TOKEN", os.environ.get("TWITTER_BEARER_TOKEN", ""))),
    ("claude_key",       st.secrets.get("ANTHROPIC_API_KEY",    os.environ.get("ANTHROPIC_API_KEY",    ""))),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─────────────────────────────────────────────────────────────
# TOP NAV
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="topbar">
  <div class="topbar-logo"><span class="seg">SEGA</span> TWITTER LENS</div>
  <div class="topbar-divider"></div>
  <div class="topbar-label">Social Sentiment Platform</div>
  <div class="topbar-pill">Beta</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
  <div class="hero-title">TWITTER <span class="accent">ANALYTICS</span></div>
  <div class="hero-sub">Pull tweets for any query or hashtag — explore sentiment, engagement, keywords, and AI insights in one view.</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# QUICK-START TOPIC CHIPS
# ─────────────────────────────────────────────────────────────

st.markdown('<div class="chip-row">', unsafe_allow_html=True)
_chip_cols = st.columns(len(QUICK_TOPICS))
_chip_clicked = None
for _ci, _label in enumerate(QUICK_TOPICS):
    with _chip_cols[_ci]:
        st.markdown('<div class="query-chip">', unsafe_allow_html=True)
        if st.button(_label, key=f"chip_{_ci}"):
            _chip_clicked = _label
        st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# API KEY STATUS (loaded from st.secrets / env vars)
# ─────────────────────────────────────────────────────────────

_tw_ok = bool(st.session_state.twitter_key)
_cl_ok = bool(st.session_state.claude_key)

if not (_tw_ok and _cl_ok):
    st.markdown("""
<div style="background:var(--surface);border:1px solid var(--border);border-top:2px solid var(--neg);
border-radius:0 0 8px 8px;padding:1rem 1.5rem;margin-bottom:1rem;">
<div style="font-size:.62rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;
color:var(--neg);margin-bottom:.5rem;">Missing API Keys</div>
<div style="font-size:.82rem;color:var(--text-dim);line-height:1.7;">
Add the following to <code>.streamlit/secrets.toml</code> in your project folder:
<pre style="background:var(--bg);border:1px solid var(--border);border-radius:6px;
padding:.75rem 1rem;margin:.6rem 0 0;font-size:.8rem;color:var(--blue);">TWITTER_BEARER_TOKEN = "your-token-here"
ANTHROPIC_API_KEY    = "sk-ant-your-key-here"</pre>
Then restart the app.
</div>
</div>
""", unsafe_allow_html=True)
else:
    st.markdown(f"""
<div style="display:flex;gap:1rem;margin-bottom:1rem;">
  <div style="background:var(--pos-dim);border:1px solid rgba(32,198,90,.25);border-radius:6px;
  padding:.4rem 1rem;font-size:.68rem;font-weight:600;color:var(--pos);">✓ Twitter API connected</div>
  <div style="background:var(--pos-dim);border:1px solid rgba(32,198,90,.25);border-radius:6px;
  padding:.4rem 1rem;font-size:.68rem;font-weight:600;color:var(--pos);">✓ Anthropic API connected</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SEARCH FORM
# ─────────────────────────────────────────────────────────────

st.markdown('<div class="search-block">', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns([3, 1.2, 1.2, 1.2])
with c1:
    st.markdown('<div class="field-label">Topic / Search Term</div>', unsafe_allow_html=True)
    topic_input = st.text_input(
        "topic", label_visibility="collapsed",
        placeholder="e.g.  fighting games,  soulslike,  rpg  — or any custom query",
        value=_chip_clicked or "",
        key="topic_text_input",
    )
with c2:
    st.markdown('<div class="field-label">Max Tweets / Query</div>', unsafe_allow_html=True)
    max_tweets = st.selectbox("max tweets", [25, 50, 100], index=1, label_visibility="collapsed")
with c3:
    st.markdown('<div class="field-label">Language</div>', unsafe_allow_html=True)
    lang = st.selectbox("lang", ["en", "es", "fr", "de", "ja", "any"], label_visibility="collapsed")
with c4:
    st.markdown('<div class="field-label">Batch Size</div>', unsafe_allow_html=True)
    batch_size = st.selectbox("batch", [5, 10, 20], index=1, label_visibility="collapsed",
                              help="Tweets analysed per Claude request")

_sr1, _ = st.columns([1.5, 4.5])
with _sr1:
    st.markdown('<div class="field-label">Sort Tweets By</div>', unsafe_allow_html=True)
    sort_mode = st.selectbox("sort_mode", ["Most Recent", "Most Engagement"],
                             label_visibility="collapsed",
                             help="Most Engagement over-fetches then returns highest likes+retweets")

_filter_col1, _filter_col2, _btn_col, _ = st.columns([1, 1, 1, 3])
with _filter_col1:
    exclude_rt    = st.checkbox("Exclude retweets", value=True)
with _filter_col2:
    exclude_reply = st.checkbox("Exclude replies", value=True)
with _btn_col:
    search_clicked = st.button("SEARCH TOPIC", width='stretch')
st.markdown("</div>", unsafe_allow_html=True)

# ── Chip auto-triggers search ─────────────────────────────────
if _chip_clicked:
    search_clicked = True
    topic_input    = _chip_clicked

# ─────────────────────────────────────────────────────────────
# TOPIC SEARCH LOGIC — populate found_queries
# ─────────────────────────────────────────────────────────────

if search_clicked and topic_input.strip():
    resolved = resolve_topic(topic_input.strip())
    if resolved:
        # Curated topic hit — merge into existing list, preserving any custom additions
        new_queries = CURATED_TOPICS[resolved]
        existing    = st.session_state.found_queries
        merged      = existing + [q for q in new_queries if q not in existing]
        st.session_state.found_queries = merged
        for q in new_queries:
            if q not in st.session_state.selected_queries:
                st.session_state.selected_queries[q] = True
        st.session_state.last_topic = resolved
    else:
        # Free-text: add as a single query if not already present
        q = topic_input.strip()
        if q not in st.session_state.found_queries:
            st.session_state.found_queries.append(q)
            st.session_state.selected_queries[q] = True
        st.session_state.last_topic = q
    # Clear results so dashboard reflects the new query set
    st.session_state.results_df = None
    st.session_state.summary_df = None

# ─────────────────────────────────────────────────────────────
# QUERY TOGGLE LIST (mirrors Steam's game checkbox list)
# ─────────────────────────────────────────────────────────────

if st.session_state.found_queries:
    st.markdown(
        '<div class="section-header"><span class="dot"></span>QUERIES FOUND</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:.78rem;color:var(--muted);margin-bottom:.75rem;">' +
        (f'Curated list for <strong style="color:var(--text);">{st.session_state.last_topic}</strong> — ' if resolve_topic(st.session_state.last_topic) else "") +
        'Toggle queries on/off, add custom ones below, then click <strong style="color:var(--blue);">Fetch &amp; Analyse</strong>.</div>',
        unsafe_allow_html=True,
    )

    # Select-all / deselect-all / clear-all row
    _sa_col, _sd_col, _cl_col, _ = st.columns([1, 1, 1, 5])
    with _sa_col:
        if st.button("Select all", key="sel_all"):
            for q in st.session_state.found_queries:
                st.session_state.selected_queries[q] = True
            st.rerun()
    with _sd_col:
        if st.button("Deselect all", key="desel_all"):
            for q in st.session_state.found_queries:
                st.session_state.selected_queries[q] = False
            st.rerun()
    with _cl_col:
        if st.button("Clear list", key="clear_all"):
            st.session_state.found_queries    = []
            st.session_state.selected_queries = {}
            st.rerun()

    # Checkbox grid — 2 columns, with a ✕ remove button per query
    for _qi, _q in enumerate(list(st.session_state.found_queries)):
        _cb_col, _rm_col = st.columns([11, 1])
        with _cb_col:
            _checked = st.session_state.selected_queries.get(_q, True)
            _new     = st.checkbox(_q, value=_checked, key=f"qcheck_{_qi}")
            st.session_state.selected_queries[_q] = _new
        with _rm_col:
            if st.button("✕", key=f"rm_{_qi}", help=f"Remove '{_q}'"):
                st.session_state.found_queries.remove(_q)
                st.session_state.selected_queries.pop(_q, None)
                st.rerun()

    # ── Add a custom query ────────────────────────────────────
    st.markdown(
        '<div style="margin-top:.9rem;font-size:.62rem;font-weight:700;letter-spacing:.18em;'
        'text-transform:uppercase;color:var(--muted);margin-bottom:.4rem;">Add a query</div>',
        unsafe_allow_html=True,
    )
    _add_col, _add_btn = st.columns([5, 1])
    with _add_col:
        _add_input = st.text_input(
            "add_query", label_visibility="collapsed",
            placeholder='e.g.  "Guilty Gear Strive"  or  #ArcSystemWorks',
            key="add_query_input",
        )
    with _add_btn:
        _add_clicked = st.button("ADD", key="btn_add_query", width='stretch')
    if _add_clicked and _add_input.strip():
        _aq = _add_input.strip()
        if _aq not in st.session_state.found_queries:
            st.session_state.found_queries.append(_aq)
            st.session_state.selected_queries[_aq] = True
            st.rerun()
        else:
            st.caption(f"'{_aq}' is already in the list.")

    # Fetch & Analyse button
    _selected_list = [q for q, v in st.session_state.selected_queries.items() if v]
    st.markdown("<br>", unsafe_allow_html=True)
    _fa_col, _ = st.columns([1, 5])
    with _fa_col:
        fetch_clicked = st.button(
            f"FETCH & ANALYSE ({len(_selected_list)} {'query' if len(_selected_list)==1 else 'queries'})",
            width='stretch',
            disabled=not _selected_list,
        )

    # ─────────────────────────────────────────────────────────────
    # FETCH + ANALYSE LOGIC
    # ─────────────────────────────────────────────────────────────

    if fetch_clicked and _selected_list:
        # Twitter free/Basic tier: search window is always the last 7 days
        import datetime as _dt
        _now        = _dt.datetime.now(_dt.timezone.utc)
        _start_time = None  # let Twitter default to its own 7-day window
        _end_time   = None

        if not st.session_state.twitter_key:
            st.error("Twitter Bearer Token missing — check your secrets.toml.")
        elif not st.session_state.claude_key:
            st.error("Anthropic API key missing — check your secrets.toml.")
        elif not TWEEPY_AVAILABLE:
            st.error("tweepy not installed. Run: pip install tweepy")
        elif not ANTHROPIC_AVAILABLE:
            st.error("anthropic not installed. Run: pip install anthropic")
        else:
            all_tweets = []
            ac = _anthropic.Anthropic(api_key=st.session_state.claude_key)

            with st.status(f"Processing {len(_selected_list)} queries…", expanded=True) as status:
                for qi, query in enumerate(_selected_list):
                    status.update(label=f"🔍 Fetching tweets for: {query} ({qi+1}/{len(_selected_list)})")
                    try:
                        tweets = fetch_tweets(
                            st.session_state.twitter_key, query,
                            max_tweets, exclude_rt, exclude_reply, lang,
                            start_time=_start_time,
                            end_time=_end_time,
                            sort_by_engagement=(sort_mode == "Most Engagement"),
                        )
                    except Exception as e:
                        st.warning(f"Twitter API error for '{query}': {e}")
                        tweets = []

                    if not tweets:
                        st.warning(f"No tweets found for '{query}' — skipping.")
                        continue

                    st.write(f"✅ **{query}** — fetched {len(tweets)} tweets")

                    batches = [tweets[i:i+batch_size] for i in range(0, len(tweets), batch_size)]
                    progress = st.progress(0, text=f"Analysing {query}…")

                    consecutive_failures = 0
                    failed = False
                    for i, batch in enumerate(batches):
                        status.update(label=f"🤖 {query}: batch {i+1}/{len(batches)}")
                        try:
                            all_tweets.extend(analyze_sentiment_batch(ac, batch))
                            consecutive_failures = 0
                        except _anthropic.AuthenticationError:
                            st.error("Invalid Anthropic API key — check console.anthropic.com/settings/keys.")
                            failed = True
                            break
                        except _anthropic.APIConnectionError as e:
                            consecutive_failures += 1
                            st.warning(f"Batch {i+1} connection error: {e}")
                            if consecutive_failures >= 2:
                                st.error("Multiple connection failures — stopping. Check your network and API key.")
                                failed = True
                                break
                        except Exception as e:
                            consecutive_failures += 1
                            st.warning(f"Batch {i+1} failed ({type(e).__name__}): {e}")
                            if consecutive_failures >= 2:
                                st.error("Multiple batch failures — stopping early.")
                                failed = True
                                break
                        progress.progress((i+1)/len(batches))

                    if failed:
                        break

                status.update(label="✅ All queries complete!", state="complete")

            if all_tweets:
                new_df = pd.DataFrame(all_tweets)
                if st.session_state.results_df is not None:
                    combined = pd.concat([st.session_state.results_df, new_df], ignore_index=True)
                    combined = combined.drop_duplicates(subset=["id"])
                    st.session_state.results_df = combined
                else:
                    st.session_state.results_df = new_df

                for q in _selected_list:
                    if q not in st.session_state.last_queries:
                        st.session_state.last_queries.append(q)

                st.session_state.summary_df = build_summary(st.session_state.results_df)

# ─────────────────────────────────────────────────────────────
# RESULTS DASHBOARD
# ─────────────────────────────────────────────────────────────

if st.session_state.results_df is not None and st.session_state.summary_df is not None:
    df  = st.session_state.results_df
    sdf = st.session_state.summary_df

    # ── Query filter ─────────────────────────────────────────
    if len(sdf) > 1:
        with st.expander("Filter by query", expanded=False):
            _qf_choices = st.multiselect(
                "Select queries to include",
                options=df["query"].unique().tolist(),
                default=df["query"].unique().tolist(),
                label_visibility="collapsed",
            )
            if _qf_choices:
                df  = df[df["query"].isin(_qf_choices)].copy()
                sdf = build_summary(df) if len(df) else sdf

    # ── KPI STRIP ─────────────────────────────────────────────
    total_tweets  = len(df)
    total_queries = sdf["query"].nunique()
    avg_sentiment = sdf["positive_pct"].mean()
    top_query     = sdf.iloc[0]["query"] if len(sdf) else "—"
    top_pct       = sdf.iloc[0]["positive_pct"] if len(sdf) else 0
    avg_score     = df["score"].mean()

    _sc = "#20c65a" if avg_sentiment >= 60 else "#f0a500" if avg_sentiment >= 40 else "#ff3d52"
    short_q = top_query[:24] + ("…" if len(top_query) > 24 else "")

    st.markdown(f"""
<style>
.kpi-sticky {{ position:sticky; top:0; z-index:999; background:var(--bg); padding:.6rem 0 .5rem; border-bottom:1px solid var(--border); margin-bottom:1.25rem; }}
.kpi-strip  {{ display:flex; gap:1rem; align-items:stretch; }}
.kpi-tile   {{ flex:1; background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:.9rem 1.2rem; position:relative; overflow:hidden; transition:border-color .2s; }}
.kpi-tile:hover {{ border-color:var(--border-hi); }}
.kpi-tile.blue-top {{ border-top:2px solid var(--blue); }}
.kpi-tile.pos-top  {{ border-top:2px solid {_sc}; }}
.kpi-tile-label {{ font-size:.58rem; font-weight:700; letter-spacing:.2em; text-transform:uppercase; color:var(--muted); margin-bottom:.3rem; }}
.kpi-tile-val {{ font-family:'Inter Tight',sans-serif; font-size:1.9rem; font-weight:900; color:var(--text); line-height:1; letter-spacing:-.025em; }}
.kpi-tile-sub {{ font-size:.68rem; color:var(--muted); margin-top:.2rem; }}
@keyframes countUp {{ from {{ opacity:0; transform:translateY(6px); }} to {{ opacity:1; transform:translateY(0); }} }}
.kpi-tile-val {{ animation:countUp .5s ease forwards; }}
</style>
<div class="kpi-sticky">
  <div class="kpi-strip">
    <div class="kpi-tile blue-top">
      <div class="kpi-tile-label">Tweets Collected</div>
      <div class="kpi-tile-val">{total_tweets:,}</div>
      <div class="kpi-tile-sub">across {total_queries} {'query' if total_queries==1 else 'queries'}</div>
    </div>
    <div class="kpi-tile pos-top">
      <div class="kpi-tile-label">Avg Sentiment</div>
      <div class="kpi-tile-val" style="color:{_sc};">{avg_sentiment:.0f}%</div>
      <div class="kpi-tile-sub">positive tweets</div>
    </div>
    <div class="kpi-tile blue-top">
      <div class="kpi-tile-label">Top Query</div>
      <div class="kpi-tile-val" style="font-size:1.1rem;line-height:1.25;padding-top:.15rem;">{short_q}</div>
      <div class="kpi-tile-sub">{top_pct:.0f}% positive</div>
    </div>
    <div class="kpi-tile blue-top">
      <div class="kpi-tile-label">Avg Score</div>
      <div class="kpi-tile-val">{avg_score:+.2f}</div>
      <div class="kpi-tile-sub">−1.0 (neg) to +1.0 (pos)</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── TABS ─────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["SENTIMENT", "ENGAGEMENT", "QUERY TABLE", "TWEETS", "AI ANALYSIS"])

    # ════════════════════════════════════════════════════════
    # TAB 1 — SENTIMENT
    # ════════════════════════════════════════════════════════
    with tab1:
        with st.expander("How sentiment is calculated", expanded=False):
            st.markdown(
                "Each tweet is sent to Claude in batches. Claude assigns a label "
                "(**Positive / Neutral / Negative**) and a score from −1.0 to +1.0, "
                "plus a brief rationale. The **% Positive** metric shown is simply "
                "`positive tweets ÷ total tweets × 100`. No external NLP library is used."
            )

        st.markdown('<div class="section-header"><span class="dot"></span>POSITIVE SENTIMENT RANKING</div>', unsafe_allow_html=True)
        st.plotly_chart(chart_sentiment_bar(sdf), config={"displayModeBar": False})

        st.markdown('<div class="section-header"><span class="dot"></span>SENTIMENT vs. ENGAGEMENT</div>', unsafe_allow_html=True)
        st.caption("Bubble size = tweet count for that query")
        st.plotly_chart(chart_sentiment_scatter(sdf), config={"displayModeBar": False})

        st.markdown('<div class="section-header"><span class="dot"></span>SCORE DISTRIBUTION</div>', unsafe_allow_html=True)
        st.caption("Distribution of per-tweet sentiment scores (−1 to +1) · amber line = median")
        st.plotly_chart(chart_score_hist(df), config={"displayModeBar": False})

    # ════════════════════════════════════════════════════════
    # TAB 2 — ENGAGEMENT
    # ════════════════════════════════════════════════════════
    with tab2:
        left, right = st.columns(2)
        with left:
            st.markdown('<div class="section-header"><span class="dot"></span>TWEET VOLUME BY QUERY</div>', unsafe_allow_html=True)
            st.plotly_chart(chart_volume_bar(sdf), config={"displayModeBar": False})
        with right:
            st.markdown('<div class="section-header"><span class="dot"></span>SENTIMENT vs. LIKES</div>', unsafe_allow_html=True)
            st.caption("Point size = retweet count")
            st.plotly_chart(chart_engagement_scatter(df), config={"displayModeBar": False})

    # ════════════════════════════════════════════════════════
    # TAB 3 — QUERY TABLE
    # ════════════════════════════════════════════════════════
    with tab3:
        st.markdown('<div class="section-header"><span class="dot"></span>QUERY SUMMARY</div>', unsafe_allow_html=True)
        display = sdf.rename(columns={
            "query":          "Query",
            "tweet_count":    "Tweets",
            "positive_count": "Positive",
            "negative_count": "Negative",
            "neutral_count":  "Neutral",
            "positive_pct":   "% Positive",
            "avg_score":      "Avg Score",
            "avg_likes":      "Avg Likes",
            "avg_retweets":   "Avg RTs",
        })
        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "% Positive": st.column_config.ProgressColumn(
                    "% Positive", min_value=0, max_value=100, format="%.1f%%"
                ),
                "Avg Score": st.column_config.NumberColumn("Avg Score", format="%+.3f"),
            },
        )
        st.markdown("<br>", unsafe_allow_html=True)
        dl1, _ = st.columns([1, 5])
        with dl1:
            st.download_button(
                "Download summary (.csv)",
                data=display.to_csv(index=False).encode("utf-8"),
                file_name="twitter_sentiment_summary.csv",
                mime="text/csv",
                width='stretch',
            )

    # ════════════════════════════════════════════════════════
    # TAB 4 — TWEETS + keyword insights
    # ════════════════════════════════════════════════════════
    with tab4:

        # ── Keyword extraction ────────────────────────────────────────────────
        import json as _j, re as _re
        _pos_texts = df[df["sentiment"] == "Positive"]["text"].tolist()
        _neg_texts = df[df["sentiment"] == "Negative"]["text"].tolist()
        _pos_kw = extract_keywords(_pos_texts, 30)
        _neg_kw = extract_keywords(_neg_texts, 30)
        _pos_set = {w for w, _ in _pos_kw}
        _neg_set = {w for w, _ in _neg_kw}

        # ── Keyword chip CSS ──────────────────────────────────────────────────
        st.markdown("""
<style>
.kw-btn-pos > button {
    background: var(--pos-dim) !important; color: var(--pos) !important;
    border: 1px solid rgba(32,198,90,.25) !important; border-radius: 4px !important;
    font-size: .68rem !important; font-weight: 600 !important; letter-spacing: .04em !important;
    padding: .22rem .6rem !important; min-height: unset !important; height: auto !important;
    text-transform: none !important; box-shadow: none !important; width:100% !important;
}
.kw-btn-pos > button:hover { background: rgba(32,198,90,.22) !important; transform: none !important; }
.kw-btn-active-pos > button {
    background: var(--pos) !important; color: #000 !important;
    border: 1px solid var(--pos) !important; border-radius: 4px !important;
    font-size: .68rem !important; font-weight: 700 !important;
    padding: .22rem .6rem !important; min-height: unset !important; height: auto !important;
    text-transform: none !important; box-shadow: none !important; width:100% !important;
}
.kw-btn-neg > button {
    background: var(--neg-dim) !important; color: var(--neg) !important;
    border: 1px solid rgba(255,61,82,.25) !important; border-radius: 4px !important;
    font-size: .68rem !important; font-weight: 600 !important; letter-spacing: .04em !important;
    padding: .22rem .6rem !important; min-height: unset !important; height: auto !important;
    text-transform: none !important; box-shadow: none !important; width:100% !important;
}
.kw-btn-neg > button:hover { background: rgba(255,61,82,.22) !important; transform: none !important; }
.kw-btn-active-neg > button {
    background: var(--neg) !important; color: #fff !important;
    border: 1px solid var(--neg) !important; border-radius: 4px !important;
    font-size: .68rem !important; font-weight: 700 !important;
    padding: .22rem .6rem !important; min-height: unset !important; height: auto !important;
    text-transform: none !important; box-shadow: none !important; width:100% !important;
}
.kw-chip-clear > button {
    background: transparent !important; color: var(--muted) !important;
    border: 1px solid var(--border) !important; border-radius: 20px !important;
    font-size: .7rem !important; font-weight: 600 !important;
    padding: .25rem .75rem !important; min-height: unset !important; height: auto !important;
    text-transform: none !important; box-shadow: none !important;
}
.kw-chip-clear > button:hover { border-color: var(--muted) !important; transform: none !important; }
</style>
""", unsafe_allow_html=True)

        # session state for selected keyword chip
        if "kw_selected_term" not in st.session_state:
            st.session_state.kw_selected_term      = None
        if "kw_selected_sentiment" not in st.session_state:
            st.session_state.kw_selected_sentiment = None
        # legacy plain filter (still used by tweet browser below)
        if "kw_filter" not in st.session_state:
            st.session_state.kw_filter = ""

        def _render_kw_buttons(kws, sentiment):
            """5-column grid of keyword buttons; active chip is highlighted."""
            if not kws:
                st.markdown('<span style="font-size:.8rem;color:var(--muted);">No data</span>',
                            unsafe_allow_html=True)
                return
            n_cols = 5
            rows   = [kws[i:i+n_cols] for i in range(0, len(kws), n_cols)]
            active = st.session_state.kw_selected_term
            active_sent = st.session_state.kw_selected_sentiment
            for row_kws in rows:
                btn_cols = st.columns(n_cols)
                for col, (word, count) in zip(btn_cols, row_kws):
                    is_active = (active == word and active_sent == sentiment)
                    css = (f"kw-btn-active-{sentiment}" if is_active else f"kw-btn-{sentiment}")
                    with col:
                        st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
                        if st.button(f"{word}  {count}",
                                     key=f"kw_{sentiment}_{word.replace(' ','_')}"):
                            if is_active:
                                st.session_state.kw_selected_term      = None
                                st.session_state.kw_selected_sentiment = None
                                st.session_state.kw_filter             = ""
                            else:
                                st.session_state.kw_selected_term      = word
                                st.session_state.kw_selected_sentiment = sentiment
                                st.session_state.kw_filter             = word
                        st.markdown('</div>', unsafe_allow_html=True)

        # ── Word clouds ───────────────────────────────────────────────────────
        st.markdown(
            '<div class="section-header"><span class="dot"></span>KEYWORD INSIGHTS'
            '<span style="color:var(--muted);font-size:.7rem;font-weight:400;"> '
            '— click any keyword to filter tweets below</span></div>',
            unsafe_allow_html=True,
        )
        _wc1, _wc2 = st.columns(2)
        with _wc1:
            st.markdown('<div style="font-size:.62rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--pos);margin-bottom:.5rem;">Positive</div>', unsafe_allow_html=True)
            if WORDCLOUD_AVAILABLE and _pos_kw:
                _wc_bytes = generate_wordcloud_img(_j.dumps(dict(_pos_kw)), True)
                if _wc_bytes:
                    st.image(_wc_bytes, use_container_width=True)
            else:
                st.caption(", ".join(f"{w} ({c})" for w, c in _pos_kw[:15]))
        with _wc2:
            st.markdown('<div style="font-size:.62rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--neg);margin-bottom:.5rem;">Negative</div>', unsafe_allow_html=True)
            if WORDCLOUD_AVAILABLE and _neg_kw:
                _wc_bytes = generate_wordcloud_img(_j.dumps(dict(_neg_kw)), False)
                if _wc_bytes:
                    st.image(_wc_bytes, use_container_width=True)
            else:
                st.caption(", ".join(f"{w} ({c})" for w, c in _neg_kw[:15]))

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Two-panel keyword chip grid ───────────────────────────────────────
        _kl, _kr = st.columns(2)
        with _kl:
            st.markdown(
                f'<div class="section-header"><span class="dot"></span>'
                f'WHAT PEOPLE LIKED '
                f'<span style="color:var(--muted);font-size:.7rem;font-weight:400;">'
                f'— {len(_pos_texts):,} positive tweets</span></div>',
                unsafe_allow_html=True,
            )
            _render_kw_buttons(_pos_kw[:30], "pos")
        with _kr:
            st.markdown(
                f'<div class="section-header"><span class="dot"></span>'
                f'WHAT PEOPLE DISLIKED '
                f'<span style="color:var(--muted);font-size:.7rem;font-weight:400;">'
                f'— {len(_neg_texts):,} negative tweets</span></div>',
                unsafe_allow_html=True,
            )
            _render_kw_buttons(_neg_kw[:30], "neg")

        # ── Matching tweets panel (shown when a chip is active) ───────────────
        if st.session_state.kw_selected_term:
            _kw_term  = st.session_state.kw_selected_term
            _kw_sent  = st.session_state.kw_selected_sentiment
            _kw_color = "var(--pos)" if _kw_sent == "pos" else "var(--neg)"
            _kw_hex   = "#20c65a"   if _kw_sent == "pos" else "#ff3d52"
            _kw_label = "positive"  if _kw_sent == "pos" else "negative"

            _kw_pool = df[df["sentiment"] == ("Positive" if _kw_sent == "pos" else "Negative")].copy()
            _kw_mask  = _kw_pool["text"].str.contains(_re.escape(_kw_term), case=False, na=False)
            _kw_matches = _kw_pool[_kw_mask].sort_values("likes", ascending=False).head(10)

            st.markdown(
                f'<div style="background:var(--surface);border:1px solid var(--border);'
                f'border-left:3px solid {_kw_hex};border-radius:0 6px 6px 0;'
                f'padding:.75rem 1.1rem;margin:1.2rem 0 .75rem;">'
                f'<span style="font-size:.7rem;font-weight:700;letter-spacing:.15em;'
                f'text-transform:uppercase;color:{_kw_hex};">TWEETS MENTIONING</span> '
                f'<span style="font-family:Inter Tight,sans-serif;font-weight:800;'
                f'font-size:1.05rem;color:var(--text);">"{_kw_term}"</span> '
                f'<span style="font-size:.75rem;color:var(--muted);">'
                f'— {len(_kw_pool[_kw_mask]):,} {_kw_label} tweets match</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if _kw_matches.empty:
                st.info("No matching tweets.")
            else:
                for _, _row in _kw_matches.iterrows():
                    _raw_text = str(_row["text"])
                    _esc_text = _html.escape(_raw_text)
                    _highlighted = _re.sub(
                        _re.escape(_kw_term),
                        lambda m: f'<strong style="color:{_kw_hex};font-weight:700;">'
                                  + _html.escape(m.group(0)) + '</strong>',
                        _esc_text,
                        flags=_re.IGNORECASE,
                    )
                    _uname   = _html.escape(str(_row["username"]))
                    _created = _html.escape(str(_row.get("created_at", "")))
                    _likes_h = f'<span>♥ {_row["likes"]:,}</span>' if _row["likes"] else ""
                    _rt_h    = f'<span>🔁 {_row["retweets"]:,}</span>' if _row["retweets"] else ""
                    st.markdown(
                        f'<div style="background:var(--surface2);border:1px solid var(--border);'
                        f'border-left:3px solid {_kw_hex};border-radius:0 6px 6px 0;'
                        f'padding:.8rem 1rem .85rem;margin-bottom:.7rem;">'
                        f'<div style="font-size:.7rem;color:var(--muted);margin-bottom:.4rem;'
                        f'display:flex;gap:.8rem;flex-wrap:wrap;">'
                        f'<span>@{_uname}</span><span style="color:var(--muted);">{_created}</span>'
                        f'{_likes_h}{_rt_h}</div>'
                        f'<div style="font-size:.84rem;line-height:1.65;color:var(--text);">'
                        f'{_highlighted}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            _cl_a, _cl_b = st.columns([5, 1])
            with _cl_b:
                st.markdown('<div class="kw-chip-clear">', unsafe_allow_html=True)
                if st.button("✕ Clear", key="kw_clear"):
                    st.session_state.kw_selected_term      = None
                    st.session_state.kw_selected_sentiment = None
                    st.session_state.kw_filter             = ""
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # ── Tweet browser ─────────────────────────────────────────────────────
        st.markdown('<div class="section-header"><span class="dot"></span>TWEET BROWSER</div>', unsafe_allow_html=True)

        _f1, _f2, _f3 = st.columns([2, 2, 2])
        with _f1:
            sent_filter = st.multiselect("Sentiment", ["Positive", "Neutral", "Negative"],
                                         default=["Positive", "Neutral", "Negative"])
        with _f2:
            sort_by = st.selectbox("Sort by", ["Score (↓)", "Score (↑)", "Likes (↓)", "Retweets (↓)"])
        with _f3:
            query_filter = st.multiselect("Query", df["query"].unique().tolist(),
                                          default=df["query"].unique().tolist())

        filtered = df[df["sentiment"].isin(sent_filter) & df["query"].isin(query_filter)].copy()

        if st.session_state.kw_filter:
            filtered = filtered[filtered["text"].str.contains(
                st.session_state.kw_filter, case=False, na=False
            )]

        sort_map = {
            "Score (↓)":    ("score",    False),
            "Score (↑)":    ("score",    True),
            "Likes (↓)":    ("likes",    False),
            "Retweets (↓)": ("retweets", False),
        }
        col, asc = sort_map[sort_by]
        filtered = filtered.sort_values(col, ascending=asc)

        st.markdown(
            f'<div style="font-size:.72rem;color:var(--muted);margin:.5rem 0 1rem;">'
            f'Showing <strong style="color:var(--text);">{len(filtered):,}</strong> of {len(df):,} tweets'
            + (f' · keyword: <strong style="color:var(--blue);">{st.session_state.kw_filter}</strong>' if st.session_state.kw_filter else "")
            + '</div>',
            unsafe_allow_html=True,
        )

        badge_cls = {"Positive": "pos", "Negative": "neg", "Neutral": "neu"}
        for _, row in filtered.head(100).iterrows():
            cls       = badge_cls.get(row["sentiment"], "neu")
            username  = _html.escape(str(row["username"]))
            text      = _html.escape(str(row["text"]))
            reason    = _html.escape(str(row["reason"]))
            created   = _html.escape(str(row.get("created_at", "")))
            score_str = f"{row['score']:+.2f}"
            likes_html = f'<span>♥ {row["likes"]:,}</span>' if row["likes"] else ""
            rt_html    = f'<span>🔁 {row["retweets"]:,}</span>' if row["retweets"] else ""
            st.markdown(f"""
<div class="tweet-card {cls}">
  <div class="tweet-meta">
    <span>@{username}</span>
    <span style="color:var(--muted);">{created}</span>
    {likes_html}
    {rt_html}
    <span class="tweet-badge {cls}">{row["sentiment"]}&nbsp;{score_str}</span>
  </div>
  <div class="tweet-text">{text}</div>
  <div style="font-size:.7rem;color:var(--muted);margin-top:.4rem;">{reason}</div>
</div>
""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        dl_col2, _ = st.columns([1, 5])
        with dl_col2:
            st.download_button(
                "Download all tweets (.csv)",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="twitter_sentiment_tweets.csv",
                mime="text/csv",
                width='stretch',
            )

    # ════════════════════════════════════════════════════════
    # TAB 5 — AI ANALYSIS
    # ════════════════════════════════════════════════════════
    with tab5:
        # Reuse keywords computed in tab4
        pos_kw   = _pos_kw
        neg_kw   = _neg_kw
        only_pos = ", ".join(w for w, _ in pos_kw if w not in _neg_set)[:120]
        only_neg = ", ".join(w for w, _ in neg_kw if w not in _pos_set)[:120]

        st.markdown('<div class="section-header"><span class="dot"></span>AI ANALYSIS</div>', unsafe_allow_html=True)

        if not ANTHROPIC_AVAILABLE:
            st.warning("anthropic not installed. Run: pip install anthropic")
        elif not st.session_state.claude_key:
            st.warning("Enter your Anthropic API key above to use AI Analysis.")
        else:
            # Controls
            ai_col1, ai_col2, ai_col3 = st.columns([2, 2, 1])
            with ai_col1:
                report_focus = st.selectbox("Analysis focus", [
                    "Overall sentiment summary",
                    "Sentiment deep-dive — what drives positive vs negative",
                    "Query comparison — how topics stack up",
                    "Pain points — what's most criticised and why",
                    "Praise — what's most celebrated and why",
                ])
            with ai_col2:
                report_tone = st.selectbox("Output tone", [
                    "Analytical & objective",
                    "Executive summary (brief)",
                    "Consumer research style",
                ])
            with ai_col3:
                ai_model = st.selectbox("Model", ["claude-sonnet-4-6", "claude-opus-4-6"])

            generate_clicked = st.button("GENERATE REPORT", width='stretch')

            # ── Prompt builder ────────────────────────────────
            def build_analysis_prompt(df, sdf, focus, tone):
                n_tweets  = len(df)
                n_queries = sdf["query"].nunique()
                avg_pos   = sdf["positive_pct"].mean()
                spread    = sdf["positive_pct"].max() - sdf["positive_pct"].min() if len(sdf) > 1 else 0
                best      = sdf.iloc[0]["query"]  if len(sdf) else "—"
                worst     = sdf.iloc[-1]["query"] if len(sdf) else "—"

                query_blocks = []
                for _, row in sdf.iterrows():
                    grp = df[df["query"] == row["query"]]
                    top_pos = grp[grp["sentiment"]=="Positive"].nlargest(3, "likes")["text"].tolist()
                    top_neg = grp[grp["sentiment"]=="Negative"].nlargest(3, "likes")["text"].tolist()
                    query_blocks.append(
                        f"Query: {row['query']}\n"
                        f"  Tweets: {row['tweet_count']} | Positive: {row['positive_pct']:.1f}% | Avg Score: {row['avg_score']:+.3f}\n"
                        f"  Avg Likes: {row['avg_likes']:.1f} | Avg RTs: {row['avg_retweets']:.1f}\n"
                        f"  Sample positive tweets: {top_pos}\n"
                        f"  Sample negative tweets: {top_neg}"
                    )

                pos_kw_str = ", ".join(f"{w}({c})" for w, c in pos_kw[:30])
                neg_kw_str = ", ".join(f"{w}({c})" for w, c in neg_kw[:30])

                focus_map = {
                    "Overall sentiment summary": f"""
Provide a comprehensive overview:
1. What is the overall mood across all queries? Is it positive, mixed, or negative?
2. What are the 3-4 dominant themes or topics appearing across tweets?
3. Which queries have the most polarised responses and why?
4. What do the keyword profiles reveal about what people care about?
5. What surprises you most in this data?
Quote specific tweets. Name specific queries. Be concrete.""",

                    "Sentiment deep-dive — what drives positive vs negative": f"""
Analyse the specific drivers of positive and negative sentiment:
1. Identify top 4-5 factors correlating with positive tweets — go beyond surface keywords
2. Identify top 4-5 factors correlating with negative tweets — be specific
3. Compare the emotional language — tone, intensity, specificity
4. Are there keywords appearing in BOTH positive and negative tweets? What does that ambivalence signal?
5. Which queries best exemplify each driver? Quote specific tweet language.
Be analytical. Avoid vague observations.""",

                    "Query comparison — how topics stack up": f"""
Compare all queries head-to-head:
1. Create a ranked leaderboard with specific reasoning for each position
2. For the top queries: what are they doing right that others aren't?
3. For the bottom queries: what specific issues are dragging their scores down?
4. Are there surprising patterns — high engagement but low sentiment, or vice versa?
5. What does the spread between best and worst ({spread:.0f} percentage points) suggest?
Quote tweets. Name queries. Be direct.""",

                    "Pain points — what's most criticised and why": f"""
Deep-dive into negative sentiment:
1. Identify and group all major pain points into 4-6 distinct themes
2. For each theme: how prevalent is it, which queries are most affected, quote specific tweet language
3. Distinguish fixable issues vs fundamental problems
4. Are any pain points unique to specific queries, or are they cross-cutting?
5. Prioritise: if a developer/brand read this, what are the top 3 things to address?
Be specific and direct. Avoid vague summaries.""",

                    "Praise — what's most celebrated and why": f"""
Deep-dive into positive sentiment:
1. Identify and group all major praise themes into 4-6 distinct categories
2. For each theme: how prevalent is it, which queries exemplify it best, quote specific tweet language
3. What aspects are generating genuine enthusiasm vs mild satisfaction?
4. What do the positive differentiator keywords reveal about what this audience uniquely values?
5. What does this praise data suggest about unmet needs others could capitalise on?
Be specific. Quote tweets. Identify what makes top performers genuinely stand out.""",
                }

                tone_map = {
                    "Analytical & objective":
                        "Write in a precise, analytical tone. Use data to support every claim. Avoid hedging language — if the data shows it, state it confidently.",
                    "Executive summary (brief)":
                        "Write as a tight executive briefing. Use headers and bullets. Lead with the single most important finding. Total length: 350-500 words. Every sentence must earn its place.",
                    "Consumer research style":
                        "Write in a formal consumer research report style with numbered sections, clear headings, and a findings + implications structure for each major point.",
                }

                return f"""You are a senior social media analyst with deep expertise in sentiment analysis and consumer psychology. You have been given Twitter data.

Your task is to produce genuinely insightful analysis — not a surface-level summary. Dig into the data. Find patterns. Make arguments. Quote tweets. Be specific. A good analyst doesn't just describe the data; they interpret it.

═══════════════════════════════════════
DATASET OVERVIEW
═══════════════════════════════════════
Total tweets: {n_tweets:,} across {n_queries} queries
Average positive sentiment: {avg_pos:.1f}%
Sentiment spread: {spread:.0f}pp (best: {best}, worst: {worst})

═══════════════════════════════════════
PER-QUERY DATA (sorted best → worst)
═══════════════════════════════════════
{"".join(chr(10)*2 + b for b in query_blocks)}

═══════════════════════════════════════
CROSS-QUERY KEYWORD FREQUENCIES
═══════════════════════════════════════
Positive tweets — top 30 terms: {pos_kw_str}
Negative tweets — top 30 terms: {neg_kw_str}
Differentiator keywords (positive only): {only_pos}
Differentiator keywords (negative only): {only_neg}

═══════════════════════════════════════
YOUR TASK
═══════════════════════════════════════
{focus_map[focus]}

OUTPUT TONE: {tone_map[tone]}

HARD RULES:
- Every claim must reference specific data from this brief (query names, keywords, tweet quotes, numbers)
- Do not write generic observations that could apply to any dataset
- Do not pad with transitions or summaries — every paragraph must contain new analysis
- Use markdown formatting with clear section headers"""

            # ── Generate ──────────────────────────────────────
            if generate_clicked:
                st.session_state.ai_report = ""
                prompt = build_analysis_prompt(df, sdf, report_focus, report_tone)
                report_placeholder = st.empty()
                status_placeholder = st.empty()
                full_text = ""

                try:
                    client = _anthropic.Anthropic(api_key=st.session_state.claude_key)
                    status_placeholder.markdown(
                        '<div style="font-size:.78rem;color:var(--muted);">Connecting to Claude…</div>',
                        unsafe_allow_html=True,
                    )
                    with client.messages.stream(
                        model=ai_model,
                        max_tokens=4096,
                        system=(
                            "You are a senior social media analyst. "
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
                dl_col3, _ = st.columns([1, 4])
                with dl_col3:
                    st.download_button(
                        "Download report (.md)",
                        data=st.session_state.ai_report,
                        file_name=f"twitter_analysis_{'_'.join(st.session_state.last_queries[:2]).replace(' ','_')}.md",
                        mime="text/markdown",
                        width='stretch',
                    )

# ─────────────────────────────────────────────────────────────
# EMPTY STATE
# ─────────────────────────────────────────────────────────────

elif not st.session_state.results_df:
    st.markdown("""
    <div class="empty-state">
      <div class="empty-title">NO DATA YET</div>
      <div class="empty-sub">
        Enter a query above and click <strong style="color:var(--blue);">Fetch &amp; Analyse</strong>
        to pull tweets and run sentiment analysis.
      </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="footer">
  <div class="footer-brand">SEGA TWITTER LENS</div>
  <div class="footer-note">Data sourced from Twitter/X API v2 · Internal analytics use only</div>
</div>
""", unsafe_allow_html=True)