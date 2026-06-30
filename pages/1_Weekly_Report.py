"""
pages/1_Weekly_Report.py — AI Analysis, downloads, follow-up chat.

Requires st.session_state.ccu_data to be populated — visit the Dashboard
page first if this page shows the "no data" message below.
"""

import re
import streamlit as st

from common import *  # noqa: F401,F403
from common import _REPORTLAB_AVAILABLE, _anthropic  # leading underscore — import * skips these

st.set_page_config(
    page_title="SEGA Shooter Intel — Weekly Report",
    page_icon=":material/description:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_defaults()
require_auth()
render_topbar()

st.markdown(f"""
<div class="section-header" style="margin-top:1.5rem">
  <span class="dot"></span>{T("select_analysis")}
</div>
""", unsafe_allow_html=True)

if not st.session_state.ccu_data:
    st.info(T("drilldown_no_data"))
    safe_page_link(HOME_PAGE, label="Go to Dashboard to fetch live CCU data", icon="📊")
    st.stop()

ccu_data = st.session_state.ccu_data

# Recompute wow_diff fresh on this page — cheap (CSV math, no network) and
# avoids relying on session_state having been populated by a prior Dashboard
# render earlier in the same session.
_wr_raw_data = load_all_raw(frozenset(r["app_id"] for r in ccu_data))
_wr_live_map = {r["app_id"]: r["ccu"] for r in ccu_data}
st.session_state["_wow_diff_cache"] = compute_period_diff(_wr_raw_data, _wr_live_map, days=7)

# ─────────────────────────────────────────────────────────────
# ANALYSIS PRESETS  — insight cards, one per PRESET_QUERIES entry.
# Clicking a card sets active_query and clears any cached report so the
# AI ANALYSIS block below regenerates immediately.
# ─────────────────────────────────────────────────────────────

_preset_cols = st.columns(len(PRESET_QUERIES))
for _pc, _preset in zip(_preset_cols, PRESET_QUERIES):
    with _pc:
        _label = T("preset_labels").get(_preset["id"], _preset["label"])
        _desc  = T("preset_descs").get(_preset["id"], _preset["desc"])
        _tag   = T("preset_tags").get(_preset["id"], _preset["tag"])
        _active = st.session_state.active_query == _preset["id"]
        st.markdown(f"""
        <div class="insight-card" style="{'border-left-color:#7ab0ff;' if _active else ''}">
          <span class="{_preset['tag_class']}">{_tag}</span>
          <div class="insight-card-title" style="margin-top:.5rem">{_label}</div>
          <div class="insight-card-desc">{_desc}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(T("run_analysis"), key=f"preset_btn_{_preset['id']}",
                     use_container_width=True,
                     type="primary" if _active else "secondary"):
            st.session_state.active_query     = _preset["id"]
            st.session_state.ai_report        = ""
            st.session_state.ai_chat_history  = []
            st.session_state.report_label     = _label
            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f'<div class="field-label">{T("custom_label")}</div>', unsafe_allow_html=True)
_col_q, _col_btn = st.columns([5, 1])
with _col_q:
    _custom = st.text_input(
        "Custom query",
        value=st.session_state.custom_query,
        label_visibility="collapsed",
        placeholder=T("custom_placeholder"),
        key="custom_input",
    )
with _col_btn:
    _run_custom = st.button(T("run_btn"), key="run_custom")

if _run_custom and _custom.strip():
    st.session_state.custom_query     = _custom.strip()
    st.session_state.active_query     = "custom"
    st.session_state.ai_report        = ""
    st.session_state.ai_chat_history  = []
    st.session_state.report_label     = T("custom_query_label")
    st.rerun()

st.markdown("---")

# AI ANALYSIS — generation, downloads, follow-up chat
if st.session_state.active_query:
    _genre_lbl = st.session_state.get("roster_genre", "FPS")
    if _genre_lbl == "BOTH": _genre_lbl = "FPS"
    st.markdown(f"""
<div class="section-header">
  <span class="dot"></span>{T("ai_analysis_header", label=st.session_state.report_label.upper())}
</div>
""", unsafe_allow_html=True)
    if not st.secrets.get("AWS_ACCESS_KEY_ID_API"):
        st.warning(T("no_key_warning"))
    elif not ANTHROPIC_AVAILABLE:
        st.error(T("no_anthropic_error"))
    elif not st.session_state.ai_report:
        _ck = f"{st.session_state.active_query}_{st.session_state.report_language}_{hash(str([r['ccu'] for r in ccu_data]))}"
        if _ck in st.session_state.report_cache:
            st.session_state.ai_report = st.session_state.report_cache[_ck]
            st.info(T("cache_notice"))
        else:
            with st.spinner(T("spinner_generating")):
                try:
                    import anthropic as _ant2
                    _aq2 = st.session_state.active_query
                    if _aq2 == "weekly_report":
                        _up2 = build_weekly_report_prompt(
                            ccu_data[:25], st.session_state.report_language)
                        _max_tok = 6000   # Section 1 + 2 (full table) + Section 3
                    elif _aq2 == "ccu_mecha":
                        _up2 = build_ccu_mecha_prompt(ccu_data[:10], genre=_genre_lbl)
                        _max_tok = 4000
                    elif _aq2 == "competitive_gap":
                        _up2 = build_competitive_gap_prompt(
                            ccu_data[:5], st.session_state.report_language)
                        _max_tok = 4000
                    elif _aq2 == "table_stakes":
                        _up2 = build_table_stakes_prompt()
                        _max_tok = 4000
                    elif _aq2 == "social_metrics":
                        _up2 = build_social_metrics_prompt()
                        _max_tok = 4000
                    # table_stakes / social_metrics take no ccu_data or language
                    # arg (they're general market-knowledge prompts, not CCU-driven)
                    # — the system prompt below still carries the JP instruction,
                    # but reinforce it inline since these builders predate that.
                    if _aq2 in ("table_stakes", "social_metrics") and st.session_state.report_language == "Japanese":
                        _up2 += "\n\nIMPORTANT: Write the entire response in Japanese (日本語) using professional business Japanese. Do not switch to English at any point."
                    else:
                        _up2 = st.session_state.custom_query or build_weekly_report_prompt(
                            ccu_data[:25], st.session_state.report_language)
                        _max_tok = 4000
                    _cl2 = _ant2.AnthropicBedrock(
                        aws_access_key=st.secrets.get("AWS_ACCESS_KEY_ID_API", ""),
                        aws_secret_key=st.secrets.get("AWS_SECRET_ACCESS_KEY_API", ""),
                        aws_region=st.secrets.get("AWS_BEDROCK_REGION", "us-east-1"),
                    )
                    _r2  = _cl2.messages.create(
                        model="us.anthropic.claude-sonnet-4-6",
                        max_tokens=_max_tok,
                        system=build_system_prompt(st.session_state.report_language),
                        messages=[{"role": "user", "content": _up2}],
                    )
                    st.session_state.ai_report = _r2.content[0].text
                    st.session_state.report_cache[_ck] = st.session_state.ai_report
                    save_daily_cache(
                        st.session_state.get("roster_genre", "FPS"),
                        [r["app_id"] for r in ccu_data],
                        ccu_data,
                        st.session_state.ai_report,
                        st.session_state.get("report_label", ""),
                    )
                    _ag = st.session_state.get("roster_genre", "FPS")
                    if should_auto_archive(_ag):
                        _af = save_report_to_archive(
                            st.session_state.ai_report,
                            st.session_state.report_label,
                            _ag, ccu_data)
                        if _af:
                            st.toast(T("auto_archived", f=_af), icon="✅")
                except Exception as _e2:
                    st.error(T("analysis_failed", e=_e2))
    if st.session_state.ai_report:
        render_report_with_tables(st.session_state.ai_report)
        st.markdown("<br>", unsafe_allow_html=True)
        _fn2 = re.sub(r"[^a-z0-9]+", "_", st.session_state.report_label.lower())[:40]
        fname2 = f"sega_shooter_intel_{_fn2}"
        _da1, _da2, _da3, _da4, _da5, _da6 = st.columns(6)
        with _da1:
            st.download_button(T("dl_md"), data=st.session_state.ai_report,
                file_name=f"{fname2}.md", mime="text/markdown",
                use_container_width=True, key="dl_md_top")
        with _da2:
            _html2 = report_to_html(st.session_state.ai_report).encode("utf-8")
            st.download_button(T("dl_html"), data=_html2,
                file_name=f"{fname2}.html", mime="text/html",
                use_container_width=True, key="dl_html_top")
        with _da3:
            if _REPORTLAB_AVAILABLE:
                _pdf2 = report_to_pdf(st.session_state.ai_report)
                if _pdf2:
                    st.download_button(T("dl_pdf"), data=_pdf2,
                        file_name=f"{fname2}.pdf", mime="application/pdf",
                        use_container_width=True, key="dl_pdf_top")
            else:
                st.caption(T("dl_pdf_missing"))
        with _da4:
            if st.button(T("dl_pptx_btn"), key="dl_pptx_top", use_container_width=True):
                with st.spinner(T("spinner_pptx")):
                    # NEW: snapshot-of-the-page export (Playwright). Falls
                    # back to the original text-based deck automatically.
                    _pptx2 = None
                    _used_fallback = False
                    try:
                        _pptx2 = generate_pptx_snapshot_bytes(
                            st.session_state.ai_report,
                            st.session_state.ccu_data or [],
                            st.session_state.report_label,
                            st.session_state.get("_wow_diff_cache", {}),
                            st.session_state.report_language,
                        )
                    except Exception:
                        _pptx2 = None
                    if not _pptx2:
                        _used_fallback = True
                        _pptx2 = generate_pptx_bytes(
                            st.session_state.ai_report,
                            st.session_state.ccu_data or [],
                            st.session_state.report_label,
                        )
                if _pptx2:
                    if _used_fallback:
                        st.caption(T("pptx_fallback_note"))
                    st.download_button(T("dl_pptx_file"), data=_pptx2,
                        file_name=f"{fname2}.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        key="dl_pptx_actual_top")
                else:
                    st.error(T("dl_pptx_error"))
        with _da5:
            if st.button(T("regen_btn"), key="regen_top", use_container_width=True):
                st.session_state.ai_report = ""
                st.session_state.report_cache = {}
                st.rerun()
        with _da6:
            if st.button(T("archive_btn"), key="archive_btn", use_container_width=True):
                _ag2 = st.session_state.get("roster_genre", "FPS")
                _af2 = save_report_to_archive(
                    st.session_state.ai_report,
                    st.session_state.report_label,
                    _ag2, ccu_data)
                st.toast(T("archive_saved", f=_af2) if _af2 else T("archive_failed"),
                         icon="✅" if _af2 else "⚠️")

        # Follow-up chat
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-header"><span class="dot"></span>{T("chat_header")}'
            f'<span style="color:var(--muted);font-size:.7rem;font-weight:400;"> '
            f'{T("chat_subtext")}</span></div>',
            unsafe_allow_html=True,
        )

        def build_chat_system_top():
            # Full CCU snapshot — all titles, not just top 15
            ccu_ctx = ""
            if st.session_state.ccu_data:
                ccu_ctx = "\n\n## Live CCU Snapshot (all tracked titles)\n" + "\n".join(
                    f"- {r['name']} ({r['sub']}): {r['ccu']:,} CCU | "
                    f"YoY {r.get('yoy','N/A')} | MoM {(r.get('hist_summary') or {}).get('mom_trend','—')} | "
                    f"Review {r.get('review_pct','?')}%"
                    for r in st.session_state.ccu_data
                )
            _chat_lang = (
                " Respond in Japanese (日本語) using professional business Japanese."
                if st.session_state.report_language == "Japanese" else ""
            )
            # Full report — no truncation. The system prompt sits outside the
            # conversation turns so it doesn't inflate the user/assistant history.
            return (
                "You are a senior games market analyst at SEGA. "
                "Answer follow-up questions concisely, accurately, and commercially. "
                "Reference the report and live data below where relevant. "
                "Use markdown for formatting." + _chat_lang + "\n\n"
                f"## Weekly Intelligence Report\n\n{st.session_state.ai_report}"
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
                _cc = _anthropic.AnthropicBedrock(
                aws_access_key=st.secrets.get("AWS_ACCESS_KEY_ID_API", ""),
                aws_secret_key=st.secrets.get("AWS_SECRET_ACCESS_KEY_API", ""),
                aws_region=st.secrets.get("AWS_BEDROCK_REGION", "us-east-1"),
            )
                with st.chat_message("assistant"):
                    _reply = ""
                    _ph_chat = st.empty()
                    with _cc.messages.stream(
                        model="us.anthropic.claude-sonnet-4-6",
                        max_tokens=2048,
                        system=build_chat_system_top(),
                        messages=api_msgs,
                    ) as _stream:
                        for _delta in _stream.text_stream:
                            _reply += _delta
                            _ph_chat.markdown(_reply + "▌")
                    _ph_chat.markdown(_reply)
                st.session_state.ai_chat_history.append({"role": "assistant", "content": _reply})
            except Exception as _ce:
                st.error(T("chat_error", e=f"{type(_ce).__name__}: {_ce}"))

        if st.session_state.ai_chat_history:
            if st.button(T("chat_clear"), key="clear_chat_top"):
                st.session_state.ai_chat_history = []
                st.session_state.ai_chat_pending = False
                st.rerun()

    st.markdown("---")

# ─────────────────────────────────────────────────────────────

if st.session_state.get("ai_report") and st.secrets.get("AWS_ACCESS_KEY_ID_API"):
    _user_msg = st.chat_input(T("chat_placeholder"), key="ai_chat_input_top")
    if _user_msg:
        st.session_state.ai_chat_history.append({"role": "user", "content": _user_msg})
        st.session_state.ai_chat_pending = True
        st.rerun()


render_footer()
