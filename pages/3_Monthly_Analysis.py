"""
pages/3_Monthly_Analysis.py — Compare archived weekly reports month-over-month.

Reads from the JSON report archive (auto-populated every Monday by the
background scheduler, or manually via the Archive button on the Weekly
Report page). Does not require a live CCU fetch in the current session.
"""

import streamlit as st
from datetime import datetime

from common import *  # noqa: F401,F403

st.set_page_config(
    page_title="SEGA Shooter Intel — Monthly Analysis",
    page_icon=":material/calendar_month:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_defaults()
require_auth()
enforce_common_module_integrity()
render_topbar()
render_nav_tabs("monthly")

# ─────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="section-header">
  <span class="dot"></span>{T("monthly_header")}
</div>
""", unsafe_allow_html=True)

# ─── AUTO-ARCHIVE ────────────────────────────────────────────
# Archive the current session's data the first time this page is
# visited, so the user never has to click a button manually.
#
# Guards that prevent this from doing the wrong thing:
#   1. Only archives if CCU data was fetched this session and is
#      non-empty (no data = nothing to archive).
#   2. Skips when the fetch health looks systemic (all-zero CCU
#      means the live API failed — bad data shouldn't be archived).
#   3. Only archives once per session per genre (session_state flag)
#      so Streamlit reruns don't create duplicate entries.
#   4. Only archives when an AI report exists in session_state —
#      the snapshot alone (without a report) isn't useful in the
#      Monthly view.
# ─────────────────────────────────────────────────────────────

_ccu_data_now  = st.session_state.get("ccu_data", [])
_report_now    = st.session_state.get("ai_report", "")
_label_now     = st.session_state.get("report_label", "Weekly Report")
_genre_now     = st.session_state.get("roster_genre", "FPS")
_fh            = summarize_fetch_health(_ccu_data_now) if _ccu_data_now else {"looks_systemic": True}
_archive_flag  = f"_auto_archived_{_genre_now}"

if (_ccu_data_now and _report_now and not _fh["looks_systemic"]
        and not st.session_state.get(_archive_flag)):
    _saved = save_report_to_archive(_report_now, _label_now, _genre_now, _ccu_data_now)
    if _saved:
        st.session_state[_archive_flag] = True
        st.toast(T("auto_archive_success"), icon="📦")
    else:
        st.caption(T("auto_archive_failed"))
elif _ccu_data_now and _fh["looks_systemic"]:
    st.caption(T("auto_archive_skipped"))

_all_archives = list_archived_reports()

if not _all_archives:
    st.info(T("monthly_none"))
else:
    # Build month selector — group archives by YYYY-MM
    from collections import defaultdict as _dd
    _by_month: dict[str, list[dict]] = _dd(list)
    for _ar in _all_archives:
        _month_key = _ar["date"][:7]   # "2026-03"
        _by_month[_month_key].append(_ar)
    _month_keys = sorted(_by_month.keys(), reverse=True)

    st.caption(T("monthly_count", n=len(_all_archives), m=len(_month_keys)))

    with st.expander(T("monthly_expander"), expanded=True):
        _sel_month = st.selectbox(
            T("monthly_select"),
            options=_month_keys,
            format_func=lambda m: datetime.strptime(m, "%Y-%m").strftime("%B %Y"),
            key="monthly_sel_month",
        )

        _month_reports = _by_month[_sel_month]
        st.markdown(T("monthly_reports_for", n=len(_month_reports),
                      month=datetime.strptime(_sel_month, '%Y-%m').strftime('%B %Y')))

        # Show report cards
        _report_cols = st.columns(min(len(_month_reports), 4))
        for _ci, _rep in enumerate(_month_reports):
            with _report_cols[_ci % 4]:
                _genre_badge = _rep.get("genre", "?")
                _n_titles = len(_rep.get("ccu_snapshot", []))
                st.markdown(f"""<div class="metric-card blue-top" style="padding:.8rem 1rem;">
                <div class="metric-label">{_rep['date']}</div>
                <div style="font-size:.85rem;font-weight:600;color:var(--text)">{_genre_badge}</div>
                <div class="metric-sub">{T("monthly_titles", n=_n_titles)}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # CCU drift table — compare first vs last report of the month
        if len(_month_reports) >= 2:
            _sorted_month = sorted(_month_reports, key=lambda x: x["date"])
            _first = _sorted_month[0]
            _last  = _sorted_month[-1]

            _first_snap = {r["app_id"]: r["ccu"] for r in _first.get("ccu_snapshot", [])}
            _last_snap  = {r["app_id"]: r["ccu"] for r in _last.get("ccu_snapshot",  [])}
            _names       = {r["app_id"]: r["name"] for r in _last.get("ccu_snapshot", [])}

            # Build lookup for WoW from last snapshot
            _last_wow  = {r["app_id"]: r.get("wow", "N/A") for r in _last.get("ccu_snapshot", [])}

            _C_DRIFT = T("col_monthly_drift")
            _C_LWOW  = T("col_latest_wow")
            _C_TTL   = T("col_title")
            _drift_rows = []
            for _aid, _ccu_end in _last_snap.items():
                _ccu_start = _first_snap.get(_aid)
                if _ccu_start and _ccu_start > 0:
                    _drift_pct = round((_ccu_end - _ccu_start) / _ccu_start * 100)
                    _sign = "+" if _drift_pct >= 0 else ""
                    _drift_rows.append({
                        _C_TTL:                  _names.get(_aid, str(_aid)),
                        f"CCU {_first['date']}": f"{_ccu_start:,}",
                        f"CCU {_last['date']}":  f"{_ccu_end:,}",
                        _C_DRIFT:                f"{_sign}{_drift_pct}%",
                        _C_LWOW:                 _last_wow.get(_aid, "N/A"),
                    })
            _drift_rows.sort(key=lambda x: int(x[_C_DRIFT].replace("%","").replace("+","")), reverse=True)

            st.markdown(T("monthly_drift", a=_first['date'], b=_last['date']))
            render_table(_drift_rows, [_C_TTL, f"CCU {_first['date']}", f"CCU {_last['date']}", _C_DRIFT, _C_LWOW])
        elif len(_month_reports) == 1:
            st.info(T("monthly_one"))

        st.markdown("---")

        # AI monthly comparison
        st.markdown(T("monthly_ai_header"))
        st.caption(T("monthly_ai_caption"))

        if not st.secrets.get("AWS_ACCESS_KEY_ID_API"):
            st.warning(T("monthly_no_key"))
        else:
            if st.button(T("monthly_run_btn"), key="run_monthly_btn"):
                _month_prompts = []
                for _rep in sorted(_month_reports, key=lambda x: x["date"]):
                    _snap_lines = "  ".join(
                        f"{r['name']}: {r['ccu']:,} CCU | WoW {r.get('wow','N/A')} | MoM {r.get('mom','—')} | YoY {r.get('yoy','N/A')}"
                        for r in _rep.get("ccu_snapshot", [])
                    )
                    _excerpt = _rep.get('report_md','')[:1500]
                    _rep_genre = _rep.get('genre','?')
                    _week_date = _rep['date']
                    _month_prompts.append(
                        f"=== WEEK OF {_week_date} ({_rep_genre}) ===\n"
                        f"{_snap_lines}\n\nREPORT EXCERPT:\n{_excerpt}"
                    )

                _monthly_lang_note = (
                    "\n\nIMPORTANT: Write the entire report in Japanese (日本語), using "
                    "professional business Japanese. Do not switch to English at any point."
                    if st.session_state.report_language == "Japanese" else ""
                )
                _monthly_prompt = f"""You are reviewing {len(_month_reports)} weekly shooter market intelligence reports from {_sel_month}.

{chr(10).join(_month_prompts)}

Produce a MONTHLY ACCURACY & TREND REPORT covering:
1. TREND CONSISTENCY — do the weekly CCU numbers tell a coherent story across the month? Flag any titles where the reported trend reversed unexpectedly.
2. NOTABLE MOVES — which titles showed the largest sustained gains or losses across the full month?
3. ACCURACY CHECK — compare the narrative in each week's report against the raw CCU numbers. Flag any cases where the commentary overstated or understated a move.
4. MONTH SUMMARY — one paragraph summarising the overall market direction for {datetime.strptime(_sel_month, "%Y-%m").strftime("%B %Y")}.

Be specific and data-driven. Use the CCU numbers directly.{_monthly_lang_note}"""

                try:
                    import anthropic as _anth_m
                    _mc = _anth_m.AnthropicBedrock(
                    aws_access_key=st.secrets.get("AWS_ACCESS_KEY_ID_API", ""),
                    aws_secret_key=st.secrets.get("AWS_SECRET_ACCESS_KEY_API", ""),
                    aws_region=st.secrets.get("AWS_BEDROCK_REGION", "us-east-1"),
                )
                    with st.spinner(T("monthly_spinner")):
                        _mr = _mc.messages.create(
                            model="us.anthropic.claude-sonnet-4-6",
                            max_tokens=3000,
                            messages=[{"role": "user", "content": _monthly_prompt}],
                        )
                    _monthly_report = _mr.content[0].text
                    st.session_state[f"monthly_report_{_sel_month}"] = _monthly_report
                except Exception as _me:
                    st.error(T("monthly_failed", e=_me))

            if st.session_state.get(f"monthly_report_{_sel_month}"):
                st.markdown("---")
                st.markdown(st.session_state[f"monthly_report_{_sel_month}"])
                # Download
                _mfn = f"sega_monthly_{_sel_month}.md"
                st.download_button(T("monthly_dl"),
                    data=st.session_state[f"monthly_report_{_sel_month}"],
                    file_name=_mfn, mime="text/markdown",
                    key="dl_monthly_md")



render_footer()
