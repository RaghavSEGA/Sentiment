"""
pages/2_Deep_Dive.py — Per-game intelligence deep dive.

Requires st.session_state.ccu_data to be populated — visit the Dashboard
page first if this page shows the "no data" message below.
"""

import streamlit as st
import plotly.graph_objects as go

from common import *  # noqa: F401,F403

st.set_page_config(
    page_title="SEGA Shooter Intel — Deep Dive",
    page_icon=":material/search:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_defaults()
require_auth()
render_topbar()

# ─────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="section-header">
  <span class="dot"></span>{T("drilldown_header")}
</div>
""", unsafe_allow_html=True)

if not st.session_state.ccu_data:
    st.info(T("drilldown_no_data"))
    st.page_link("shooter_intel.py", label="Go to Dashboard to fetch live CCU data", icon="📊")
else:
    _dd_names  = [g["name"] for g in st.session_state.ccu_data]
    _dd_ids    = [g["app_id"] for g in st.session_state.ccu_data]
    _dd_prev   = st.session_state.drilldown_game

    _dd_default_idx = _dd_ids.index(_dd_prev) if _dd_prev in _dd_ids else 0
    _dd_col1, _dd_col2 = st.columns([4, 1])
    with _dd_col1:
        _dd_selected_name = st.selectbox(
            T("drilldown_select"),
            options=_dd_names,
            index=_dd_default_idx,
            key="drilldown_selectbox",
            label_visibility="collapsed",
        )
    with _dd_col2:
        _dd_btn = st.button(T("drilldown_btn"), key="drilldown_run", use_container_width=True)

    _dd_selected_id = _dd_ids[_dd_names.index(_dd_selected_name)]

    # If game changed, clear cached report (but keep chart visible)
    if _dd_selected_id != st.session_state.drilldown_game:
        st.session_state.drilldown_game   = _dd_selected_id
        st.session_state.drilldown_report = st.session_state.drilldown_cache.get(_dd_selected_id, "")

    #  Per-game CCU history chart (always shown when a game is selected)
    _dd_hist_all = load_all_historical(frozenset({_dd_selected_id}))
    _dd_mdf = _dd_hist_all.get(_dd_selected_id)
    _dd_game_data = next((g for g in st.session_state.ccu_data if g["app_id"] == _dd_selected_id), None)

    if _dd_mdf is not None and not _dd_mdf.empty:
        _dd_plot_df = _dd_mdf.sort_values("month")
        _dd_events  = get_game_events(_dd_selected_id)

        fig_dd = go.Figure()

        # Area fill + line
        fig_dd.add_trace(go.Scatter(
            x=[str(p) for p in _dd_plot_df["month"]],
            y=_dd_plot_df["peak_ccu"],
            mode="lines",
            name=T("trace_peak"),
            line=dict(color="#0057FF", width=2.5),
            fill="tozeroy",
            fillcolor="rgba(0,87,255,0.10)",
            hovertemplate="<b>%{x}</b><br>Peak CCU: %{y:,}<extra></extra>",
        ))

        # Avg CCU line
        if "avg_ccu" in _dd_plot_df.columns:
            fig_dd.add_trace(go.Scatter(
                x=[str(p) for p in _dd_plot_df["month"]],
                y=_dd_plot_df["avg_ccu"],
                mode="lines",
                name=T("trace_avg"),
                line=dict(color="#5588ff", width=1.5, dash="dot"),
                hovertemplate="<b>%{x}</b><br>Avg CCU: %{y:,}<extra></extra>",
            ))

        # Annotated vertical lines for notable events
        x_vals = [str(p) for p in _dd_plot_df["month"]]
        for ev_date, ev_label in _dd_events:
            # Find nearest month in data
            ev_match = next((x for x in x_vals if x.startswith(ev_date[:7])), None)
            if ev_match:
                fig_dd.add_vline(
                    x=ev_match,
                    line_width=1,
                    line_dash="dash",
                    line_color="rgba(255,200,50,0.5)",
                )
                fig_dd.add_annotation(
                    x=ev_match,
                    y=1.0,
                    yref="paper",
                    text=ev_label,
                    showarrow=False,
                    font=dict(size=9, color="#ffc832"),
                    textangle=-60,
                    xanchor="left",
                    yanchor="bottom",
                    bgcolor="rgba(5,8,24,0.7)",
                )

        # Live CCU dot
        if _dd_game_data and _dd_game_data.get("ccu"):
            fig_dd.add_trace(go.Scatter(
                x=["Live"],
                y=[_dd_game_data["ccu"]],
                mode="markers",
                name=T("trace_live"),
                marker=dict(color="#00ff99", size=10, symbol="circle"),
                hovertemplate=f"<b>Live now</b><br>CCU: {_dd_game_data['ccu']:,}<extra></extra>",
            ))

        fig_dd.update_layout(
            **{**PLOTLY_BASE, "margin": dict(l=10, r=10, t=60, b=40)},
            title=dict(
                text=T("chart_drilldown_title", name=_dd_selected_name),
                font=dict(size=13, color="#b8bcd4"), x=0,
            ),
            xaxis=dict(showgrid=False, tickangle=-45, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#1a1e30", tickformat=","),
            height=360,
            legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_dd, use_container_width=True)

        # Quick stat pills beneath the chart
        _hs = _dd_game_data.get("hist_summary", {}) if _dd_game_data else {}
        _pill_cols = st.columns(4)
        _pills = [
            (T("pill_peak_ever"), f"{_hs.get('peak_ever', '—'):,}" if isinstance(_hs.get('peak_ever'), int) else "—"),
            (T("pill_peak_12m"),  f"{_hs.get('peak_12m', '—'):,}" if isinstance(_hs.get('peak_12m'),  int) else "—"),
            (T("pill_avg_12m"),   f"{_hs.get('avg_12m', '—'):,}" if isinstance(_hs.get('avg_12m'),   int) else "—"),
            (T("pill_mom"),       _hs.get('mom_trend', '—')),
        ]
        for col, (label, val) in zip(_pill_cols, _pills):
            col.metric(label, val)
    else:
        st.info(T("drilldown_no_csv", name=_dd_selected_name, appid=_dd_selected_id))

    #  AI deep-dive report
    if _dd_btn or st.session_state.drilldown_report:
        if _dd_btn and not st.session_state.drilldown_cache.get(_dd_selected_id):
            if not st.secrets.get("AWS_ACCESS_KEY_ID_API"):
                st.warning(T("drilldown_no_key"))
            else:
                if _dd_game_data:
                    with st.spinner(T("drilldown_spinner")):
                        try:
                            import anthropic as _ant
                            _dd_prompt = build_drilldown_prompt(
                                _dd_game_data, _dd_hist_all, st.session_state.report_language
                            )
                            _dd_client = _ant.AnthropicBedrock(
                            aws_access_key=st.secrets.get("AWS_ACCESS_KEY_ID_API", ""),
                            aws_secret_key=st.secrets.get("AWS_SECRET_ACCESS_KEY_API", ""),
                            aws_region=st.secrets.get("AWS_BEDROCK_REGION", "us-east-1"),
                        )
                            # 3000 tokens — JP deep dives were also at risk of truncation
                            _dd_resp = _dd_client.messages.create(
                                model="us.anthropic.claude-sonnet-4-6",
                                max_tokens=3000,
                                system=build_system_prompt(st.session_state.report_language),
                                messages=[{"role": "user", "content": _dd_prompt}],
                            )
                            _dd_text = _dd_resp.content[0].text
                            st.session_state.drilldown_report = _dd_text
                            st.session_state.drilldown_cache[_dd_selected_id] = _dd_text
                        except Exception as _dd_err:
                            st.error(T("drilldown_failed", e=_dd_err))

        if st.session_state.drilldown_report:
            st.markdown(st.session_state.drilldown_report)
            _dd_fname = _dd_selected_name.lower().replace(" ", "_").replace(":", "")
            st.download_button(
                T("drilldown_dl"),
                data=st.session_state.drilldown_report,
                file_name=f"deepdive_{_dd_fname}.md",
                mime="text/markdown",
                key="drilldown_download",
            )


render_footer()
