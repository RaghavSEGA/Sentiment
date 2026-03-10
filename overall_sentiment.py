"""
SEGA Unified Social Intelligence Platform
==========================================
Unified dashboard aggregating Reddit, X/Twitter, Discord, Steam,
Market Intelligence, and Wishlist/Traffic tracking.

Business Requirements Addressed:
  1. External title wishlist & traffic numbers (SteamSpy/SteamDB)
  2. Reddit + X + Discord aggregated marketing dashboard
  3. Steam Community Hub follower/member counts across time periods
  4. Genre-agnostic Market Intelligence (formerly Shooter-only)
  5. Reddit posts (not just comments)
  6. Full Japanese translation support

Run with:  streamlit run sega_unified_dashboard.py
Required:  pip install streamlit requests pandas plotly anthropic
           matplotlib wordcloud vaderSentiment tweepy reportlab markdown
"""

import re, time, io, json, os
from datetime import datetime, timedelta
from collections import Counter
from pathlib import Path

import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── Optional dependencies ──────────────────────────────────────
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
    import tweepy
    TWEEPY_OK = True
except ImportError:
    TWEEPY_OK = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors as _rlc
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Preformatted
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

try:
    import markdown as _md_lib
    MARKDOWN_OK = True
except ImportError:
    MARKDOWN_OK = False

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SEGA Social Intelligence Platform",
    page_icon=":material/analytics:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# TRANSLATIONS (EN / JA) — Requirement 6
# ─────────────────────────────────────────────────────────────
TRANSLATIONS = {
    "en": {
        # Nav
        "app_title": "SEGA SOCIAL INTELLIGENCE",
        "app_subtitle": "Unified Marketing Analytics Platform",
        "nav_reddit": "Reddit",
        "nav_twitter": "X / Twitter",
        "nav_discord": "Discord",
        "nav_steam_reviews": "Steam Reviews",
        "nav_steam_community": "Steam Community",
        "nav_wishlist": "Wishlist & Traffic",
        "nav_market_intel": "Market Intel",
        "lang_label": "Language / 言語",
        # Common
        "fetch": "Fetch",
        "analyse": "Analyse",
        "generate_report": "✨ Generate AI Report",
        "no_data": "NO DATA YET",
        "loading": "Loading…",
        "genre": "Genre / Topic",
        "game_title": "Game Title",
        "subreddits": "Subreddits",
        "posts_label": "Posts",
        "comments_label": "Comments",
        "sentiment_label": "Sentiment",
        "positive": "Positive",
        "negative": "Negative",
        "neutral": "Neutral",
        "score": "Score",
        "date": "Date",
        "download_csv": "⬇ Download CSV",
        "download_report": "DOWNLOAD REPORT",
        "dl_md": "⬇ Markdown",
        "dl_html": "⬇ HTML",
        "dl_pdf": "⬇ PDF",
        "chat_placeholder": "Ask a follow-up question…",
        "clear_chat": "Clear chat",
        "api_key_hint": "Enter your Claude API key",
        "twitter_bearer_hint": "Twitter/X Bearer Token",
        "discord_token_hint": "Discord Bot Token",
        # Reddit
        "reddit_title": "Reddit Sentiment Lens",
        "reddit_sub": "Analyse community sentiment across subreddits — posts & comments",
        "fetch_posts": "Fetch Posts & Comments",
        "posts_per_sub": "Posts per subreddit",
        "post_content_type": "Content to fetch",
        "content_posts_only": "Posts only",
        "content_posts_comments": "Posts + Comments",
        # Twitter
        "twitter_title": "X / Twitter Sentiment Lens",
        "twitter_sub": "Track real-time sentiment across queries and hashtags",
        "queries_label": "Search queries (one per line)",
        "max_tweets": "Max tweets per query",
        "fetch_analyse": "Fetch & Analyse",
        # Discord
        "discord_title": "Discord Community Lens",
        "discord_sub": "Monitor community sentiment across Discord servers",
        "server_id": "Server / Channel ID(s)",
        "message_limit": "Messages to fetch",
        # Steam Reviews
        "steam_reviews_title": "Steam Review Analyser",
        "steam_reviews_sub": "Deep dive into player reviews across any genre",
        "search_genre": "Search Genre",
        "found_games": "Found Games",
        # Steam Community
        "steam_community_title": "Steam Community Hub",
        "steam_community_sub": "Track follower & member counts across time periods",
        "community_game": "Game name or App ID",
        "time_period": "Time period",
        "period_7d": "Last 7 days",
        "period_30d": "Last 30 days",
        "period_90d": "Last 90 days",
        "period_1y": "Last 1 year",
        "period_all": "All time",
        "members": "Members",
        "followers": "Followers",
        "in_game": "In-game",
        "fetch_community": "Fetch Community Stats",
        # Wishlist & Traffic
        "wishlist_title": "Wishlist & Traffic Tracker",
        "wishlist_sub": "External title wishlist counts, player traffic & market visibility",
        "wishlist_count": "Wishlist Count",
        "owners": "Owners (estimated)",
        "peak_ccu": "Peak CCU",
        "avg_playtime": "Avg Playtime (hrs)",
        "price": "Price",
        "reviews_total": "Total Reviews",
        "fetch_wishlist": "Fetch Market Data",
        "compare_titles": "Compare titles (one per line)",
        # Market Intel
        "market_title": "Market Intelligence",
        "market_sub": "Genre-agnostic competitive analysis — CCU, reviews, trends",
        "select_genre_intel": "Select genre for analysis",
        "fetch_ccu": "Fetch Live CCU",
        "analysis_type": "Analysis type",
        "an_ccu": "CCU Landscape",
        "an_table": "Table Stakes",
        "an_social": "Social Metrics",
        "an_weekly": "Weekly Report",
        "an_custom": "Custom Query",
        "custom_query": "Custom analysis question",
        # Errors
        "err_no_key": "Add CLAUDE_KEY to Streamlit secrets or enter it in the sidebar.",
        "err_auth": "Invalid API key.",
        "err_rate": "Rate limit — wait and retry.",
        "err_tweepy": "Install `tweepy` to use Twitter features.",
        "err_vader": "Install `vaderSentiment` for local sentiment analysis.",
    },
    "ja": {
        # Nav
        "app_title": "SEGAソーシャルインテリジェンス",
        "app_subtitle": "統合マーケティング分析プラットフォーム",
        "nav_reddit": "Reddit",
        "nav_twitter": "X / Twitter",
        "nav_discord": "Discord",
        "nav_steam_reviews": "Steamレビュー",
        "nav_steam_community": "Steamコミュニティ",
        "nav_wishlist": "ウィッシュリスト・流量",
        "nav_market_intel": "市場インテリジェンス",
        "lang_label": "Language / 言語",
        # Common
        "fetch": "取得",
        "analyse": "分析",
        "generate_report": "✨ AIレポート生成",
        "no_data": "データなし",
        "loading": "読み込み中…",
        "genre": "ジャンル / トピック",
        "game_title": "ゲームタイトル",
        "subreddits": "サブレディット",
        "posts_label": "投稿",
        "comments_label": "コメント",
        "sentiment_label": "センチメント",
        "positive": "ポジティブ",
        "negative": "ネガティブ",
        "neutral": "ニュートラル",
        "score": "スコア",
        "date": "日付",
        "download_csv": "⬇ CSV ダウンロード",
        "download_report": "レポートダウンロード",
        "dl_md": "⬇ Markdown",
        "dl_html": "⬇ HTML",
        "dl_pdf": "⬇ PDF",
        "chat_placeholder": "フォローアップの質問を入力…",
        "clear_chat": "チャットをクリア",
        "api_key_hint": "Claude APIキーを入力",
        "twitter_bearer_hint": "Twitter/X Bearerトークン",
        "discord_token_hint": "Discord Botトークン",
        # Reddit
        "reddit_title": "Redditセンチメントレンズ",
        "reddit_sub": "サブレディット全体のコミュニティセンチメントを分析 — 投稿・コメント",
        "fetch_posts": "投稿・コメントを取得",
        "posts_per_sub": "サブレディットごとの投稿数",
        "post_content_type": "取得コンテンツ",
        "content_posts_only": "投稿のみ",
        "content_posts_comments": "投稿＋コメント",
        # Twitter
        "twitter_title": "X / Twitterセンチメントレンズ",
        "twitter_sub": "クエリ・ハッシュタグ全体のリアルタイムセンチメントを追跡",
        "queries_label": "検索クエリ（1行に1件）",
        "max_tweets": "クエリごとの最大ツイート数",
        "fetch_analyse": "取得・分析",
        # Discord
        "discord_title": "Discordコミュニティレンズ",
        "discord_sub": "Discordサーバーのコミュニティセンチメントを監視",
        "server_id": "サーバー／チャンネルID",
        "message_limit": "取得メッセージ数",
        # Steam Reviews
        "steam_reviews_title": "Steamレビューアナライザー",
        "steam_reviews_sub": "あらゆるジャンルのプレイヤーレビューを詳細分析",
        "search_genre": "ジャンルを検索",
        "found_games": "ゲームが見つかりました",
        # Steam Community
        "steam_community_title": "SteamコミュニティHub",
        "steam_community_sub": "各期間のフォロワー数・メンバー数を追跡",
        "community_game": "ゲーム名またはApp ID",
        "time_period": "期間",
        "period_7d": "直近7日間",
        "period_30d": "直近30日間",
        "period_90d": "直近90日間",
        "period_1y": "直近1年間",
        "period_all": "全期間",
        "members": "メンバー数",
        "followers": "フォロワー数",
        "in_game": "プレイ中",
        "fetch_community": "コミュニティ統計を取得",
        # Wishlist & Traffic
        "wishlist_title": "ウィッシュリスト・流量トラッカー",
        "wishlist_sub": "外部タイトルのウィッシュリスト数・プレイヤー流量・市場視認性",
        "wishlist_count": "ウィッシュリスト数",
        "owners": "オーナー数（推定）",
        "peak_ccu": "ピークCCU",
        "avg_playtime": "平均プレイ時間（時間）",
        "price": "価格",
        "reviews_total": "総レビュー数",
        "fetch_wishlist": "市場データを取得",
        "compare_titles": "比較タイトル（1行に1件）",
        # Market Intel
        "market_title": "市場インテリジェンス",
        "market_sub": "ジャンル横断の競合分析 — CCU・レビュー・トレンド",
        "select_genre_intel": "分析ジャンルを選択",
        "fetch_ccu": "ライブCCUを取得",
        "analysis_type": "分析タイプ",
        "an_ccu": "CCUランドスケープ",
        "an_table": "テーブルステークス",
        "an_social": "ソーシャル指標",
        "an_weekly": "週次レポート",
        "an_custom": "カスタムクエリ",
        "custom_query": "カスタム分析の質問",
        # Errors
        "err_no_key": "StreamlitシークレットにまたはサイドバーにクロードAPIキーを追加してください。",
        "err_auth": "APIキーが無効です。",
        "err_rate": "レート制限 — 少し待ってから再試行してください。",
        "err_tweepy": "Twitter機能を使用するには`tweepy`をインストールしてください。",
        "err_vader": "ローカルセンチメント分析には`vaderSentiment`をインストールしてください。",
    },
}

def T(key: str) -> str:
    lang = st.session_state.get("lang", "en")
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)

# ─────────────────────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────────────────────
_defaults = {
    "lang": "en",
    "active_tab": "reddit",
    "claude_key": "",
    "twitter_bearer": "",
    "discord_token": "",
    # Reddit
    "reddit_posts": [],
    "reddit_comments": [],
    "reddit_fetched": False,
    # Twitter
    "twitter_df": None,
    "twitter_fetched": False,
    # Discord
    "discord_df": None,
    "discord_fetched": False,
    # Steam Reviews
    "steam_games": [],
    "steam_reviews_df": None,
    "steam_fetched": False,
    # Steam Community
    "community_data": {},
    "community_fetched": False,
    # Wishlist
    "wishlist_data": [],
    "wishlist_fetched": False,
    # Market Intel
    "market_ccu": [],
    "market_fetched": False,
    "market_genre": "RPG",
    # AI
    "ai_report": "",
    "ai_chat_history": [],
    "ai_chat_pending": False,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────
STOPWORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","with",
    "is","it","its","this","that","was","are","be","as","i","my","we","you",
    "they","he","she","not","do","did","has","have","had","will","just","can",
    "so","if","about","by","from","what","how","when","no","up","out","get",
    "all","more","your","their","been","very","into","which","would","like",
    "than","after","also","than","game","games","want","need","love","hate",
}

def keywords(texts, n=20):
    words = []
    for t in texts:
        for w in re.sub(r"[^a-z\s]", "", str(t).lower()).split():
            if w not in STOPWORDS and len(w) > 3:
                words.append(w)
    return Counter(words).most_common(n)

def sentiment_label(score: float) -> str:
    lang = st.session_state.get("lang", "en")
    if score >= 0.05:
        return T("positive") if lang == "ja" else "Positive"
    if score <= -0.05:
        return T("negative") if lang == "ja" else "Negative"
    return T("neutral") if lang == "ja" else "Neutral"

def vader_score(text: str) -> float:
    if VADER_OK:
        return _Vader().polarity_scores(str(text))["compound"]
    # Naive fallback
    pos_words = {"good","great","amazing","love","best","awesome","excellent","fun","enjoyed","perfect"}
    neg_words = {"bad","terrible","awful","hate","worst","broken","garbage","horrible","disappointing"}
    words = set(str(text).lower().split())
    return min(1.0, max(-1.0, (len(words & pos_words) - len(words & neg_words)) * 0.15))

def section_header(title: str):
    st.markdown(
        f'<div class="section-header"><span class="dot"></span>{title}</div>',
        unsafe_allow_html=True,
    )

def metric_row(metrics: list[dict]):
    """metrics: list of {label, value, delta?, color?}"""
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        color = m.get("color", "var(--blue)")
        delta = m.get("delta", "")
        delta_html = f'<div class="metric-delta">{delta}</div>' if delta else ""
        col.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-label">{m["label"]}</div>'
            f'<div class="metric-value" style="color:{color}">{m["value"]}</div>'
            f'{delta_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

def plotly_dark_layout(title=""):
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#b8bcd4", family="Poppins"),
        title=dict(text=title, font=dict(color="#eef0fa", size=14, family="Inter Tight"), x=0.01),
        xaxis=dict(gridcolor="#232640", zerolinecolor="#232640"),
        yaxis=dict(gridcolor="#232640", zerolinecolor="#232640"),
        margin=dict(l=40, r=20, t=50, b=40),
    )

def report_to_html(text: str) -> str:
    body = _md_lib.markdown(text) if MARKDOWN_OK else f"<pre>{text}</pre>"
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>SEGA Report</title>
<style>body{{font-family:sans-serif;max-width:900px;margin:40px auto;line-height:1.6;}}
h1,h2,h3{{color:#1a3acc;}}pre{{background:#f4f4f4;padding:1em;border-radius:4px;}}
</style></head><body>{body}</body></html>"""

def report_to_pdf(text: str) -> bytes | None:
    if not REPORTLAB_OK:
        return None
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=18,
                        textColor=_rlc.HexColor("#1a3acc"), spaceAfter=10)
    H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=14,
                        textColor=_rlc.HexColor("#1a3acc"), spaceAfter=8)
    BODY = ParagraphStyle("BODY", parent=styles["Normal"], fontSize=10, leading=15, spaceAfter=6)
    story = []
    for line in text.split("\n"):
        if line.startswith("# "): story.append(Paragraph(line[2:], H1))
        elif line.startswith("## "): story.append(Paragraph(line[3:], H2))
        elif line.startswith("- "): story.append(Paragraph(f"• {line[2:]}", BODY))
        elif line.strip() == "": story.append(Spacer(1, 6))
        else: story.append(Paragraph(line, BODY))
    doc.build(story)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────
# STEAM API HELPERS
# ─────────────────────────────────────────────────────────────
STEAM_SEARCH = "https://store.steampowered.com/api/storesearch/"
STEAM_REVIEWS = "https://store.steampowered.com/appreviews/{appid}"
STEAM_APPDETAILS = "https://store.steampowered.com/api/appdetails"
STEAM_SPY = "https://steamspy.com/api.php"
STEAM_COMMUNITY_API = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"

def steam_search_game(query: str, max_results=10) -> list[dict]:
    try:
        r = requests.get(STEAM_SEARCH, params={"term": query, "l": "english", "cc": "us"}, timeout=10)
        items = r.json().get("items", [])
        return [{"appid": i["id"], "name": i["name"], "tiny_image": i.get("tiny_image","")} for i in items[:max_results]]
    except Exception:
        return []

def steam_game_details(appid: int) -> dict:
    try:
        r = requests.get(STEAM_APPDETAILS, params={"appids": appid, "cc": "us", "l": "english"}, timeout=10)
        data = r.json().get(str(appid), {}).get("data", {})
        return data
    except Exception:
        return {}

def steamspy_data(appid: int) -> dict:
    """SteamSpy provides owners, wishlists (limited), CCU estimates — Req 1 & 3"""
    try:
        r = requests.get(STEAM_SPY, params={"request": "appdetails", "appid": appid}, timeout=10)
        return r.json()
    except Exception:
        return {}

def steamspy_genre(genre: str, max_pages=2) -> list[dict]:
    games = []
    for page in range(max_pages):
        try:
            r = requests.get(STEAM_SPY, params={"request": "genre", "genre": genre, "page": page}, timeout=12)
            data = r.json()
            if not data:
                break
            games.extend(list(data.values()))
            time.sleep(0.5)
        except Exception:
            break
    return games

def steam_reviews_fetch(appid: int, n: int = 100) -> list[dict]:
    reviews, cursor = [], "*"
    while len(reviews) < n:
        try:
            r = requests.get(
                STEAM_REVIEWS.format(appid=appid),
                params={"json": 1, "num_per_page": min(100, n - len(reviews)),
                        "cursor": cursor, "filter": "recent", "language": "english"},
                timeout=10,
            )
            data = r.json()
            batch = data.get("reviews", [])
            if not batch:
                break
            reviews.extend(batch)
            cursor = data.get("cursor", "")
            if not cursor:
                break
            time.sleep(0.3)
        except Exception:
            break
    return reviews[:n]

def steam_community_stats(appid: int) -> dict:
    """Req 3: Steam Community Hub follower/member data"""
    result = {}
    # Current players via Steam API
    try:
        r = requests.get(STEAM_COMMUNITY_API, params={"appid": appid}, timeout=8)
        result["current_players"] = r.json().get("response", {}).get("player_count", 0)
    except Exception:
        result["current_players"] = 0

    # SteamSpy for total owners + CCU
    spy = steamspy_data(appid)
    result["owners_est"] = spy.get("owners", "N/A")
    result["peak_ccu"] = spy.get("peak_ccu", 0)
    result["ccu"] = spy.get("ccu", 0)
    result["name"] = spy.get("name", "")
    result["positive"] = spy.get("positive", 0)
    result["negative"] = spy.get("negative", 0)
    result["average_forever"] = spy.get("average_forever", 0)  # avg playtime mins

    # Community hub member count via store page (scrape public data)
    try:
        r = requests.get(
            f"https://store.steampowered.com/app/{appid}/",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        html = r.text
        # Community members
        import re as _re
        m = _re.search(r'"group_members_count":\s*"?([\d,]+)"?', html)
        if m:
            result["community_members"] = int(m.group(1).replace(",", ""))
        m2 = _re.search(r'"FollowerCount":\s*(\d+)', html)
        if m2:
            result["followers"] = int(m2.group(1))
    except Exception:
        pass

    return result

# ─────────────────────────────────────────────────────────────
# REDDIT HELPERS (no API key) — Req 5: posts primary
# ─────────────────────────────────────────────────────────────
REDDIT_SEARCH = "https://www.reddit.com/search.json"
REDDIT_SUB_NEW = "https://www.reddit.com/r/{sub}/new.json"
REDDIT_SUB_HOT = "https://www.reddit.com/r/{sub}/hot.json"
REDDIT_COMMENTS = "https://www.reddit.com{permalink}.json"
_REDDIT_HEADERS = {"User-Agent": "SEGASocialLens/2.0 (+research)"}

def reddit_fetch_posts(subreddit: str, limit: int = 25, sort: str = "hot") -> list[dict]:
    """Req 5: fetch posts (not just comments)"""
    url = REDDIT_SUB_HOT.format(sub=subreddit) if sort == "hot" else REDDIT_SUB_NEW.format(sub=subreddit)
    posts = []
    after = None
    while len(posts) < limit:
        params = {"limit": min(100, limit - len(posts)), "raw_json": 1}
        if after:
            params["after"] = after
        try:
            r = requests.get(url, headers=_REDDIT_HEADERS, params=params, timeout=12)
            data = r.json()["data"]
            children = data.get("children", [])
            for c in children:
                p = c["data"]
                posts.append({
                    "type": "post",
                    "id": p.get("id",""),
                    "subreddit": p.get("subreddit",""),
                    "title": p.get("title",""),
                    "selftext": p.get("selftext","")[:500],
                    "full_text": (p.get("title","") + " " + p.get("selftext",""))[:800],
                    "score": p.get("score", 0),
                    "num_comments": p.get("num_comments", 0),
                    "date": datetime.utcfromtimestamp(p.get("created_utc", 0)),
                    "permalink": "https://reddit.com" + p.get("permalink",""),
                    "url": p.get("url",""),
                    "author": p.get("author",""),
                    "upvote_ratio": p.get("upvote_ratio", 0.5),
                    "flair": p.get("link_flair_text",""),
                })
            after = data.get("after")
            if not after:
                break
            time.sleep(0.5)
        except Exception:
            break
    return posts[:limit]

def reddit_fetch_comments(permalink: str, limit: int = 20) -> list[dict]:
    comments = []
    try:
        r = requests.get(REDDIT_COMMENTS.format(permalink=permalink.rstrip("/")),
                         headers=_REDDIT_HEADERS,
                         params={"limit": limit, "depth": 2, "raw_json": 1}, timeout=12)
        data = r.json()
        if len(data) < 2:
            return comments
        for c in data[1]["data"]["children"]:
            if c["kind"] == "t1":
                d = c["data"]
                comments.append({
                    "type": "comment",
                    "id": d.get("id",""),
                    "subreddit": d.get("subreddit",""),
                    "full_text": d.get("body","")[:500],
                    "score": d.get("score", 0),
                    "date": datetime.utcfromtimestamp(d.get("created_utc", 0)),
                    "permalink": "https://reddit.com" + d.get("permalink",""),
                    "author": d.get("author",""),
                    "title": "",
                })
    except Exception:
        pass
    return comments

def reddit_search_posts(query: str, subreddit: str = "", limit: int = 25) -> list[dict]:
    """Search posts by keyword across Reddit or within a subreddit"""
    posts = []
    params = {"q": query, "limit": min(100, limit), "sort": "relevance",
              "t": "month", "raw_json": 1, "type": "link"}
    if subreddit:
        params["restrict_sr"] = "on"
        url = f"https://www.reddit.com/r/{subreddit}/search.json"
    else:
        url = REDDIT_SEARCH
    try:
        r = requests.get(url, headers=_REDDIT_HEADERS, params=params, timeout=12)
        children = r.json()["data"]["children"]
        for c in children:
            p = c["data"]
            posts.append({
                "type": "post",
                "id": p.get("id",""),
                "subreddit": p.get("subreddit",""),
                "title": p.get("title",""),
                "selftext": p.get("selftext","")[:500],
                "full_text": (p.get("title","") + " " + p.get("selftext",""))[:800],
                "score": p.get("score", 0),
                "num_comments": p.get("num_comments", 0),
                "date": datetime.utcfromtimestamp(p.get("created_utc", 0)),
                "permalink": "https://reddit.com" + p.get("permalink",""),
                "url": p.get("url",""),
                "author": p.get("author",""),
                "upvote_ratio": p.get("upvote_ratio", 0.5),
                "flair": p.get("link_flair_text",""),
            })
    except Exception:
        pass
    return posts[:limit]

# ─────────────────────────────────────────────────────────────
# DISCORD HELPERS (Bot Token)
# ─────────────────────────────────────────────────────────────
def discord_fetch_messages(channel_id: str, token: str, limit: int = 100) -> list[dict]:
    messages = []
    url = f"https://discord.com/api/v10/channels/{channel_id.strip()}/messages"
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    before = None
    while len(messages) < limit:
        params = {"limit": min(100, limit - len(messages))}
        if before:
            params["before"] = before
        try:
            r = requests.get(url, headers=headers, params=params, timeout=10)
            if r.status_code != 200:
                break
            batch = r.json()
            if not batch:
                break
            for m in batch:
                messages.append({
                    "id": m["id"],
                    "author": m["author"]["username"],
                    "content": m.get("content",""),
                    "timestamp": m["timestamp"],
                    "reactions": sum(r["count"] for r in m.get("reactions",[])),
                })
            before = batch[-1]["id"]
            time.sleep(0.3)
        except Exception:
            break
    return messages[:limit]

# ─────────────────────────────────────────────────────────────
# AI REPORT GENERATION
# ─────────────────────────────────────────────────────────────
ai_model = "claude-sonnet-4-20250514"

def get_claude_key() -> str:
    k = st.session_state.get("claude_key","").strip()
    if k:
        return k
    try:
        return st.secrets.get("CLAUDE_KEY","")
    except Exception:
        return ""

def stream_ai_report(prompt: str, system: str = "") -> str:
    key = get_claude_key()
    if not key or not ANTHROPIC_OK:
        return ""
    client = _anthropic.Anthropic(api_key=key)
    ph = st.empty(); txt = ""
    try:
        kwargs = dict(model=ai_model, max_tokens=4096,
                      messages=[{"role": "user", "content": prompt}])
        if system:
            kwargs["system"] = system
        with client.messages.stream(**kwargs) as s:
            for d in s.text_stream:
                txt += d; ph.markdown(txt + "▌")
        ph.markdown(txt)
    except _anthropic.AuthenticationError:
        st.error(T("err_auth"))
    except _anthropic.RateLimitError:
        st.error(T("err_rate"))
    except Exception as e:
        st.error(f"{type(e).__name__}: {e}")
    return txt

def render_ai_tab(report_key: str, prompt_fn, chat_system_fn=None, slug: str = "report"):
    key = get_claude_key()
    if not key:
        st.warning(T("err_no_key"))
        return
    if not st.session_state.get(report_key):
        if st.button(T("generate_report"), key=f"gen_{report_key}"):
            report = stream_ai_report(prompt_fn())
            st.session_state[report_key] = report
    else:
        st.markdown(st.session_state[report_key])

    if st.session_state.get(report_key):
        _show_download_buttons(st.session_state[report_key], slug)
        if chat_system_fn:
            _render_chat(report_key, chat_system_fn)

def _show_download_buttons(report: str, slug: str):
    st.markdown(f'<div style="font-size:.62rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);margin-bottom:.5rem;">{T("download_report")}</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(T("dl_md"), data=report, file_name=f"sega_{slug}.md", mime="text/markdown", key=f"dl_md_{slug}")
    with c2:
        st.download_button(T("dl_html"), data=report_to_html(report).encode(), file_name=f"sega_{slug}.html", mime="text/html", key=f"dl_html_{slug}")
    with c3:
        pdf = report_to_pdf(report)
        if pdf:
            st.download_button(T("dl_pdf"), data=pdf, file_name=f"sega_{slug}.pdf", mime="application/pdf", key=f"dl_pdf_{slug}")
        else:
            st.caption("PDF: install `reportlab`")

def _render_chat(report_key: str, system_fn):
    st.markdown("<br>", unsafe_allow_html=True)
    section_header("FOLLOW-UP CHAT")
    chat_key = f"chat_{report_key}"
    pending_key = f"pending_{report_key}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []
    if pending_key not in st.session_state:
        st.session_state[pending_key] = False

    for msg in st.session_state[chat_key]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if st.session_state[pending_key]:
        st.session_state[pending_key] = False
        key = get_claude_key()
        client = _anthropic.Anthropic(api_key=key)
        with st.chat_message("assistant"):
            ph = st.empty(); rep = ""
            try:
                with client.messages.stream(
                    model=ai_model, max_tokens=2048,
                    system=system_fn(),
                    messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state[chat_key]],
                ) as s:
                    for d in s.text_stream:
                        rep += d; ph.markdown(rep + "▌")
                ph.markdown(rep)
                st.session_state[chat_key].append({"role": "assistant", "content": rep})
            except Exception as e:
                st.error(f"Chat error: {e}")

    um = st.chat_input(T("chat_placeholder"), key=f"ci_{report_key}")
    if um:
        st.session_state[chat_key].append({"role": "user", "content": um})
        st.session_state[pending_key] = True
        st.rerun()

    if st.session_state.get(chat_key):
        if st.button(T("clear_chat"), key=f"clr_{report_key}"):
            st.session_state[chat_key] = []
            st.session_state[pending_key] = False
            st.rerun()

# ─────────────────────────────────────────────────────────────
# GENRE PRESETS
# ─────────────────────────────────────────────────────────────
GENRE_PRESETS = {
    "RPG": {
        "steam_tag": "RPG",
        "subreddits": ["rpg", "JRPG", "Games", "gaming"],
        "steamspy_genre": "RPG",
    },
    "Action": {
        "steam_tag": "Action",
        "subreddits": ["gaming", "Games", "patientgamers"],
        "steamspy_genre": "Action",
    },
    "Shooter": {
        "steam_tag": "Shooter",
        "subreddits": ["FPS", "Games", "gaming", "competitivegaming"],
        "steamspy_genre": "Action",
    },
    "Strategy": {
        "steam_tag": "Strategy",
        "subreddits": ["4Xgaming", "strategy", "Games"],
        "steamspy_genre": "Strategy",
    },
    "MOBA": {
        "steam_tag": "MOBA",
        "subreddits": ["DotA2", "leagueoflegends", "Games"],
        "steamspy_genre": "Free to Play",
    },
    "Battle Royale": {
        "steam_tag": "Battle Royale",
        "subreddits": ["FortNiteBR", "apexlegends", "gaming"],
        "steamspy_genre": "Free to Play",
    },
    "Sports": {
        "steam_tag": "Sports",
        "subreddits": ["sportsaregames", "FIFA", "Games"],
        "steamspy_genre": "Sports",
    },
    "Racing": {
        "steam_tag": "Racing",
        "subreddits": ["simracing", "Gaming", "granturismo"],
        "steamspy_genre": "Racing",
    },
    "Horror": {
        "steam_tag": "Horror",
        "subreddits": ["survivalhorrorgaming", "Games", "gaming"],
        "steamspy_genre": "Action",
    },
    "Simulation": {
        "steam_tag": "Simulation",
        "subreddits": ["patientgamers", "Games", "gaming"],
        "steamspy_genre": "Simulation",
    },
    "Custom": {
        "steam_tag": "",
        "subreddits": [],
        "steamspy_genre": "",
    },
}

# ─────────────────────────────────────────────────────────────
# CSS STYLES
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;700;800;900&family=Poppins:wght@300;400;500;600&display=swap');

:root,html[data-theme="light"],html[data-theme="dark"],[data-theme="light"],[data-theme="dark"]{
  color-scheme:dark!important;
  --bg:#060810;--surface:#0c0e1c;--surface2:#111328;--surface3:#181b2e;
  --border:#1e2238;--border-hi:#2d3155;
  --blue:#4080ff;--blue-lo:#1a3acc;
  --blue-glow:rgba(64,128,255,.16);--blue-glow-hi:rgba(64,128,255,.28);
  --text:#eef0fa;--text-dim:#b8bcd4;--muted:#555a7a;
  --pos:#20c65a;--pos-dim:rgba(32,198,90,.12);
  --neg:#ff3d52;--neg-dim:rgba(255,61,82,.12);
  --amber:#ffb938;--amber-dim:rgba(255,185,56,.12);
  --purple:#a855f7;--purple-dim:rgba(168,85,247,.12);
  --cyan:#22d3ee;--cyan-dim:rgba(34,211,238,.12);
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
.block-container{padding:0 2rem 4rem!important;max-width:1480px!important;}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-thumb{background:var(--border-hi);border-radius:4px;}

/* ─── TOP BAR ─── */
.topbar{background:var(--surface);border-bottom:1px solid var(--border);
  padding:.7rem 2rem;margin:0 -2rem 1.5rem;display:flex;align-items:center;gap:1.2rem;position:relative;}
.topbar::after{content:'';position:absolute;bottom:-1px;left:0;right:0;height:1px;
  background:linear-gradient(90deg,var(--blue) 0%,rgba(64,128,255,0) 50%);}
.topbar-logo{font-family:'Inter Tight',sans-serif;font-size:.9rem;font-weight:900;
  color:var(--text)!important;letter-spacing:.12em;text-transform:uppercase;}
.topbar-logo .seg{color:var(--blue);}
.topbar-div{width:1px;height:16px;background:var(--border-hi);flex-shrink:0;}
.topbar-label{font-size:.55rem;font-weight:600;color:var(--muted)!important;letter-spacing:.2em;text-transform:uppercase;}
.topbar-pill{margin-left:auto;background:var(--blue-glow);border:1px solid rgba(64,128,255,.28);
  border-radius:20px;padding:.15rem .65rem;font-size:.55rem;font-weight:700;
  letter-spacing:.14em;text-transform:uppercase;color:var(--blue)!important;}

/* ─── MODULE NAV ─── */
.module-nav{display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:1.5rem;}
.mod-btn{background:var(--surface);border:1px solid var(--border);border-radius:6px;
  padding:.45rem 1rem;font-size:.72rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;
  color:var(--text-dim)!important;cursor:pointer;transition:all .15s;white-space:nowrap;}
.mod-btn:hover{border-color:var(--blue);color:var(--text)!important;}
.mod-btn.active{background:var(--blue-glow);border-color:var(--blue);color:var(--blue)!important;
  box-shadow:0 0 0 1px rgba(64,128,255,.2);}
.mod-icon{margin-right:.4rem;font-size:.8rem;}

/* ─── HERO ─── */
.hero{padding:1.2rem 0 .75rem;}
.hero-title{font-family:'Inter Tight',sans-serif;font-size:2.2rem;font-weight:900;
  line-height:1.05;color:var(--text)!important;letter-spacing:-.03em;margin-bottom:.4rem;}
.hero-title .accent{color:var(--blue);}
.hero-sub{font-size:.84rem;font-weight:300;color:var(--muted)!important;max-width:560px;line-height:1.65;}

/* ─── QUERY BLOCK ─── */
.query-block{background:var(--surface);border:1px solid var(--border);
  border-top:2px solid var(--blue);border-radius:0 0 10px 10px;padding:1.3rem 1.6rem 1.1rem;margin:.6rem 0 0;}
.field-label{font-size:.56rem;font-weight:700;letter-spacing:.22em;text-transform:uppercase;
  color:var(--muted)!important;margin-bottom:.25rem;}

/* ─── FORM CONTROLS ─── */
.stTextInput>div>div>input,.stNumberInput>div>div>input,.stTextArea>div>div>textarea{
  background:var(--bg)!important;border:1px solid var(--border)!important;border-radius:6px!important;
  color:var(--text)!important;font-family:'Poppins',sans-serif!important;font-size:.86rem!important;caret-color:var(--blue)!important;}
.stTextInput>div>div>input:focus,.stNumberInput>div>div>input:focus,.stTextArea>div>div>textarea:focus{
  border-color:var(--blue)!important;box-shadow:0 0 0 3px var(--blue-glow)!important;}
input::placeholder,textarea::placeholder{color:var(--muted)!important;opacity:.6!important;}
div[data-baseweb="select"]>div{background:var(--bg)!important;border-color:var(--border)!important;color:var(--text)!important;}
div[data-baseweb="select"] svg{fill:var(--muted)!important;}
div[data-baseweb="select"] span,div[data-baseweb="select"] input{color:var(--text)!important;}
div[data-baseweb="menu"],div[data-baseweb="popover"]{background:var(--surface2)!important;
  border:1px solid var(--border-hi)!important;box-shadow:0 8px 32px rgba(0,0,0,.6)!important;}
div[data-baseweb="menu"] li{color:var(--text)!important;background:transparent!important;}
div[data-baseweb="menu"] li:hover,[aria-selected="true"]{background:var(--surface3)!important;}
.stCheckbox>label span,.stRadio>div>label span{color:var(--text)!important;font-size:.84rem!important;}

/* ─── BUTTONS ─── */
.stButton>button{background:var(--blue)!important;color:#fff!important;border:none!important;
  border-radius:6px!important;font-family:'Inter Tight',sans-serif!important;
  font-size:.75rem!important;font-weight:800!important;letter-spacing:.1em!important;
  text-transform:uppercase!important;padding:.45rem 1.4rem!important;
  box-shadow:0 2px 12px rgba(64,128,255,.3)!important;transition:all .15s!important;}
.stButton>button:hover{background:var(--blue-lo)!important;box-shadow:0 4px 20px rgba(64,128,255,.45)!important;transform:translateY(-1px)!important;}
.stButton>button:disabled{background:var(--surface3)!important;color:var(--muted)!important;box-shadow:none!important;}
.stDownloadButton>button{background:transparent!important;color:var(--blue)!important;
  border:1px solid rgba(64,128,255,.35)!important;border-radius:6px!important;
  font-family:'Inter Tight',sans-serif!important;font-size:.7rem!important;font-weight:700!important;
  letter-spacing:.1em!important;text-transform:uppercase!important;transition:all .15s!important;}
.stDownloadButton>button:hover{background:var(--blue-glow)!important;border-color:var(--blue)!important;}

/* ─── TABS ─── */
div[data-testid="stTabs"]>div>div[data-testid="stHorizontalBlock"]{
  border-bottom:1px solid var(--border)!important;gap:.3rem!important;}
button[data-baseweb="tab"]{background:transparent!important;color:var(--muted)!important;
  border:none!important;border-bottom:2px solid transparent!important;font-family:'Inter Tight',sans-serif!important;
  font-size:.72rem!important;font-weight:700!important;letter-spacing:.1em!important;text-transform:uppercase!important;
  padding:.5rem .9rem!important;transition:all .15s!important;}
button[data-baseweb="tab"]:hover{color:var(--text)!important;}
button[data-baseweb="tab"][aria-selected="true"]{color:var(--blue)!important;
  border-bottom-color:var(--blue)!important;}

/* ─── METRICS ─── */
.metric-card{background:var(--surface);border:1px solid var(--border);border-radius:8px;
  padding:.9rem 1.1rem;min-height:4.5rem;}
.metric-label{font-size:.55rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;
  color:var(--muted)!important;margin-bottom:.3rem;}
.metric-value{font-family:'Inter Tight',sans-serif;font-size:1.75rem;font-weight:900;line-height:1;color:var(--blue);}
.metric-delta{font-size:.65rem;color:var(--muted)!important;margin-top:.25rem;}

/* ─── SECTION HEADER ─── */
.section-header{font-family:'Inter Tight',sans-serif;font-size:.68rem;font-weight:800;
  letter-spacing:.2em;text-transform:uppercase;color:var(--text-dim)!important;
  border-bottom:1px solid var(--border);padding-bottom:.4rem;margin:1.5rem 0 .75rem;display:flex;align-items:center;gap:.5rem;}
.dot{width:5px;height:5px;background:var(--blue);border-radius:50%;flex-shrink:0;}

/* ─── POST CARDS ─── */
.post-card{background:var(--surface);border:1px solid var(--border);border-radius:7px;
  padding:.85rem 1rem;margin-bottom:.6rem;transition:border-color .15s;}
.post-card:hover{border-color:var(--border-hi);}
.post-title{font-size:.88rem;font-weight:600;color:var(--text)!important;margin-bottom:.3rem;line-height:1.35;}
.post-excerpt{font-size:.78rem;color:var(--text-dim)!important;line-height:1.5;margin-bottom:.4rem;}
.post-meta{font-size:.65rem;color:var(--muted)!important;}
.badge{display:inline-block;padding:.1rem .45rem;border-radius:3px;font-size:.6rem;font-weight:700;
  letter-spacing:.1em;text-transform:uppercase;margin-right:.4rem;}
.badge-pos{background:var(--pos-dim);color:var(--pos)!important;}
.badge-neg{background:var(--neg-dim);color:var(--neg)!important;}
.badge-neu{background:var(--surface3);color:var(--muted)!important;}
.badge-post{background:var(--blue-glow);color:var(--blue)!important;}
.badge-cmt{background:var(--amber-dim);color:var(--amber)!important;}

/* ─── WISHLIST CARDS ─── */
.wish-card{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:1rem 1.1rem;margin-bottom:.7rem;}
.wish-title{font-family:'Inter Tight',sans-serif;font-size:1rem;font-weight:800;color:var(--text)!important;margin-bottom:.5rem;}
.wish-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:.5rem;margin-top:.4rem;}
.wish-stat{background:var(--surface3);border-radius:5px;padding:.4rem .6rem;}
.wish-stat-label{font-size:.5rem;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:var(--muted)!important;}
.wish-stat-value{font-family:'Inter Tight',sans-serif;font-size:1.1rem;font-weight:800;color:var(--cyan)!important;}

/* ─── COMMUNITY CARD ─── */
.community-hero{background:linear-gradient(135deg,var(--surface) 0%,var(--surface3) 100%);
  border:1px solid var(--border);border-radius:10px;padding:1.5rem;margin-bottom:1rem;}
.community-name{font-family:'Inter Tight',sans-serif;font-size:1.4rem;font-weight:900;color:var(--text)!important;}
.community-stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem;margin-top:1rem;}
.cstat{background:var(--bg);border:1px solid var(--border);border-radius:7px;padding:.75rem;}
.cstat-label{font-size:.52rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--muted)!important;}
.cstat-value{font-family:'Inter Tight',sans-serif;font-size:1.5rem;font-weight:900;margin-top:.2rem;}

/* ─── EMPTY STATE ─── */
.empty-state{text-align:center;padding:4rem 2rem;}
.empty-title{font-family:'Inter Tight',sans-serif;font-size:1.8rem;font-weight:900;
  color:var(--border-hi)!important;letter-spacing:.1em;margin-bottom:.75rem;}
.empty-sub{font-size:.88rem;color:var(--muted)!important;max-width:380px;margin:0 auto;line-height:1.7;}

/* ─── FOOTER ─── */
.footer{border-top:1px solid var(--border);margin-top:3rem;padding:1.2rem 0;
  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.5rem;}
.footer-brand{font-family:'Inter Tight',sans-serif;font-size:.65rem;font-weight:900;
  letter-spacing:.2em;text-transform:uppercase;color:var(--border-hi)!important;}
.footer-note{font-size:.6rem;color:var(--muted)!important;}

/* ─── MARKET INTEL ─── */
.ccu-row{background:var(--surface);border:1px solid var(--border);border-radius:6px;
  padding:.6rem 1rem;margin-bottom:.35rem;display:flex;align-items:center;justify-content:space-between;}
.ccu-name{font-size:.85rem;font-weight:500;color:var(--text)!important;}
.ccu-val{font-family:'Inter Tight',sans-serif;font-size:1rem;font-weight:800;color:var(--amber)!important;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SIDEBAR: API KEYS + LANGUAGE
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    lang_choice = st.selectbox(T("lang_label"), ["English", "日本語"],
                                index=0 if st.session_state.lang == "en" else 1)
    new_lang = "en" if lang_choice == "English" else "ja"
    if new_lang != st.session_state.lang:
        st.session_state.lang = new_lang
        st.rerun()

    st.markdown("---")
    st.markdown("**API Keys**")
    key_input = st.text_input(T("api_key_hint"), type="password",
                               value=st.session_state.claude_key, key="sidebar_claude_key")
    if key_input != st.session_state.claude_key:
        st.session_state.claude_key = key_input

    bearer_input = st.text_input(T("twitter_bearer_hint"), type="password",
                                  value=st.session_state.twitter_bearer, key="sidebar_bearer")
    if bearer_input != st.session_state.twitter_bearer:
        st.session_state.twitter_bearer = bearer_input

    discord_input = st.text_input(T("discord_token_hint"), type="password",
                                   value=st.session_state.discord_token, key="sidebar_discord")
    if discord_input != st.session_state.discord_token:
        st.session_state.discord_token = discord_input

# ─────────────────────────────────────────────────────────────
# TOP BAR
# ─────────────────────────────────────────────────────────────
flag = "🇯🇵" if st.session_state.lang == "ja" else "🌐"
st.markdown(f"""
<div class="topbar">
  <div class="topbar-logo"><span class="seg">SEGA</span></div>
  <div class="topbar-div"></div>
  <div class="topbar-label">{T("app_title")}</div>
  <div class="topbar-pill">{flag} {T("app_subtitle")}</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# MODULE NAVIGATION — real Streamlit buttons
# ─────────────────────────────────────────────────────────────
TAB_DEFS = [
    ("reddit",          "💬", T("nav_reddit"), "🚧 under construction"),
    ("twitter",         "🐦", T("nav_twitter"), ""),
    ("discord",         "🎮", T("nav_discord"), ""),
    ("steam_reviews",   "⭐", T("nav_steam_reviews"), ""),
    ("steam_community", "🏠", T("nav_steam_community"), ""),
    ("wishlist",        "📈", T("nav_wishlist"), ""),
    ("market_intel",    "🎯", T("nav_market_intel"), ""),
]

st.markdown("""
<style>
/* Nav button row */
div[data-testid="stHorizontalBlock"].nav-row > div { padding: 0 3px !important; }

/* Base nav button style — overrides the global .stButton */
.nav-btn-wrap .stButton > button {
    background: var(--surface) !important;
    color: var(--text-dim) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    font-family: 'Inter Tight', sans-serif !important;
    font-size: .7rem !important;
    font-weight: 700 !important;
    letter-spacing: .08em !important;
    text-transform: uppercase !important;
    padding: .42rem .75rem !important;
    box-shadow: none !important;
    width: 100% !important;
    white-space: nowrap !important;
    transition: all .15s !important;
}
.nav-btn-wrap .stButton > button:hover {
    border-color: var(--blue) !important;
    color: var(--text) !important;
    transform: none !important;
    box-shadow: none !important;
}
/* Active tab */
.nav-btn-active .stButton > button {
    background: var(--blue-glow) !important;
    border-color: var(--blue) !important;
    color: var(--blue) !important;
    box-shadow: 0 0 0 1px rgba(64,128,255,.18) !important;
}
/* Under-construction badge on Reddit button */
.nav-btn-wrap .stButton > button .uc-badge {
    font-size: .5rem;
    opacity: .7;
    font-style: italic;
}
</style>
""", unsafe_allow_html=True)

nav_cols = st.columns(len(TAB_DEFS))
for col, (tab_id, icon, label, badge) in zip(nav_cols, TAB_DEFS):
    is_active = st.session_state.active_tab == tab_id
    wrap_cls = "nav-btn-active nav-btn-wrap" if is_active else "nav-btn-wrap"
    btn_label = f"{icon} {label}" + (f"\n{badge}" if badge else "")
    with col:
        st.markdown(f'<div class="{wrap_cls}">', unsafe_allow_html=True)
        if st.button(btn_label, key=f"nav_{tab_id}", use_container_width=True):
            st.session_state.active_tab = tab_id
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

active = st.session_state.active_tab

# ═════════════════════════════════════════════════════════════
# MODULE: REDDIT — Req 5 (posts primary)
# ═════════════════════════════════════════════════════════════
if active == "reddit":
    st.markdown(f"""
    <div class="hero">
      <div class="hero-title">💬 {T("reddit_title")}<span class="accent">.</span></div>
      <div class="hero-sub">{T("reddit_sub")}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="query-block">', unsafe_allow_html=True)
    r_col1, r_col2, r_col3 = st.columns([3, 2, 1])
    with r_col1:
        r_genre = st.text_input(T("genre"), value="JRPG", key="r_genre",
                                 placeholder="e.g. Persona, Like a Dragon, Final Fantasy")
    with r_col2:
        genre_key = st.selectbox("Genre preset", list(GENRE_PRESETS.keys()),
                                  index=list(GENRE_PRESETS.keys()).index("RPG"),
                                  key="r_genre_preset")
        default_subs = ", ".join(GENRE_PRESETS[genre_key]["subreddits"])
    with r_col3:
        r_limit = st.number_input(T("posts_per_sub"), min_value=5, max_value=100, value=25, step=5, key="r_limit")

    r_subs_raw = st.text_input(T("subreddits"), value=default_subs, key="r_subs",
                                placeholder="gaming, Games, patientgamers")

    r_col4, r_col5 = st.columns([2, 3])
    with r_col4:
        content_mode = st.radio(T("post_content_type"),
                                 [T("content_posts_only"), T("content_posts_comments")],
                                 horizontal=True, key="r_content_mode")
    with r_col5:
        r_sort = st.radio("Sort", ["hot", "new"], horizontal=True, key="r_sort")

    fetch_btn = st.button(T("fetch_posts"), key="r_fetch")
    st.markdown("</div>", unsafe_allow_html=True)

    if fetch_btn:
        subs = [s.strip() for s in r_subs_raw.split(",") if s.strip()]
        if not subs:
            st.warning("Enter at least one subreddit.")
        else:
            all_posts = []
            progress = st.progress(0, text="Fetching posts…")
            for i, sub in enumerate(subs):
                posts = reddit_fetch_posts(sub, limit=r_limit, sort=r_sort)
                # Score sentiment on posts
                for p in posts:
                    sc = vader_score(p["full_text"])
                    p["sent_score"] = sc
                    p["sentiment"] = sentiment_label(sc)
                all_posts.extend(posts)
                progress.progress((i + 1) / len(subs), text=f"r/{sub} — {len(posts)} posts")
                time.sleep(0.4)

            # Optionally fetch comments
            if content_mode == T("content_posts_comments") or content_mode == "Posts + Comments":
                all_comments = []
                cmts_progress = st.progress(0, text="Fetching comments…")
                # Sample top posts for comments
                sample_posts = sorted(all_posts, key=lambda x: x["score"], reverse=True)[:min(30, len(all_posts))]
                for i, p in enumerate(sample_posts):
                    cmts = reddit_fetch_comments(p["permalink"].replace("https://reddit.com",""), limit=15)
                    for c in cmts:
                        sc = vader_score(c["full_text"])
                        c["sent_score"] = sc
                        c["sentiment"] = sentiment_label(sc)
                    all_comments.extend(cmts)
                    cmts_progress.progress((i + 1) / len(sample_posts))
                    time.sleep(0.3)
                st.session_state.reddit_comments = all_comments
            else:
                st.session_state.reddit_comments = []

            st.session_state.reddit_posts = all_posts
            st.session_state.reddit_fetched = True
            st.session_state.ai_report_reddit = ""
            st.rerun()

    if st.session_state.reddit_fetched and st.session_state.reddit_posts:
        posts = st.session_state.reddit_posts
        comments = st.session_state.reddit_comments
        df_p = pd.DataFrame(posts)
        df_c = pd.DataFrame(comments) if comments else pd.DataFrame()

        n_posts = len(df_p)
        n_cmts = len(df_c)
        pos_n = len(df_p[df_p["sentiment"] == df_p["sentiment"].map(lambda x: sentiment_label(0.1) if x in [T("positive"), "Positive"] else x)])
        # Re-count properly
        pos_posts = df_p[df_p["sent_score"] >= 0.05]
        neg_posts = df_p[df_p["sent_score"] <= -0.05]
        avg_s = df_p["sent_score"].mean()
        pos_pct = 100 * len(pos_posts) / max(n_posts, 1)
        neg_pct = 100 * len(neg_posts) / max(n_posts, 1)

        metric_row([
            {"label": T("posts_label"), "value": f"{n_posts:,}", "color": "var(--blue)"},
            {"label": T("comments_label"), "value": f"{n_cmts:,}", "color": "var(--amber)"},
            {"label": f"% {T('positive')}", "value": f"{pos_pct:.1f}%", "color": "var(--pos)"},
            {"label": f"% {T('negative')}", "value": f"{neg_pct:.1f}%", "color": "var(--neg)"},
            {"label": "Avg VADER", "value": f"{avg_s:+.3f}", "color": "var(--blue)"},
        ])

        tab_overview, tab_posts, tab_comments, tab_ai = st.tabs([
            "📊 Overview", f"📝 {T('posts_label')} ({n_posts})",
            f"💬 {T('comments_label')} ({n_cmts})", "✨ AI Report"
        ])

        with tab_overview:
            c1, c2 = st.columns(2)
            with c1:
                section_header("SENTIMENT BREAKDOWN — POSTS")
                sent_counts = df_p["sentiment"].value_counts()
                colors_map = {"Positive": "#20c65a", "Negative": "#ff3d52", "Neutral": "#5a5f82",
                              T("positive"): "#20c65a", T("negative"): "#ff3d52", T("neutral"): "#5a5f82"}
                fig = go.Figure(go.Pie(
                    labels=sent_counts.index.tolist(),
                    values=sent_counts.values.tolist(),
                    hole=0.55,
                    marker=dict(colors=[colors_map.get(s, "#4080ff") for s in sent_counts.index]),
                ))
                fig.update_layout(**plotly_dark_layout())
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                section_header("POST VOLUME BY SUBREDDIT")
                sub_counts = df_p["subreddit"].value_counts().head(10)
                fig2 = go.Figure(go.Bar(
                    x=sub_counts.values, y=sub_counts.index, orientation="h",
                    marker=dict(color="#4080ff", opacity=0.85),
                ))
                fig2.update_layout(**plotly_dark_layout())
                st.plotly_chart(fig2, use_container_width=True)

            # Sentiment over time
            section_header("SENTIMENT SCORE OVER TIME")
            df_p["date_day"] = pd.to_datetime(df_p["date"]).dt.date
            daily = df_p.groupby("date_day")["sent_score"].mean().reset_index()
            fig3 = go.Figure(go.Scatter(
                x=daily["date_day"], y=daily["sent_score"],
                mode="lines+markers", line=dict(color="#4080ff", width=2),
                fill="tozeroy", fillcolor="rgba(64,128,255,0.08)",
            ))
            fig3.update_layout(**plotly_dark_layout())
            st.plotly_chart(fig3, use_container_width=True)

        with tab_posts:
            section_header(f"{T('posts_label').upper()}")
            sort_col = st.selectbox("Sort by", ["score", "sent_score", "num_comments", "date"], key="r_sort_posts")
            df_sorted = df_p.sort_values(sort_col, ascending=False).head(50)
            for _, row in df_sorted.iterrows():
                s_cls = "badge-pos" if row["sent_score"] >= 0.05 else ("badge-neg" if row["sent_score"] <= -0.05 else "badge-neu")
                s_lbl = "POS" if row["sent_score"] >= 0.05 else ("NEG" if row["sent_score"] <= -0.05 else "NEU")
                st.markdown(
                    f'<div class="post-card">'
                    f'<div class="post-title"><span class="badge badge-post">POST</span>'
                    f'<span class="badge {s_cls}">{s_lbl} {row["sent_score"]:+.2f}</span>'
                    f'{row["title"]}</div>'
                    f'<div class="post-excerpt">{str(row.get("selftext",""))[:200]}</div>'
                    f'<div class="post-meta">r/{row["subreddit"]} · ▲{row["score"]:,} · '
                    f'💬{row.get("num_comments",0):,} · '
                    f'<a href="{row["permalink"]}" target="_blank" style="color:var(--blue)">view ↗</a></div>'
                    f'</div>', unsafe_allow_html=True)
            st.download_button(T("download_csv"), data=df_p.to_csv(index=False).encode(),
                               file_name="reddit_posts.csv", mime="text/csv")

        with tab_comments:
            if df_c.empty:
                st.info("Comments not fetched. Select 'Posts + Comments' mode and re-fetch.")
            else:
                section_header(f"{T('comments_label').upper()}")
                df_cs = df_c.sort_values("sent_score", ascending=False).head(50)
                for _, row in df_cs.iterrows():
                    s_cls = "badge-pos" if row["sent_score"] >= 0.05 else ("badge-neg" if row["sent_score"] <= -0.05 else "badge-neu")
                    s_lbl = "POS" if row["sent_score"] >= 0.05 else ("NEG" if row["sent_score"] <= -0.05 else "NEU")
                    st.markdown(
                        f'<div class="post-card">'
                        f'<span class="badge badge-cmt">COMMENT</span>'
                        f'<span class="badge {s_cls}">{s_lbl} {row["sent_score"]:+.2f}</span>'
                        f'<span style="font-size:.84rem;color:var(--text-dim)">{str(row["full_text"])[:280]}</span>'
                        f'<div class="post-meta" style="margin-top:.3rem">r/{row["subreddit"]} · ▲{row["score"]:,}</div>'
                        f'</div>', unsafe_allow_html=True)
                st.download_button(T("download_csv"), data=df_c.to_csv(index=False).encode(),
                                   file_name="reddit_comments.csv", mime="text/csv", key="dl_cmts")

        with tab_ai:
            def reddit_prompt():
                genre = st.session_state.get("r_genre", "")
                pk = ", ".join(f"{w}({c})" for w, c in keywords(pos_posts["full_text"].tolist())[:20])
                nk = ", ".join(f"{w}({c})" for w, c in keywords(neg_posts["full_text"].tolist())[:20])
                sub_lines = "\n".join(f"  - r/{s}: {c} posts" for s, c in df_p["subreddit"].value_counts().items())
                return f"""You are a senior games market analyst at SEGA.
Write a structured executive sentiment analysis report from this Reddit data.

Genre / topic: {genre}
Posts analysed: {n_posts:,} | Comments: {n_cmts:,}
Date range: {df_p["date"].min()} → {df_p["date"].max()}
Positive posts: {pos_pct:.1f}% | Negative: {neg_pct:.1f}% | Avg VADER: {avg_s:+.4f}

Subreddit breakdown:
{sub_lines}

Positive keywords: {pk}
Negative keywords: {nk}

Write a comprehensive report:
1. Executive Summary
2. Sentiment Landscape
3. Subreddit Breakdown
4. Key Themes
5. Community Strengths & Pain Points
6. Actionable SEGA Recommendations

Use markdown. Be specific with numbers. Language: {"Japanese" if st.session_state.lang == "ja" else "English"}"""

            def reddit_chat_system():
                return (f"You are a SEGA games analyst. Answer in {'Japanese' if st.session_state.lang == 'ja' else 'English'}.\n"
                        f"Report context:\n{st.session_state.get('ai_report_reddit','')[:3000]}")

            if "ai_report_reddit" not in st.session_state:
                st.session_state.ai_report_reddit = ""
            render_ai_tab("ai_report_reddit", reddit_prompt, reddit_chat_system, slug="reddit_sentiment")

    elif not st.session_state.reddit_fetched:
        st.markdown(f'<div class="empty-state"><div class="empty-title">{T("no_data")}</div>'
                    f'<div class="empty-sub">Select a genre, configure subreddits, then click <strong style="color:var(--blue)">{T("fetch_posts")}</strong>.</div></div>',
                    unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════
# MODULE: TWITTER / X
# ═════════════════════════════════════════════════════════════
elif active == "twitter":
    st.markdown(f"""
    <div class="hero">
      <div class="hero-title">🐦 {T("twitter_title")}<span class="accent">.</span></div>
      <div class="hero-sub">{T("twitter_sub")}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="query-block">', unsafe_allow_html=True)
    tw_col1, tw_col2 = st.columns([3, 1])
    with tw_col1:
        tw_queries = st.text_area(T("queries_label"),
                                   value="JRPG\n#RPG\nLike a Dragon game\nPersona game\nFinal Fantasy",
                                   height=100, key="tw_queries")
    with tw_col2:
        tw_max = st.number_input(T("max_tweets"), min_value=10, max_value=500, value=100, step=10, key="tw_max")
        tw_fetch = st.button(T("fetch_analyse"), key="tw_fetch")
    st.markdown("</div>", unsafe_allow_html=True)

    if tw_fetch:
        queries = [q.strip() for q in tw_queries.strip().split("\n") if q.strip()]
        bearer = st.session_state.twitter_bearer.strip()
        if not bearer:
            st.error("Enter your Twitter/X Bearer Token in the sidebar.")
        elif not TWEEPY_OK:
            st.error(T("err_tweepy"))
        else:
            client_tw = tweepy.Client(bearer_token=bearer, wait_on_rate_limit=True)
            all_tweets = []
            prog = st.progress(0)
            for i, q in enumerate(queries):
                try:
                    resp = client_tw.search_recent_tweets(
                        query=f"{q} lang:en -is:retweet",
                        max_results=min(tw_max, 100),
                        tweet_fields=["created_at", "public_metrics", "lang"],
                    )
                    if resp.data:
                        for tw in resp.data:
                            sc = vader_score(tw.text)
                            metrics = tw.public_metrics or {}
                            all_tweets.append({
                                "query": q,
                                "text": tw.text,
                                "created_at": tw.created_at,
                                "likes": metrics.get("like_count", 0),
                                "retweets": metrics.get("retweet_count", 0),
                                "replies": metrics.get("reply_count", 0),
                                "sent_score": sc,
                                "sentiment": sentiment_label(sc),
                            })
                except Exception as e:
                    st.warning(f"Query '{q}' failed: {e}")
                prog.progress((i + 1) / len(queries))

            st.session_state.twitter_df = pd.DataFrame(all_tweets) if all_tweets else None
            st.session_state.twitter_fetched = True
            st.session_state.ai_report_twitter = ""
            st.rerun()

    if st.session_state.twitter_fetched and st.session_state.twitter_df is not None:
        df = st.session_state.twitter_df
        n_tw = len(df)
        pos_tw = df[df["sent_score"] >= 0.05]
        neg_tw = df[df["sent_score"] <= -0.05]
        avg_tw = df["sent_score"].mean()

        metric_row([
            {"label": "Tweets", "value": f"{n_tw:,}", "color": "var(--blue)"},
            {"label": f"% {T('positive')}", "value": f"{100*len(pos_tw)/max(n_tw,1):.1f}%", "color": "var(--pos)"},
            {"label": f"% {T('negative')}", "value": f"{100*len(neg_tw)/max(n_tw,1):.1f}%", "color": "var(--neg)"},
            {"label": "Avg VADER", "value": f"{avg_tw:+.3f}", "color": "var(--cyan)"},
            {"label": "Queries", "value": df["query"].nunique(), "color": "var(--amber)"},
        ])

        tab_ov, tab_feed, tab_ai_tw = st.tabs(["📊 Overview", "📰 Tweet Feed", "✨ AI Report"])

        with tab_ov:
            c1, c2 = st.columns(2)
            with c1:
                section_header("SENTIMENT BY QUERY")
                qdf = df.groupby("query").agg(
                    tweet_count=("text","count"),
                    positive_pct=("sent_score", lambda x: 100*(x>=0.05).mean()),
                    avg_score=("sent_score","mean"),
                ).reset_index()
                fig = go.Figure()
                fig.add_trace(go.Bar(name="Positive %", x=qdf["query"], y=qdf["positive_pct"],
                                     marker_color="#20c65a"))
                fig.update_layout(**plotly_dark_layout("Positive % per Query"))
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                section_header("ENGAGEMENT DISTRIBUTION")
                fig2 = go.Figure(go.Scatter(
                    x=df["likes"], y=df["sent_score"], mode="markers",
                    marker=dict(color=df["sent_score"], colorscale="RdYlGn",
                                size=5, opacity=0.7, showscale=True),
                    text=df["text"].str[:60],
                ))
                fig2.update_layout(**plotly_dark_layout("Likes vs Sentiment"))
                fig2.update_xaxes(title_text="Likes")
                fig2.update_yaxes(title_text="Sentiment Score")
                st.plotly_chart(fig2, use_container_width=True)

        with tab_feed:
            section_header("TWEET FEED")
            feed_filter = st.selectbox("Filter", ["All", T("positive"), T("negative"), T("neutral")], key="tw_filter")
            feed_df = df if feed_filter == "All" else df[df["sentiment"] == feed_filter]
            feed_df = feed_df.sort_values("likes", ascending=False).head(50)
            for _, row in feed_df.iterrows():
                sc = row["sent_score"]
                s_cls = "badge-pos" if sc >= 0.05 else ("badge-neg" if sc <= -0.05 else "badge-neu")
                s_lbl = "POS" if sc >= 0.05 else ("NEG" if sc <= -0.05 else "NEU")
                st.markdown(
                    f'<div class="post-card">'
                    f'<span class="badge {s_cls}">{s_lbl} {sc:+.2f}</span>'
                    f'<span class="badge" style="background:var(--surface3);color:var(--text-dim)!important;font-size:.58rem">{row["query"]}</span>'
                    f'<div class="post-excerpt" style="margin-top:.4rem">{row["text"]}</div>'
                    f'<div class="post-meta">❤️ {row["likes"]:,} · 🔁 {row["retweets"]:,} · 💬 {row["replies"]:,}</div>'
                    f'</div>', unsafe_allow_html=True)
            st.download_button(T("download_csv"), data=df.to_csv(index=False).encode(),
                               file_name="twitter_data.csv", mime="text/csv")

        with tab_ai_tw:
            def twitter_prompt():
                qsum = "\n".join(f"  - {r['query']}: {r['tweet_count']} tweets, {r['positive_pct']:.1f}% pos"
                                 for _, r in qdf.iterrows())
                pk = ", ".join(f"{w}({c})" for w, c in keywords(pos_tw["text"].tolist())[:20])
                nk = ", ".join(f"{w}({c})" for w, c in keywords(neg_tw["text"].tolist())[:20])
                return f"""SEGA Twitter/X Sentiment Analysis Report.
{n_tw:,} tweets | {df["query"].nunique()} queries | {100*len(pos_tw)/max(n_tw,1):.1f}% positive | avg VADER {avg_tw:+.4f}

Per-query breakdown:
{qsum}

Positive keywords: {pk}
Negative keywords: {nk}

Generate executive report covering:
1. Executive Summary
2. Query-by-Query Analysis
3. Trending Themes
4. Influencer / Engagement Patterns
5. SEGA Brand Opportunities
6. Recommended Actions

Language: {"Japanese" if st.session_state.lang == "ja" else "English"}"""

            if "ai_report_twitter" not in st.session_state:
                st.session_state.ai_report_twitter = ""
            render_ai_tab("ai_report_twitter", twitter_prompt, slug="twitter_sentiment")

    elif not st.session_state.twitter_fetched:
        st.markdown(f'<div class="empty-state"><div class="empty-title">{T("no_data")}</div>'
                    f'<div class="empty-sub">Add your Twitter Bearer Token in the sidebar, enter queries, then click <strong style="color:var(--blue)">{T("fetch_analyse")}</strong>.</div></div>',
                    unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════
# MODULE: DISCORD
# ═════════════════════════════════════════════════════════════
elif active == "discord":
    st.markdown(f"""
    <div class="hero">
      <div class="hero-title">🎮 {T("discord_title")}<span class="accent">.</span></div>
      <div class="hero-sub">{T("discord_sub")}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="query-block">', unsafe_allow_html=True)
    dc_col1, dc_col2 = st.columns([3, 1])
    with dc_col1:
        dc_channels = st.text_area(T("server_id"),
                                    placeholder="123456789012345678\n987654321098765432",
                                    height=80, key="dc_channels")
    with dc_col2:
        dc_limit = st.number_input(T("message_limit"), min_value=50, max_value=1000, value=200, step=50, key="dc_limit")
        dc_fetch = st.button(T("fetch"), key="dc_fetch")
    st.markdown("</div>", unsafe_allow_html=True)

    if dc_fetch:
        token = st.session_state.discord_token.strip()
        if not token:
            st.error("Enter your Discord Bot Token in the sidebar.")
        else:
            channels = [c.strip() for c in dc_channels.strip().split("\n") if c.strip()]
            if not channels:
                st.error("Enter at least one channel ID.")
            else:
                all_msgs = []
                prog = st.progress(0)
                for i, ch in enumerate(channels):
                    msgs = discord_fetch_messages(ch, token, limit=dc_limit)
                    for m in msgs:
                        sc = vader_score(m["content"])
                        m["sent_score"] = sc
                        m["sentiment"] = sentiment_label(sc)
                        m["channel_id"] = ch
                    all_msgs.extend(msgs)
                    prog.progress((i + 1) / len(channels))
                st.session_state.discord_df = pd.DataFrame(all_msgs) if all_msgs else None
                st.session_state.discord_fetched = True
                st.session_state.ai_report_discord = ""
                st.rerun()

    if st.session_state.discord_fetched and st.session_state.discord_df is not None:
        ddf = st.session_state.discord_df
        n_m = len(ddf)
        pos_d = ddf[ddf["sent_score"] >= 0.05]
        neg_d = ddf[ddf["sent_score"] <= -0.05]
        avg_d = ddf["sent_score"].mean()

        metric_row([
            {"label": "Messages", "value": f"{n_m:,}", "color": "var(--purple)"},
            {"label": f"% {T('positive')}", "value": f"{100*len(pos_d)/max(n_m,1):.1f}%", "color": "var(--pos)"},
            {"label": f"% {T('negative')}", "value": f"{100*len(neg_d)/max(n_m,1):.1f}%", "color": "var(--neg)"},
            {"label": "Avg Sentiment", "value": f"{avg_d:+.3f}", "color": "var(--cyan)"},
        ])

        tab_ov_dc, tab_feed_dc, tab_ai_dc = st.tabs(["📊 Overview", "💬 Message Feed", "✨ AI Report"])

        with tab_ov_dc:
            c1, c2 = st.columns(2)
            with c1:
                section_header("SENTIMENT DISTRIBUTION")
                sc = ddf["sentiment"].value_counts()
                fig = go.Figure(go.Pie(labels=sc.index, values=sc.values, hole=0.5,
                                       marker=dict(colors=["#20c65a","#ff3d52","#5a5f82"])))
                fig.update_layout(**plotly_dark_layout())
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                section_header("TOP KEYWORDS")
                kws = keywords(ddf["content"].tolist(), 15)
                kw_df = pd.DataFrame(kws, columns=["word","count"])
                fig2 = go.Figure(go.Bar(x=kw_df["count"], y=kw_df["word"], orientation="h",
                                        marker=dict(color="#a855f7")))
                fig2.update_layout(**plotly_dark_layout())
                st.plotly_chart(fig2, use_container_width=True)

        with tab_feed_dc:
            section_header("MESSAGE FEED")
            for _, row in ddf.sort_values("sent_score", ascending=False).head(50).iterrows():
                sc_val = row["sent_score"]
                s_cls = "badge-pos" if sc_val >= 0.05 else ("badge-neg" if sc_val <= -0.05 else "badge-neu")
                s_lbl = "POS" if sc_val >= 0.05 else ("NEG" if sc_val <= -0.05 else "NEU")
                st.markdown(
                    f'<div class="post-card">'
                    f'<span class="badge {s_cls}">{s_lbl} {sc_val:+.2f}</span>'
                    f'<span style="font-size:.84rem;color:var(--text-dim)">{str(row["content"])[:300]}</span>'
                    f'<div class="post-meta" style="margin-top:.3rem">👤 {row["author"]} · ⭐ {row.get("reactions",0)}</div>'
                    f'</div>', unsafe_allow_html=True)
            st.download_button(T("download_csv"), data=ddf.to_csv(index=False).encode(),
                               file_name="discord_messages.csv", mime="text/csv")

        with tab_ai_dc:
            def discord_prompt():
                pk = ", ".join(f"{w}({c})" for w, c in keywords(pos_d["content"].tolist())[:15])
                nk = ", ".join(f"{w}({c})" for w, c in keywords(neg_d["content"].tolist())[:15])
                return f"""Discord Community Sentiment Analysis for SEGA.
{n_m:,} messages | {100*len(pos_d)/max(n_m,1):.1f}% positive | avg VADER {avg_d:+.4f}
Positive keywords: {pk}
Negative keywords: {nk}

Generate report covering:
1. Community Health Summary
2. Sentiment Deep Dive
3. Hot Topics & Pain Points
4. Community Growth Signals
5. Recommendations for SEGA community managers

Language: {"Japanese" if st.session_state.lang == "ja" else "English"}"""

            if "ai_report_discord" not in st.session_state:
                st.session_state.ai_report_discord = ""
            render_ai_tab("ai_report_discord", discord_prompt, slug="discord_sentiment")

    elif not st.session_state.discord_fetched:
        st.markdown(f'<div class="empty-state"><div class="empty-title">{T("no_data")}</div>'
                    f'<div class="empty-sub">Add your Discord Bot Token in the sidebar, enter channel IDs, then click <strong style="color:var(--blue)">{T("fetch")}</strong>.</div></div>',
                    unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════
# MODULE: STEAM REVIEWS
# ═════════════════════════════════════════════════════════════
elif active == "steam_reviews":
    st.markdown(f"""
    <div class="hero">
      <div class="hero-title">⭐ {T("steam_reviews_title")}<span class="accent">.</span></div>
      <div class="hero-sub">{T("steam_reviews_sub")}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="query-block">', unsafe_allow_html=True)
    sr_col1, sr_col2, sr_col3 = st.columns([3, 2, 1])
    with sr_col1:
        sr_genre = st.text_input(T("genre"), value="RPG", key="sr_genre")
    with sr_col2:
        sr_reviews_per = st.number_input("Reviews per game", min_value=20, max_value=500, value=100, step=20, key="sr_reviews_per")
    with sr_col3:
        sr_search = st.button(T("search_genre"), key="sr_search")
    st.markdown("</div>", unsafe_allow_html=True)

    if sr_search:
        with st.spinner(T("loading")):
            games = steam_search_game(sr_genre, max_results=8)
            st.session_state.steam_games = games
            if games:
                all_reviews = []
                prog = st.progress(0)
                for i, g in enumerate(games[:5]):
                    revs = steam_reviews_fetch(g["appid"], sr_reviews_per)
                    for rv in revs:
                        txt = rv.get("review","")
                        sc = vader_score(txt)
                        all_reviews.append({
                            "appid": g["appid"],
                            "game": g["name"],
                            "review": txt[:400],
                            "voted_up": rv.get("voted_up", True),
                            "sent_score": sc,
                            "sentiment": sentiment_label(sc),
                            "votes_helpful": rv.get("votes_helpful",0),
                            "timestamp": datetime.utcfromtimestamp(rv.get("timestamp_created",0)),
                        })
                    prog.progress((i+1)/min(len(games),5))
                    time.sleep(0.4)
                st.session_state.steam_reviews_df = pd.DataFrame(all_reviews) if all_reviews else None
                st.session_state.steam_fetched = True
                st.session_state.ai_report_steam = ""
                st.rerun()

    if st.session_state.steam_fetched and st.session_state.steam_reviews_df is not None:
        sdf = st.session_state.steam_reviews_df
        games = st.session_state.steam_games
        n_r = len(sdf)
        pos_r = sdf[sdf["sent_score"] >= 0.05]
        neg_r = sdf[sdf["sent_score"] <= -0.05]

        metric_row([
            {"label": "Reviews", "value": f"{n_r:,}", "color": "var(--blue)"},
            {"label": T("found_games"), "value": len(games), "color": "var(--amber)"},
            {"label": f"% {T('positive')}", "value": f"{100*len(pos_r)/max(n_r,1):.1f}%", "color": "var(--pos)"},
            {"label": f"% {T('negative')}", "value": f"{100*len(neg_r)/max(n_r,1):.1f}%", "color": "var(--neg)"},
        ])

        tab_ov_sr, tab_games_sr, tab_ai_sr = st.tabs(["📊 Overview", "🎮 By Game", "✨ AI Report"])

        with tab_ov_sr:
            c1, c2 = st.columns(2)
            with c1:
                section_header("SENTIMENT BY GAME")
                gdf = sdf.groupby("game").agg(
                    count=("review","count"),
                    pos_pct=("sent_score", lambda x: 100*(x>=0.05).mean()),
                    avg=("sent_score","mean"),
                ).reset_index()
                fig = go.Figure(go.Bar(x=gdf["game"], y=gdf["pos_pct"],
                                       marker=dict(color="#4080ff"), text=gdf["count"],
                                       textposition="outside"))
                fig.update_layout(**plotly_dark_layout("Positive Review % by Game"))
                fig.update_xaxes(tickangle=-20)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                section_header("KEYWORD CLOUD — NEGATIVE")
                nk_data = keywords(neg_r["review"].tolist(), 20)
                if WORDCLOUD_OK and nk_data:
                    wc = _WC(width=600, height=300, background_color="#0c0e1c",
                              colormap="Reds", max_words=40).generate_from_frequencies(dict(nk_data))
                    fig_wc, ax = plt.subplots(figsize=(8,4))
                    ax.imshow(wc, interpolation="bilinear")
                    ax.axis("off")
                    fig_wc.patch.set_facecolor("#0c0e1c")
                    st.pyplot(fig_wc)
                else:
                    kw_df2 = pd.DataFrame(nk_data, columns=["word","count"])
                    fig2 = go.Figure(go.Bar(x=kw_df2["count"], y=kw_df2["word"], orientation="h",
                                            marker=dict(color="#ff3d52")))
                    fig2.update_layout(**plotly_dark_layout())
                    st.plotly_chart(fig2, use_container_width=True)

        with tab_games_sr:
            sel_game = st.selectbox("Game", sdf["game"].unique(), key="sr_game_sel")
            game_df = sdf[sdf["game"] == sel_game].sort_values("sent_score", ascending=False)
            section_header(f"REVIEWS — {sel_game.upper()}")
            for _, row in game_df.head(30).iterrows():
                sc_val = row["sent_score"]
                s_cls = "badge-pos" if sc_val >= 0.05 else ("badge-neg" if sc_val <= -0.05 else "badge-neu")
                thumb = "👍" if row["voted_up"] else "👎"
                st.markdown(
                    f'<div class="post-card">'
                    f'<span class="badge {s_cls}">{sc_val:+.2f}</span>'
                    f'<span style="font-size:.84rem;color:var(--text-dim)">{thumb} {str(row["review"])[:280]}</span>'
                    f'<div class="post-meta" style="margin-top:.3rem">Helpful: {row["votes_helpful"]}</div>'
                    f'</div>', unsafe_allow_html=True)
            st.download_button(T("download_csv"), data=sdf.to_csv(index=False).encode(),
                               file_name="steam_reviews.csv", mime="text/csv")

        with tab_ai_sr:
            def steam_prompt():
                genre = st.session_state.get("sr_genre","")
                gsum = "\n".join(f"  - {r['game']}: {r['count']} reviews, {r['pos_pct']:.1f}% positive"
                                 for _, r in gdf.iterrows())
                pk = ", ".join(f"{w}({c})" for w, c in keywords(pos_r["review"].tolist())[:20])
                nk = ", ".join(f"{w}({c})" for w, c in keywords(neg_r["review"].tolist())[:20])
                return f"""Steam Review Analysis — SEGA Market Research.
Genre: {genre} | Reviews: {n_r:,} | Games: {len(games)}
{100*len(pos_r)/max(n_r,1):.1f}% positive, avg VADER {sdf["sent_score"].mean():+.4f}

Per-game breakdown:
{gsum}

Positive keywords: {pk}
Negative keywords: {nk}

Write a comprehensive analysis:
1. Market Sentiment Overview
2. Per-Title Deep Dive
3. Player Pain Points
4. Competitor Strengths
5. Design/Feature Opportunities for SEGA
6. Strategic Recommendations

Language: {"Japanese" if st.session_state.lang == "ja" else "English"}"""

            if "ai_report_steam" not in st.session_state:
                st.session_state.ai_report_steam = ""
            render_ai_tab("ai_report_steam", steam_prompt, slug="steam_reviews")

    elif not st.session_state.steam_fetched:
        st.markdown(f'<div class="empty-state"><div class="empty-title">{T("no_data")}</div>'
                    f'<div class="empty-sub">Enter a genre and click <strong style="color:var(--blue)">{T("search_genre")}</strong>.</div></div>',
                    unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════
# MODULE: STEAM COMMUNITY HUB — Req 3
# ═════════════════════════════════════════════════════════════
elif active == "steam_community":
    st.markdown(f"""
    <div class="hero">
      <div class="hero-title">🏠 {T("steam_community_title")}<span class="accent">.</span></div>
      <div class="hero-sub">{T("steam_community_sub")}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="query-block">', unsafe_allow_html=True)
    sc_col1, sc_col2, sc_col3 = st.columns([3, 2, 1])
    with sc_col1:
        sc_game = st.text_input(T("community_game"),
                                 value="Persona 5 Royal",
                                 placeholder="e.g. Like a Dragon, Final Fantasy, Yakuza",
                                 key="sc_game")
    with sc_col2:
        sc_period = st.selectbox(T("time_period"),
                                  [T("period_7d"), T("period_30d"), T("period_90d"), T("period_1y"), T("period_all")],
                                  key="sc_period")
    with sc_col3:
        sc_fetch_btn = st.button(T("fetch_community"), key="sc_fetch")
    st.markdown("</div>", unsafe_allow_html=True)

    if sc_fetch_btn:
        with st.spinner(T("loading")):
            results = steam_search_game(sc_game, max_results=5)
            community_results = []
            prog = st.progress(0)
            for i, g in enumerate(results[:5]):
                stats = steam_community_stats(g["appid"])
                stats["appid"] = g["appid"]
                stats["name"] = g["name"]
                community_results.append(stats)
                prog.progress((i+1)/len(results[:5]))
                time.sleep(0.5)
            st.session_state.community_data = {
                "results": community_results,
                "period": sc_period,
                "query": sc_game,
            }
            st.session_state.community_fetched = True
            st.rerun()

    if st.session_state.community_fetched and st.session_state.community_data.get("results"):
        cdata = st.session_state.community_data
        results = cdata["results"]

        # Primary game (first result)
        main = results[0]
        owners_str = main.get("owners_est","N/A")
        members = main.get("community_members", 0)
        followers_val = main.get("followers", 0)
        current = main.get("current_players", 0)
        peak = main.get("peak_ccu", 0)
        pos_rev = main.get("positive", 0)
        neg_rev = main.get("negative", 0)
        total_rev = pos_rev + neg_rev
        avg_play_hrs = main.get("average_forever", 0) / 60

        st.markdown(f"""
        <div class="community-hero">
          <div class="community-name">{main["name"]}</div>
          <div class="community-stats-grid">
            <div class="cstat">
              <div class="cstat-label">{T("members")}</div>
              <div class="cstat-value" style="color:var(--blue)">{members:,}</div>
            </div>
            <div class="cstat">
              <div class="cstat-label">{T("followers")}</div>
              <div class="cstat-value" style="color:var(--purple)">{followers_val:,}</div>
            </div>
            <div class="cstat">
              <div class="cstat-label">{T("in_game")}</div>
              <div class="cstat-value" style="color:var(--pos)">{current:,}</div>
            </div>
            <div class="cstat">
              <div class="cstat-label">{T("peak_ccu")}</div>
              <div class="cstat-value" style="color:var(--amber)">{peak:,}</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        metric_row([
            {"label": T("owners"), "value": owners_str, "color": "var(--cyan)"},
            {"label": T("avg_playtime"), "value": f"{avg_play_hrs:.1f}h", "color": "var(--purple)"},
            {"label": T("reviews_total"), "value": f"{total_rev:,}", "color": "var(--blue)"},
            {"label": "Review Score", "value": f"{100*pos_rev/max(total_rev,1):.1f}%" , "color": "var(--pos)"},
        ])

        # Multi-game comparison
        if len(results) > 1:
            section_header("COMMUNITY COMPARISON")
            comp_data = []
            for g in results:
                comp_data.append({
                    "Game": g["name"][:30],
                    T("in_game"): g.get("current_players",0),
                    T("peak_ccu"): g.get("peak_ccu",0),
                    "Positive Reviews": g.get("positive",0),
                    T("avg_playtime"): round(g.get("average_forever",0)/60,1),
                })
            comp_df = pd.DataFrame(comp_data)
            st.dataframe(comp_df, use_container_width=True)

            c1, c2 = st.columns(2)
            with c1:
                fig = go.Figure(go.Bar(
                    x=comp_df["Game"], y=comp_df[T("in_game")],
                    marker=dict(color="#4080ff"),
                ))
                fig.update_layout(**plotly_dark_layout("Current Players"))
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                fig2 = go.Figure(go.Bar(
                    x=comp_df["Game"], y=comp_df["Positive Reviews"],
                    marker=dict(color="#20c65a"),
                ))
                fig2.update_layout(**plotly_dark_layout("Total Positive Reviews"))
                st.plotly_chart(fig2, use_container_width=True)

        # Note on time-series data
        st.info(
            "📊 **Note on time-series community data**: Steam's public API provides current snapshots. "
            "For historical member/follower counts across time periods, integrate with SteamDB.info "
            "API (paid tier) or archive your own snapshots using the `steam_community_stats()` "
            "function on a scheduled basis (e.g. daily cron job storing to a database)."
            if st.session_state.lang == "en" else
            "📊 **時系列データについて**: Steam公開APIは現在のスナップショットを提供します。"
            "過去のメンバー数・フォロワー数の推移を取得するには、SteamDB.info API（有料プラン）との連携か、"
            "`steam_community_stats()`関数を定期実行（例：毎日のcronジョブ）してデータベースに蓄積することをお勧めします。"
        )

    elif not st.session_state.community_fetched:
        st.markdown(f'<div class="empty-state"><div class="empty-title">{T("no_data")}</div>'
                    f'<div class="empty-sub">Enter a game title and click <strong style="color:var(--blue)">{T("fetch_community")}</strong>.</div></div>',
                    unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════
# MODULE: WISHLIST & TRAFFIC — Req 1
# ═════════════════════════════════════════════════════════════
elif active == "wishlist":
    st.markdown(f"""
    <div class="hero">
      <div class="hero-title">📈 {T("wishlist_title")}<span class="accent">.</span></div>
      <div class="hero-sub">{T("wishlist_sub")}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="query-block">', unsafe_allow_html=True)
    wl_col1, wl_col2 = st.columns([3, 1])
    with wl_col1:
        wl_titles = st.text_area(T("compare_titles"),
                                  value="Like a Dragon Infinite Wealth\nPersona 5 Royal\nFinal Fantasy XVI\nYakuza 0\nOctopath Traveler II",
                                  height=120, key="wl_titles",
                                  placeholder="One game title or App ID per line")
    with wl_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        wl_fetch_btn = st.button(T("fetch_wishlist"), key="wl_fetch", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if wl_fetch_btn:
        titles = [t.strip() for t in wl_titles.strip().split("\n") if t.strip()]
        results = []
        prog = st.progress(0)
        for i, title in enumerate(titles):
            with st.spinner(f"Fetching: {title}"):
                # Search for the app
                search_results = steam_search_game(title, max_results=1)
                if not search_results:
                    prog.progress((i+1)/len(titles))
                    continue
                g = search_results[0]
                appid = g["appid"]

                # SteamSpy data (owners, CCU, etc.)
                spy = steamspy_data(appid)
                # App details
                details = steam_game_details(appid)

                # Build record
                rec = {
                    "appid": appid,
                    "name": spy.get("name", g["name"]),
                    "developer": spy.get("developer",""),
                    "publisher": spy.get("publisher",""),
                    "owners_est": spy.get("owners","N/A"),
                    "peak_ccu": spy.get("peak_ccu",0),
                    "ccu": spy.get("ccu",0),
                    "positive": spy.get("positive",0),
                    "negative": spy.get("negative",0),
                    "average_forever_hrs": round(spy.get("average_forever",0)/60,1),
                    "median_forever_hrs": round(spy.get("median_forever",0)/60,1),
                    "price_usd": details.get("price_overview",{}).get("final_formatted","N/A") if details else "N/A",
                    "release_date": details.get("release_date",{}).get("date","") if details else "",
                    "genres": ", ".join(g["description"] for g in details.get("genres",[])) if details else "",
                    "steam_url": f"https://store.steampowered.com/app/{appid}/",
                    # Wishlist: SteamSpy doesn't expose wishlist count directly in free tier
                    # Best approximation: score_rank or we note it as unavailable
                    "wishlist_note": "See SteamDB (paid) for exact wishlist count",
                }
                rec["total_reviews"] = rec["positive"] + rec["negative"]
                rec["review_score"] = round(100 * rec["positive"] / max(rec["total_reviews"],1), 1)
                results.append(rec)
                time.sleep(0.5)
            prog.progress((i+1)/len(titles))

        st.session_state.wishlist_data = results
        st.session_state.wishlist_fetched = True
        st.session_state.ai_report_wishlist = ""
        st.rerun()

    if st.session_state.wishlist_fetched and st.session_state.wishlist_data:
        wdata = st.session_state.wishlist_data

        for rec in wdata:
            pos_r_val = rec["positive"]
            neg_r_val = rec["negative"]
            rev_score = rec["review_score"]
            score_color = "var(--pos)" if rev_score >= 70 else ("var(--neg)" if rev_score < 40 else "var(--amber)")
            st.markdown(f"""
            <div class="wish-card">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                  <div class="wish-title">{rec["name"]}</div>
                  <div style="font-size:.72rem;color:var(--muted)!important">{rec.get("developer","")} · {rec.get("release_date","")} · {rec.get("genres","")}</div>
                </div>
                <a href="{rec["steam_url"]}" target="_blank" style="color:var(--blue);font-size:.7rem;font-weight:700;text-decoration:none;">Steam ↗</a>
              </div>
              <div class="wish-grid">
                <div class="wish-stat">
                  <div class="wish-stat-label">{T("owners")}</div>
                  <div class="wish-stat-value">{rec["owners_est"]}</div>
                </div>
                <div class="wish-stat">
                  <div class="wish-stat-label">{T("peak_ccu")}</div>
                  <div class="wish-stat-value" style="color:var(--amber)!important">{rec["peak_ccu"]:,}</div>
                </div>
                <div class="wish-stat">
                  <div class="wish-stat-label">{T("reviews_total")}</div>
                  <div class="wish-stat-value" style="color:var(--blue)!important">{rec["total_reviews"]:,}</div>
                </div>
                <div class="wish-stat">
                  <div class="wish-stat-label">Review Score</div>
                  <div class="wish-stat-value" style="color:{score_color}!important">{rev_score}%</div>
                </div>
                <div class="wish-stat">
                  <div class="wish-stat-label">{T("avg_playtime")}</div>
                  <div class="wish-stat-value" style="color:var(--purple)!important">{rec["average_forever_hrs"]}h</div>
                </div>
                <div class="wish-stat">
                  <div class="wish-stat-label">{T("price")}</div>
                  <div class="wish-stat-value" style="color:var(--text)!important">{rec["price_usd"]}</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.info(
            "💡 **Wishlist Counts**: Steam does not expose wishlist data via public API. "
            "Exact wishlist numbers require SteamDB Pro (steamdb.info) or Valve's Steamworks partner dashboard. "
            "For competitive title wishlists, use SteamSpy's `/api.php?request=appdetails` — it occasionally surfaces "
            "relative wishlist rank for public tracking."
            if st.session_state.lang == "en" else
            "💡 **ウィッシュリスト数について**: Steamは公開APIでウィッシュリストデータを公開していません。"
            "正確なウィッシュリスト数にはSteamDB Pro（steamdb.info）またはValveのSteamworksパートナーダッシュボードが必要です。"
        )

        # Comparison charts
        section_header("COMPARATIVE ANALYSIS")
        cdf = pd.DataFrame(wdata)
        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure(go.Bar(x=cdf["name"].str[:20], y=cdf["peak_ccu"],
                                   marker=dict(color="#ffb938")))
            fig.update_layout(**plotly_dark_layout("Peak CCU Comparison"))
            fig.update_xaxes(tickangle=-20)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig2 = go.Figure(go.Bar(x=cdf["name"].str[:20], y=cdf["review_score"],
                                    marker=dict(color=["#20c65a" if v >= 70 else ("#ff3d52" if v < 40 else "#ffb938")
                                                       for v in cdf["review_score"]])))
            fig2.update_layout(**plotly_dark_layout("Review Score %"))
            fig2.update_xaxes(tickangle=-20)
            st.plotly_chart(fig2, use_container_width=True)

        st.download_button(T("download_csv"), data=cdf.to_csv(index=False).encode(),
                           file_name="wishlist_traffic.csv", mime="text/csv")

        tab_ai_wl, = st.tabs(["✨ AI Report"])
        with tab_ai_wl:
            def wishlist_prompt():
                lines = "\n".join(
                    f"  - {r['name']}: owners={r['owners_est']}, peak_ccu={r['peak_ccu']:,}, "
                    f"reviews={r['total_reviews']:,}, score={r['review_score']}%, avgplay={r['average_forever_hrs']}h, price={r['price_usd']}"
                    for r in wdata
                )
                return f"""SEGA Competitive Market Research — Wishlist & Traffic Analysis.

Title comparison data:
{lines}

Generate a strategic market intelligence report:
1. Market Landscape Overview
2. Traffic & Engagement Leaders
3. Player Retention Analysis (avg playtime)
4. Pricing Strategy Comparison
5. Review Sentiment Positioning
6. SEGA Strategic Opportunities & Gaps

Language: {"Japanese" if st.session_state.lang == "ja" else "English"}"""

            if "ai_report_wishlist" not in st.session_state:
                st.session_state.ai_report_wishlist = ""
            render_ai_tab("ai_report_wishlist", wishlist_prompt, slug="wishlist_traffic")

    elif not st.session_state.wishlist_fetched:
        st.markdown(f'<div class="empty-state"><div class="empty-title">{T("no_data")}</div>'
                    f'<div class="empty-sub">Enter game titles (one per line) and click <strong style="color:var(--blue)">{T("fetch_wishlist")}</strong>.</div></div>',
                    unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════
# MODULE: MARKET INTELLIGENCE — Req 4 (genre-agnostic)
# ═════════════════════════════════════════════════════════════
elif active == "market_intel":
    st.markdown(f"""
    <div class="hero">
      <div class="hero-title">🎯 {T("market_title")}<span class="accent">.</span></div>
      <div class="hero-sub">{T("market_sub")}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="query-block">', unsafe_allow_html=True)
    mi_col1, mi_col2, mi_col3 = st.columns([2, 2, 1])
    with mi_col1:
        mi_genre = st.selectbox(T("select_genre_intel"), list(GENRE_PRESETS.keys()),
                                 index=list(GENRE_PRESETS.keys()).index("RPG"),
                                 key="mi_genre_sel")
        if mi_genre == "Custom":
            mi_custom_tag = st.text_input("Custom Steam tag/genre", key="mi_custom_tag", placeholder="e.g. Metroidvania, Soulslike")
    with mi_col2:
        mi_analysis_type = st.selectbox(T("analysis_type"), [
            T("an_ccu"), T("an_table"), T("an_social"), T("an_weekly"), T("an_custom")
        ], key="mi_analysis_type")
    with mi_col3:
        mi_fetch_ccu_btn = st.button(T("fetch_ccu"), key="mi_fetch_ccu")

    if mi_analysis_type == T("an_custom"):
        mi_custom_q = st.text_area(T("custom_query"),
                                    placeholder="e.g. What are the key design differentiators between top-performing RPGs and mid-tier ones?",
                                    height=80, key="mi_custom_q")
    st.markdown("</div>", unsafe_allow_html=True)

    if mi_fetch_ccu_btn:
        genre_tag = GENRE_PRESETS[mi_genre]["steamspy_genre"]
        if mi_genre == "Custom":
            genre_tag = st.session_state.get("mi_custom_tag", "Action")

        with st.spinner(T("loading")):
            raw_games = steamspy_genre(genre_tag, max_pages=2)
            if not raw_games:
                raw_games = steamspy_genre("Action", max_pages=1)

            # Sort by CCU
            raw_games.sort(key=lambda g: g.get("ccu",0), reverse=True)
            ccu_data = []
            for g in raw_games[:30]:
                owners = g.get("owners","N/A")
                ccu = g.get("ccu", 0)
                peak = g.get("peak_ccu",0)
                positive = g.get("positive",0)
                negative = g.get("negative",0)
                total_rev = positive + negative
                score = round(100 * positive / max(total_rev, 1), 1)
                prev_ccu = g.get("ccu_yesterday", ccu)
                yoy = "▲" if ccu >= prev_ccu else "▼"
                ccu_data.append({
                    "appid": g.get("appid",0),
                    "name": g.get("name",""),
                    "ccu": ccu,
                    "peak_ccu": peak,
                    "owners": owners,
                    "positive": positive,
                    "negative": negative,
                    "review_score": score,
                    "avg_play_hrs": round(g.get("average_forever",0)/60,1),
                    "price": g.get("initialprice",0)/100,
                    "yoy": yoy,
                })
            st.session_state.market_ccu = ccu_data
            st.session_state.market_genre = mi_genre
            st.session_state.market_fetched = True
            st.session_state.ai_report_market = ""
            st.rerun()

    if st.session_state.market_fetched and st.session_state.market_ccu:
        ccu_data = st.session_state.market_ccu
        genre_name = st.session_state.market_genre
        ccu_df = pd.DataFrame(ccu_data)

        total_ccu = ccu_df["ccu"].sum()
        top_game = ccu_df.iloc[0]["name"] if len(ccu_df) > 0 else ""
        top_ccu = ccu_df.iloc[0]["ccu"] if len(ccu_df) > 0 else 0
        avg_score = ccu_df["review_score"].mean()

        metric_row([
            {"label": "Genre", "value": genre_name, "color": "var(--blue)"},
            {"label": "Games Tracked", "value": len(ccu_df), "color": "var(--text)"},
            {"label": "Total CCU", "value": f"{total_ccu:,}", "color": "var(--amber)"},
            {"label": "#1 Game", "value": top_game[:20], "color": "var(--pos)"},
            {"label": "Top CCU", "value": f"{top_ccu:,}", "color": "var(--cyan)"},
            {"label": "Avg Review Score", "value": f"{avg_score:.1f}%", "color": "var(--purple)"},
        ])

        tab_ccu_live, tab_charts, tab_ai_mi = st.tabs([
            f"📡 Live CCU ({len(ccu_df)})", "📊 Charts", "✨ AI Report"
        ])

        with tab_ccu_live:
            section_header(f"TOP {genre_name.upper()} GAMES BY CCU")
            for _, row in ccu_df.iterrows():
                bar_w = min(100, int(100 * row["ccu"] / max(top_ccu, 1)))
                st.markdown(f"""
                <div class="ccu-row">
                  <div style="display:flex;flex-direction:column;flex:1;min-width:0;">
                    <div class="ccu-name">{row["name"][:45]}</div>
                    <div style="height:3px;background:var(--surface3);border-radius:2px;margin-top:.25rem;">
                      <div style="width:{bar_w}%;height:3px;background:var(--blue);border-radius:2px;"></div>
                    </div>
                  </div>
                  <div style="display:flex;gap:1.5rem;align-items:center;flex-shrink:0;margin-left:1rem;">
                    <div style="text-align:right;">
                      <div style="font-size:.5rem;color:var(--muted)!important;text-transform:uppercase;letter-spacing:.1em">CCU</div>
                      <div class="ccu-val">{row["ccu"]:,}</div>
                    </div>
                    <div style="text-align:right;">
                      <div style="font-size:.5rem;color:var(--muted)!important;text-transform:uppercase;letter-spacing:.1em">Reviews</div>
                      <div style="font-size:.85rem;font-weight:600;color:{'var(--pos)' if row['review_score']>=70 else 'var(--neg)'}!important">{row["review_score"]}%</div>
                    </div>
                    <div style="text-align:right;">
                      <div style="font-size:.5rem;color:var(--muted)!important;text-transform:uppercase;letter-spacing:.1em">Peak</div>
                      <div style="font-size:.8rem;color:var(--text-dim)!important">{row["peak_ccu"]:,}</div>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

            st.download_button(T("download_csv"), data=ccu_df.to_csv(index=False).encode(),
                               file_name=f"market_intel_{genre_name.lower()}.csv", mime="text/csv")

        with tab_charts:
            c1, c2 = st.columns(2)
            with c1:
                section_header("CCU DISTRIBUTION")
                top15 = ccu_df.head(15)
                fig = go.Figure(go.Bar(
                    x=top15["ccu"], y=top15["name"].str[:25],
                    orientation="h", marker=dict(color="#ffb938"),
                ))
                fig.update_layout(**plotly_dark_layout())
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                section_header("REVIEW SCORE vs AVG PLAYTIME")
                fig2 = go.Figure(go.Scatter(
                    x=ccu_df["avg_play_hrs"], y=ccu_df["review_score"],
                    mode="markers+text",
                    text=ccu_df["name"].str[:15],
                    textposition="top center",
                    marker=dict(
                        size=ccu_df["ccu"].apply(lambda x: max(6, min(30, x//500))),
                        color=ccu_df["review_score"],
                        colorscale="RdYlGn",
                        showscale=True,
                    ),
                ))
                fig2.update_layout(**plotly_dark_layout("Review Score vs Avg Playtime (bubble=CCU)"))
                fig2.update_xaxes(title_text="Avg Playtime (hrs)")
                fig2.update_yaxes(title_text="Review Score %")
                st.plotly_chart(fig2, use_container_width=True)

        with tab_ai_mi:
            analysis_mode = st.session_state.get("mi_analysis_type", T("an_ccu"))

            def build_market_prompt():
                ccu_lines = "\n".join(
                    f"  {i+1}. {r['name']}: CCU={r['ccu']:,}, peak={r['peak_ccu']:,}, "
                    f"review={r['review_score']}%, avgPlay={r['avg_play_hrs']}h, owners={r['owners']}"
                    for i, r in ccu_df.head(20).iterrows()
                )
                base = f"Genre: {genre_name} | {len(ccu_df)} titles tracked | Total CCU: {total_ccu:,}\n\n{ccu_lines}\n\n"
                lang_str = "Japanese" if st.session_state.lang == "ja" else "English"

                if analysis_mode == T("an_ccu"):
                    return base + f"Write a CCU Landscape analysis covering market leaders, tier distribution, and SEGA positioning opportunities. Language: {lang_str}"
                elif analysis_mode == T("an_table"):
                    return base + f"Write a Table Stakes analysis: what features do top games share? What is the baseline a new title must meet? Language: {lang_str}"
                elif analysis_mode == T("an_social"):
                    return base + f"Write a Social Metrics analysis: correlate review scores with player retention (avg playtime) and identify community health signals. Language: {lang_str}"
                elif analysis_mode == T("an_weekly"):
                    return base + f"Write a Weekly Market Report: executive briefing suitable for SEGA leadership, covering winners, losers, trends, and immediate opportunities. Language: {lang_str}"
                else:
                    custom_q = st.session_state.get("mi_custom_q","Analyse the competitive landscape.")
                    return base + f"Question: {custom_q}\n\nLanguage: {lang_str}"

            def market_chat_system():
                ccu_ctx = "\n".join(f"- {r['name']}: {r['ccu']:,} CCU" for r in ccu_data[:10])
                return (f"You are a senior games market analyst at SEGA. Genre: {genre_name}.\n"
                        f"Live CCU data:\n{ccu_ctx}\n\n"
                        f"Report: {st.session_state.get('ai_report_market','')[:3000]}")

            if "ai_report_market" not in st.session_state:
                st.session_state.ai_report_market = ""
            render_ai_tab("ai_report_market", build_market_prompt, market_chat_system, slug=f"market_intel_{genre_name.lower()}")

    elif not st.session_state.market_fetched:
        st.markdown(f'<div class="empty-state"><div class="empty-title">{T("no_data")}</div>'
                    f'<div class="empty-sub">Select a genre and click <strong style="color:var(--blue)">{T("fetch_ccu")}</strong> to load live market data.</div></div>',
                    unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="footer">
  <div class="footer-brand">SEGA SOCIAL INTELLIGENCE PLATFORM v2.0</div>
  <div class="footer-note">
    Reddit (public JSON) · X/Twitter API v2 · Discord API · Steam Store API · SteamSpy ·
    Powered by Claude · Internal analytics use only
  </div>
</div>
""", unsafe_allow_html=True)