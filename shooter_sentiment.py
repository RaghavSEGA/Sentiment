"""
shooter_intel.py — SEGA Shooter Market Intelligence — Dashboard
================================================================
Entry point for the multipage app. Run with:
    streamlit run shooter_intel.py

This page owns roster selection and the live CCU fetch — every other page
(Weekly Report, Deep Dive, Monthly Analysis, Admin) reads st.session_state
that this page populates. Visit this page first on a new session.

See common.py for shared constants, data fetchers, prompt builders, export
functions, translations, and auth.
"""

import concurrent.futures
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from common import *  # noqa: F401,F403 — shared module; see common.py docstring
from common import _fetch_one_game  # leading underscore — import * skips these

# ─────────────────────────────────────────────────────────────
# PAGE SETUP  (must run before any other Streamlit call)
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="SEGA Shooter Intel — Dashboard",
    page_icon=":material/target:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_defaults()
require_auth()
render_topbar()

# ─────────────────────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="hero">
  <div class="hero-title">{T("hero_line1")}<br><span class="accent">{T("hero_line2")}</span></div>
  <div class="hero-sub">{T("hero_sub")}</div>
</div>
""", unsafe_allow_html=True)

st.page_link("pages/1_Weekly_Report.py", label="Weekly Report & AI Analysis", icon="📝")
_nav1, _nav2, _nav3 = st.columns(3)
with _nav1:
    st.page_link("pages/2_Deep_Dive.py", label="Game Deep Dive", icon="🔍")
with _nav2:
    st.page_link("pages/3_Monthly_Analysis.py", label="Monthly Analysis", icon="📅")
with _nav3:
    st.page_link("pages/4_Admin.py", label="Admin & Settings", icon="⚙️")

# ─────────────────────────────────────────────────────────────
# QUERY BLOCK
# ─────────────────────────────────────────────────────────────

st.markdown('<div class="query-block">', unsafe_allow_html=True)

#  Genre toggle + game picker
st.markdown(f"""
<div class="section-header" style="margin-top:0">
  <span class="dot"></span>{T("dataset_header")}
</div>
""", unsafe_allow_html=True)

_g_col1, _g_col2, _g_col3, _g_spacer = st.columns([1, 1, 1, 3])
with _g_col1:
    _fps_active = st.session_state.roster_genre == "FPS"
    if st.button(T("btn_fps"), key="btn_fps",
        type="primary" if _fps_active else "secondary", use_container_width=True):
        if not _fps_active:
            st.session_state.roster_genre  = "FPS"
            st.session_state.roster_filter = []
            st.session_state.ccu_data      = []
            st.session_state.active_query  = None
            st.session_state.ai_report     = ""
            st.rerun()
with _g_col2:
    _tps_active = st.session_state.roster_genre == "TPS"
    if st.button(T("btn_tps"), key="btn_tps",
        type="primary" if _tps_active else "secondary", use_container_width=True):
        if not _tps_active:
            st.session_state.roster_genre  = "TPS"
            st.session_state.roster_filter = []
            st.session_state.ccu_data      = []
            st.session_state.active_query  = None
            st.session_state.ai_report     = ""
            st.rerun()
with _g_col3:
    _both_active = st.session_state.roster_genre == "BOTH"
    if st.button(T("btn_both"), key="btn_both",
        type="primary" if _both_active else "secondary", use_container_width=True):
        if not _both_active:
            st.session_state.roster_genre  = "BOTH"
            st.session_state.roster_filter = []
            st.session_state.ccu_data      = []
            st.session_state.active_query  = None
            st.session_state.ai_report     = ""
            st.rerun()

# Build full roster for active genre
if st.session_state.roster_genre == "BOTH":
    _both_ids    = list(dict.fromkeys(FPS_ROSTER_IDS + TPS_ROSTER_IDS))
    _full_roster = [{"app_id": a, **GAME_CATALOG[a]} for a in _both_ids if a in GAME_CATALOG]
else:
    _full_roster = get_roster(st.session_state.roster_genre)
_all_names   = [g["name"] for g in _full_roster]
_all_ids     = [g["app_id"] for g in _full_roster]
_genre_label = "First-Person Shooters" if st.session_state.roster_genre == "FPS" else ("Third-Person Shooters" if st.session_state.roster_genre == "TPS" else "FPS + TPS Combined")

# Game picker — inside expander to keep UI clean
_prev_filter = st.session_state.roster_filter
_active_count = len(_prev_filter) if _prev_filter else len(_all_names)
_expander_label = T("games_included", n=_active_count, total=len(_all_names))

with st.expander(_expander_label, expanded=False):
    _col_a, _col_b = st.columns([1, 1])
    with _col_a:
        if st.button(T("select_all"), key="picker_all", use_container_width=True):
            st.session_state.roster_filter = []
            st.session_state.ccu_data      = []
            st.rerun()
    with _col_b:
        if st.button(T("clear_all"), key="picker_clear", use_container_width=True):
            st.session_state.roster_filter = [_all_ids[0]]  # keep at least 1
            st.session_state.ccu_data      = []
            st.rerun()

    _filter_names = st.multiselect(
        "Select games",
        options=_all_names,
        default=[g["name"] for g in _full_roster if g["app_id"] in _prev_filter] if _prev_filter else _all_names,
        key="game_multiselect",
        label_visibility="collapsed",
    )
    _new_filter = [_all_ids[_all_names.index(n)] for n in _filter_names]
    if set(_new_filter) != set(_prev_filter):
        st.session_state.roster_filter = _new_filter
        st.session_state.ccu_data      = []
        st.rerun()

# Clear stale filter IDs that don't belong to the current roster
if st.session_state.roster_filter:
    _valid = [i for i in st.session_state.roster_filter if i in _all_ids]
    if _valid != st.session_state.roster_filter:
        st.session_state.roster_filter = _valid

# Apply filter → active roster
_active_ids    = st.session_state.roster_filter or _all_ids
_active_roster = [g for g in _full_roster if g["app_id"] in _active_ids]
st.session_state["_active_roster"] = _active_roster

# Overlap info
_overlap       = set(FPS_ROSTER_IDS) & set(TPS_ROSTER_IDS)
_overlap_shown = [GAME_CATALOG[a]["name"] for a in _overlap
                  if a in _active_ids and a in GAME_CATALOG]
if _overlap_shown:
    st.caption(T("overlap_note", n=len(_overlap_shown), names=", ".join(sorted(_overlap_shown))))

# ─────────────────────────────────────────────────────────────
# LIVE CCU PANEL
# ─────────────────────────────────────────────────────────────

if not st.session_state.ccu_data:
    # Try daily cache first
    _active_ids_for_cache = [g["app_id"] for g in st.session_state.get("_active_roster", [])]
    _cache = load_daily_cache(st.session_state.roster_genre, _active_ids_for_cache)
    if _cache and not st.session_state.get("force_refresh"):
        st.session_state.ccu_data  = _cache["ccu_data"]
        st.session_state.ai_report = _cache.get("ai_report", "")
        if st.session_state.ai_report:
            st.session_state.active_query = "weekly_report"
            st.session_state.report_label = _cache.get("report_label",
                f"Weekly Report — {st.session_state.roster_genre}")
        st.toast(T("cache_loaded_toast", age=cache_age_str()), icon="📦")
        st.rerun()
    else:
        st.session_state.force_refresh = False

if not st.session_state.ccu_data:
    with st.spinner(T("fetch_spinner")):
        roster      = st.session_state.get("_active_roster", get_roster("FPS"))
        roster_ids  = frozenset(g["app_id"] for g in roster)
        total       = len(roster)

        # Load CSVs for this roster only (lazy — skips unrelated files on disk)
        historical = load_all_historical(roster_ids)
        raw_data   = load_all_raw(roster_ids)
        # Snapshots are small (JSON) — load once in the main thread, pass to all workers
        _snapshots = load_ccu_snapshots()

        prog   = st.progress(0.0)
        status = st.empty()
        status.caption(f"Fetching {total} titles in parallel…")

        results: list[dict] = []
        _placeholder: dict = {   # returned when a worker raises an exception
            "ccu": 0, "ccu_from_csv": False, "ccu_live": False,
            "twitch_viewers": None, "yoy": "N/A", "yoy_val": 0,
            "yoy_source": "steamspy", "has_hist": False,
            "hist_summary": {}, "avg_2w_hrs": 0,
            "review_pct": None, "review_velocity": None,
            "pos_reviews": 0, "neg_reviews": 0,
        }

        # Spawn up to 12 workers.  SteamSpy concurrency is capped separately
        # by _STEAMSPY_SEM (Semaphore(4)) inside each worker.
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as _pool:
            _futures = {
                _pool.submit(_fetch_one_game, game, historical, raw_data, _snapshots): game
                for game in roster
            }
            _done = 0
            for _fut in concurrent.futures.as_completed(_futures):
                _done += 1
                _game = _futures[_fut]
                prog.progress(_done / total)
                status.caption(
                    T("fetching_game", name=_game["name"])
                    + f" ({_done}/{total})"
                )
                try:
                    results.append(_fut.result())
                except Exception as _exc:
                    # Keep a zero-CCU placeholder so the game still appears
                    results.append({**_game, **_placeholder})

        status.empty()
        results.sort(key=lambda x: x["ccu"], reverse=True)
        st.session_state.ccu_data = results
        save_ccu_snapshot(results)  # persist live CCU for future WoW comparison
        save_daily_cache(
            st.session_state.get("roster_genre", "FPS"),
            [r["app_id"] for r in results],
            results, "",
        )
        if not st.session_state.active_query:
            _genre_for_label = st.session_state.get("roster_genre", "FPS")
            st.session_state.active_query    = "weekly_report"
            st.session_state.report_label    = f"Weekly Report — {_genre_for_label}"
            st.session_state.ai_report       = ""
            st.session_state.ai_chat_history = []
        st.rerun()
else:
    ccu_data = st.session_state.ccu_data
raw_data = load_all_raw(frozenset(r["app_id"] for r in ccu_data))
live_ccu_map = {r["app_id"]: r["ccu"] for r in ccu_data}
wow_diff = compute_period_diff(raw_data, live_ccu_map, days=7)
st.session_state["_wow_diff_cache"] = wow_diff
n_wow    = len(wow_diff)

#  Derived stats
total_ccu    = sum(r["ccu"] for r in ccu_data)
growing      = sum(1 for r in ccu_data if r.get("yoy_val", 0) > 0)
declining    = sum(1 for r in ccu_data if r.get("yoy_val", 0) < 0)
yoy_titled   = [(r["name"], r["yoy_val"]) for r in ccu_data if r.get("yoy_val") not in (0, None) and r.get("yoy") != "N/A"]
best_mover   = max(yoy_titled, key=lambda x: x[1], default=("—", 0))
worst_mover  = min(yoy_titled, key=lambda x: x[1], default=("—", 0))
hist_count   = sum(1 for r in ccu_data if r.get("has_hist"))
health_ratios= [r["ccu"] / r["hist_summary"]["peak_ever"] * 100
                for r in ccu_data if r.get("hist_summary", {}).get("peak_ever") and r["ccu"] > 0]
avg_health   = sum(health_ratios) / len(health_ratios) if health_ratios else 0
wow_up   = sum(1 for v in wow_diff.values() if v["delta"] > 0)
wow_down = sum(1 for v in wow_diff.values() if v["delta"] < 0)
mom_up   = sum(1 for r in ccu_data if ((r.get("hist_summary") or {}).get("mom_pct") or 0) > 0)
mom_down = sum(1 for r in ccu_data if ((r.get("hist_summary") or {}).get("mom_pct") or 0) < 0)
mom_total= mom_up + mom_down

# Translated column names — defined once, reused by all tables below.
# html_table's +/- colouring works for both EN and JP names (_DELTA_COLS).
_C_TITLE   = T("col_title")
_C_YEAR    = T("col_year")
_C_LIVE    = T("col_live_ccu")
_C_7D      = T("col_7d_ago")
_C_DCCU    = T("col_change_ccu")
_C_WPCT    = T("col_weekly_change")
_C_STEAM   = T("col_steam_page")
_C_1YR     = T("col_1yr_ago")
_C_ANNUAL  = T("col_annual_change")
_C_MONTH   = T("col_month_change")

#  Row 1: Primary KPI cards
_kc1, _kc2, _kc3 = st.columns(3)
with _kc1:
    st.markdown(f"""<div class="metric-card blue-top">
    <div class="metric-label">{T("kpi_total_ccu")}</div>
    <div class="metric-value">{total_ccu:,}</div>
    <div class="metric-sub">{T("kpi_total_sub", n=len(ccu_data))}</div>
    </div>""", unsafe_allow_html=True)
with _kc2:
    health_color = "var(--pos)" if avg_health > 50 else "var(--amber)" if avg_health > 25 else "var(--neg)"
    st.markdown(f"""<div class="metric-card amber-top">
    <div class="metric-label">{T("kpi_health")}</div>
    <div class="metric-value" style="color:{health_color}">{avg_health:.0f}%</div>
    <div class="metric-sub">{T("kpi_health_sub")}</div>
    </div>""", unsafe_allow_html=True)
with _kc3:
    _total_twitch = sum(r.get("twitch_viewers") or 0 for r in ccu_data)
    _twitch_titles = sum(1 for r in ccu_data if r.get("twitch_viewers") is not None)
    if _total_twitch:
        _tw_disp = f"{_total_twitch:,}"
        _tw_sub  = T("kpi_twitch_sub", n=_twitch_titles)
    else:
        _tw_disp = "—"
        _tw_sub  = T("kpi_twitch_none")
    st.markdown(f"""<div class="metric-card purple-top">
    <div class="metric-label">{T("kpi_twitch")}</div>
    <div class="metric-value">{_tw_disp}</div>
    <div class="metric-sub">{_tw_sub}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

#  WoW expander
with st.expander(T("wow_expander", up=wow_up, down=wow_down)):
    if wow_diff:
        _w_up   = [r["name"] for r in ccu_data if wow_diff.get(r["app_id"], {}).get("delta", 0) > 0]
        _w_down = [r["name"] for r in ccu_data if wow_diff.get(r["app_id"], {}).get("delta", 0) < 0]
        if _w_up:
            st.markdown(f"<span style='color:#20c65a'>**{T('growth_label')} ({len(_w_up)}):** {', '.join(_w_up)}</span>", unsafe_allow_html=True)
        if _w_down:
            st.markdown(f"<span style='color:#ff4d4d'>**{T('decline_label')} ({len(_w_down)}):** {', '.join(_w_down)}</span>", unsafe_allow_html=True)
        wow_rows = []
        for r in ccu_data:
            d = wow_diff.get(r["app_id"])
            if d:
                wow_rows.append({
                    _C_TITLE: r["name"],
                    _C_YEAR:  str(r.get("year", "—")),
                    _C_LIVE:  f"{d['curr_ccu']:,}",
                    _C_7D:    f"{d['prev_ccu']:,}",
                    _C_DCCU:  d["delta"],
                    _C_WPCT:  round(d["delta_pct"]),
                    _C_STEAM: f'<a href="https://store.steampowered.com/app/{r["app_id"]}/" target="_blank" style="color:#4080ff">{T("store_link")}</a>',
                })
        if wow_rows:
            wow_rows_sorted = sorted(wow_rows, key=lambda x: x[_C_WPCT], reverse=True)
            for r2 in wow_rows_sorted:
                r2[_C_DCCU] = f"+{r2[_C_DCCU]:,}" if r2[_C_DCCU] > 0 else f"{r2[_C_DCCU]:,}"
                r2[_C_WPCT] = f"+{r2[_C_WPCT]}%" if r2[_C_WPCT] > 0 else f"{r2[_C_WPCT]}%"
            render_table(wow_rows_sorted,
                [_C_TITLE, _C_YEAR, _C_LIVE, _C_7D, _C_DCCU, _C_WPCT, _C_STEAM])
    else:
        st.info(T("wow_none", appid="{appid}"))

#  MoM expander
with st.expander(T("mom_expander", up=mom_up, down=mom_down)):
    _m_up   = [r["name"] for r in ccu_data if ((r.get("hist_summary") or {}).get("mom_pct") or 0) > 0]
    _m_down = [r["name"] for r in ccu_data if ((r.get("hist_summary") or {}).get("mom_pct") or 0) < 0]
    if _m_up:
        st.markdown(f"<span style='color:#20c65a'>**{T('growth_label')} ({len(_m_up)}):** {', '.join(_m_up)}</span>", unsafe_allow_html=True)
    if _m_down:
        st.markdown(f"<span style='color:#ff4d4d'>**{T('decline_label')} ({len(_m_down)}):** {', '.join(_m_down)}</span>", unsafe_allow_html=True)
    mom_rows = []
    for r in ccu_data:
        hs = r.get("hist_summary") or {}
        pct = hs.get("mom_pct")
        if pct is not None:
            mom_rows.append({
                _C_TITLE: r["name"],
                _C_LIVE:  f"{r['ccu']:,}",
                _C_MONTH: round(pct),
            })
    if mom_rows:
        mom_df = pd.DataFrame(
            sorted(mom_rows, key=lambda x: x[_C_MONTH], reverse=True)
        )
        mom_rows_sorted = mom_df.to_dict("records")
        for r2 in mom_rows_sorted:
            r2[_C_MONTH] = f"+{r2[_C_MONTH]}%" if r2[_C_MONTH] > 0 else f"{r2[_C_MONTH]}%"
        render_table(mom_rows_sorted, [_C_TITLE, _C_LIVE, _C_MONTH])
    else:
        st.info(T("yoy_none"))

#  YoY breakdown expander
with st.expander(T("yoy_expander", up=growing, down=declining)):
    _y_up   = [r["name"] for r in ccu_data if r.get("yoy_val", 0) > 0]
    _y_down = [r["name"] for r in ccu_data if r.get("yoy_val", 0) < 0]
    if _y_up:
        st.markdown(f"<span style='color:#20c65a'>**{T('growth_label')} ({len(_y_up)}):** {', '.join(_y_up)}</span>", unsafe_allow_html=True)
    if _y_down:
        st.markdown(f"<span style='color:#ff4d4d'>**{T('decline_label')} ({len(_y_down)}):** {', '.join(_y_down)}</span>", unsafe_allow_html=True)
    if yoy_titled:
        yoy_rows = []
        for r in ccu_data:
            if r.get("yoy_val") in (0, None) or r.get("yoy") == "N/A":
                continue
            hs = r.get("hist_summary") or {}
            live = r["ccu"]
            yr_ago = hs.get("yoy_ccu")
            pct = round(r["yoy_val"])
            yoy_rows.append({
                _C_TITLE:  r["name"],
                _C_LIVE:   f"{live:,}",
                _C_1YR:    f"{yr_ago:,}" if yr_ago else "N/A",
                _C_ANNUAL: pct,
            })
        if yoy_rows:
            yoy_df = pd.DataFrame(
                sorted(yoy_rows, key=lambda x: x[_C_ANNUAL] if isinstance(x[_C_ANNUAL], (int, float)) else 0, reverse=True)
            )
            yoy_rows_sorted = yoy_df.to_dict("records")
            for r2 in yoy_rows_sorted:
                r2[_C_ANNUAL] = f"+{r2[_C_ANNUAL]}%" if r2[_C_ANNUAL] > 0 else f"{r2[_C_ANNUAL]}%"
            render_table(yoy_rows_sorted,
                [_C_TITLE, _C_LIVE, _C_1YR, _C_ANNUAL])
    else:
        st.info(T("yoy_none"))

st.caption(T("formulas_caption"))

#  Sub-genre heatmap
with st.expander(T("heatmap_expander")):
    sub_totals: dict[str, int] = {}
    for r in ccu_data:
        sub_totals[r["sub"]] = sub_totals.get(r["sub"], 0) + r["ccu"]
    sub_items = sorted(sub_totals.items(), key=lambda x: x[1], reverse=True)
    if sub_items:
        fig_h = go.Figure(go.Bar(
            x=[s[0] for s in sub_items],
            y=[s[1] for s in sub_items],
            marker_color="#4080ff",
            text=[f"{s[1]:,}" for s in sub_items],
            textposition="outside",
            textfont=dict(size=9, color="#b8bcd4"),
        ))
        _heatmap_layout = {**PLOTLY_BASE, "margin": dict(l=10, r=10, t=20, b=80)}
        fig_h.update_layout(
            **_heatmap_layout,
            height=300,
            xaxis=dict(tickfont=dict(size=9), tickangle=-30, showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#1a1e30", tickformat=","),
            showlegend=False,
        )
        st.plotly_chart(fig_h, use_container_width=True)
        st.caption(T("heatmap_caption"))

# ── Top 25 bar chart (active roster, sorted by live CCU) ──
_genre_label_chart = {"FPS":"FPS","TPS":"TPS","BOTH":"FPS+TPS"}.get(st.session_state.roster_genre,"FPS")
top_n = ccu_data[:25]
rest_n = []  # all 25 in main chart

def _wow_color(r):
    d = wow_diff.get(r["app_id"])
    if d and d["delta"] > 0:  return "#20c65a"  # green = WoW up
    if d and d["delta"] < 0:  return "#ff4d4d"  # red   = WoW down
    return "#888aaa"                              # grey  = no data

hover_texts = []
for r in top_n:
    d = wow_diff.get(r["app_id"])
    wow_str = f"<br>WoW: {d['delta_pct']:+.1f}% ({d['period_label']})" if d else ""
    hover_texts.append(f"<b>{r['name']}</b><br>CCU: {r['ccu']:,}<br>YoY: {r.get('yoy','N/A')}{wow_str}<extra></extra>")
colors = [_wow_color(r) for r in top_n]
_top_labels = [f"#{i+1} {r['name']}" for i, r in enumerate(top_n)]
fig = go.Figure(go.Bar(
    x=_top_labels,
    y=[r["ccu"] for r in top_n],
    marker_color=colors,
    text=[f"{r['ccu']:,}" for r in top_n],
    textposition="outside",
    textfont=dict(size=10, color="#b8bcd4"),
    hovertemplate=hover_texts,
))
fig.update_layout(
    **PLOTLY_BASE,
    title=dict(text=T("chart_top25_title", n=len(top_n), genre=_genre_label_chart),
               font=dict(size=13, color="#b8bcd4"), x=0),
    xaxis=dict(showgrid=False, tickfont=dict(size=10), tickangle=-30, linecolor="#232640"),
    yaxis=dict(showgrid=True, gridcolor="#1a1e30", tickformat=","),
    height=340, showlegend=False,
)
st.plotly_chart(fig, use_container_width=True)
st.caption(T("chart_caption", genre=_genre_label_chart))

# ── Ranks 11-25 bar chart ──
if rest_n:
    hover_texts_r = []
    for r in rest_n:
        d = wow_diff.get(r["app_id"])
        wow_str = f"<br>WoW: {d['delta_pct']:+.1f}% ({d['period_label']})" if d else ""
        hover_texts_r.append(f"<b>{r['name']}</b><br>CCU: {r['ccu']:,}<br>YoY: {r.get('yoy','N/A')}{wow_str}<extra></extra>")
    colors_r = [_wow_color(r) for r in rest_n]
    rank_labels = [f"#{i+11} {r['name']}" for i, r in enumerate(rest_n)]
    fig_r = go.Figure(go.Bar(
        x=rank_labels,
        y=[r["ccu"] for r in rest_n],
        marker_color=colors_r,
        text=[f"{r['ccu']:,}" for r in rest_n],
        textposition="outside",
        textfont=dict(size=10, color="#b8bcd4"),
        hovertemplate=hover_texts_r,
    ))
    fig_r.update_layout(
        **PLOTLY_BASE,
        title=dict(text=T("chart_ranks_title", start=11, end=len(ccu_data), genre=_genre_label_chart),
                   font=dict(size=13, color="#b8bcd4"), x=0),
        xaxis=dict(showgrid=False, tickfont=dict(size=9), tickangle=-30, linecolor="#232640"),
        yaxis=dict(showgrid=True, gridcolor="#1a1e30", tickformat=","),
        height=320, showlegend=False,
    )
    st.plotly_chart(fig_r, use_container_width=True)
    st.caption(T("chart_caption", genre=_genre_label_chart))

#  Full data table
_tbl_genre = st.session_state.get("roster_genre", "FPS")
with st.expander(T("table_expander", genre=_tbl_genre)):
    _C_RANK = T("col_rank");      _C_SUB  = T("col_subgenre")
    _C_PUB  = T("col_publisher"); _C_F2P  = T("col_f2p")
    _C_YOY  = T("col_yoy");       _C_PEAK = T("col_peak_ever")
    _C_P12  = T("col_peak_12m");  _C_A12  = T("col_avg_ccu_12m")
    _C_MOM  = T("col_mom");       _C_REV  = T("col_review")
    _C_TWIT = T("col_twitch");    _C_VEL  = T("col_rev_velocity")
    _C_YSRC = T("col_yoy_source")
    _src_map = {"snapshot": "Snapshot", "csv": "SteamDB", "steamspy": "SteamSpy"}
    df = pd.DataFrame([{
        _C_RANK: i + 1,
        _C_TITLE: r["name"],
        _C_SUB:   r["sub"],
        _C_PUB:   r["publisher"],
        _C_F2P:   T("yes") if r["f2p"] else T("no"),
        _C_LIVE:  f"{r['ccu']:,} *" if r.get("ccu_from_csv") else f"{r['ccu']:,}",
        _C_TWIT:  f"{r['twitch_viewers']:,}" if r.get("twitch_viewers") is not None else "—",
        _C_YOY:   r.get("yoy", "N/A"),
        _C_YSRC:  _src_map.get(r.get("yoy_source", "steamspy"), "—"),
        _C_PEAK:  f"{r['hist_summary']['peak_ever']:,}" if r.get("hist_summary", {}).get("peak_ever") else "—",
        _C_P12:   f"{r['hist_summary']['peak_12m']:,}" if r.get("hist_summary", {}).get("peak_12m")  else "—",
        _C_A12:   f"{r['hist_summary']['avg_12m']:,}" if r.get("hist_summary", {}).get("avg_12m")   else "—",
        _C_MOM:   r.get("hist_summary", {}).get("mom_trend", "—"),
        _C_REV:   f"{r['review_pct']}%" if r.get("review_pct") else "—",
        _C_VEL:   f"+{r['review_velocity']}/day" if r.get("review_velocity") is not None else "—",
    } for i, r in enumerate(ccu_data)])

    render_table(df.to_dict("records"),
        [_C_RANK, _C_TITLE, _C_SUB, _C_PUB, _C_F2P,
         _C_LIVE, _C_TWIT, _C_YOY, _C_YSRC,
         _C_PEAK, _C_P12, _C_A12, _C_MOM, _C_REV, _C_VEL],
        height=len(df) * 36 + 60)
    st.caption(T("table_footnote"))

#  Monthly history chart
hist_titles = [r for r in ccu_data if r.get("has_hist")]
if hist_titles:
    historical = load_all_historical(frozenset(r["app_id"] for r in hist_titles))
    with st.expander(T("history_expander")):
        fig2 = go.Figure()
        # Collect all x values across all traces for event matching
        _all_x_sets: dict[int, list[str]] = {}
        for r in hist_titles:
            mdf = historical.get(r["app_id"])
            if mdf is not None and not mdf.empty:
                last_24 = mdf.tail(24)
                x_vals = [str(p) for p in last_24["month"]]
                _all_x_sets[r["app_id"]] = x_vals
                # Build hover text with events for this game
                events = get_game_events(r["app_id"])
                event_map = {e[0][:7]: e[1] for e in events}
                hover = []
                for x, y in zip(x_vals, last_24["peak_ccu"]):
                    ev = event_map.get(x[:7], "")
                    ev_str = f"<br><b>{ev}</b>" if ev else ""
                    y_str = f"{int(y):,}" if y == y else "N/A"  # NaN-safe
                    hover.append(f"<b>{r['name']}</b><br>{x}<br>Peak CCU: {y_str}{ev_str}<extra></extra>")
                fig2.add_trace(go.Scatter(
                    x=x_vals,
                    y=last_24["peak_ccu"],
                    mode="lines", name=r["name"],
                    hovertemplate=hover,
                    line=dict(width=2),
                ))

        # If 5 or fewer games shown, add visible annotations; otherwise events are hover-only
        if len(hist_titles) <= 5:
            _seen_dates: set[str] = set()
            for r in hist_titles:
                x_vals = _all_x_sets.get(r["app_id"], [])
                for ev_date, ev_label in get_game_events(r["app_id"]):
                    ev_match = next((x for x in x_vals if x.startswith(ev_date[:7])), None)
                    if ev_match and ev_match not in _seen_dates:
                        _seen_dates.add(ev_match)
                        fig2.add_vline(
                            x=ev_match,
                            line_width=1, line_dash="dash",
                            line_color="rgba(255,200,50,0.4)",
                        )
                        fig2.add_annotation(
                            x=ev_match, y=1.0, yref="paper",
                            text=f"{r['name'][:10]}: {ev_label}",
                            showarrow=False,
                            font=dict(size=8, color="#ffc832"),
                            textangle=-60, xanchor="left", yanchor="bottom",
                            bgcolor="rgba(5,8,24,0.7)",
                        )
            _note = T("history_note_few")
        else:
            _note = T("history_note_many")

        fig2.update_layout(
            **{**PLOTLY_BASE, "margin": dict(l=10, r=10, t=80, b=40)},
            title=dict(text=T("chart_history_title"), font=dict(size=13, color="#b8bcd4"), x=0),
            xaxis=dict(showgrid=False, tickangle=-45, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#1a1e30", tickformat=","),
            height=420,
            legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(T("history_caption", note=_note))

if st.button(T("refresh_ccu_btn"), key="refresh_ccu"):
    st.cache_data.clear()
    st.session_state.ccu_data = []
    st.rerun()


render_footer()
