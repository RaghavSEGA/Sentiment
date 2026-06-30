"""
pages/4_Admin.py — Configuration status, cache controls, CSV uploads,
and a viewer for the background scheduler's log file.
"""

import streamlit as st

from common import *  # noqa: F401,F403
from common import _archive_dir, _cache_path  # leading underscore — import * skips these

st.set_page_config(
    page_title="SEGA Shooter Intel — Admin",
    page_icon=":material/settings:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_defaults()
require_auth()
render_topbar()
render_nav_tabs("admin")

st.markdown(f"""
<div class="hero" style="padding-top:0.75rem">
  <div class="hero-title" style="font-size:1.8rem">{T("admin_header")}</div>
</div>
""", unsafe_allow_html=True)

st.markdown(f'<div class="admin-note" style="font-size:.78rem;color:var(--muted);margin-bottom:1rem;">{T("admin_csv_note")}</div>', unsafe_allow_html=True)

st.markdown(f"""
<div class="section-header" style="margin-top:0">
  <span class="dot"></span>{T("sidebar_config")}
</div>
""", unsafe_allow_html=True)

# Active roster reflects whatever genre/filter was last set on the Dashboard
# page this session; falls back to FPS if Dashboard hasn't been visited yet.
SHOOTER_ROSTER = st.session_state.get("_active_roster", get_roster("FPS"))

st.markdown("---")

_bedrock_ok = bool(st.secrets.get("AWS_ACCESS_KEY_ID_API"))
if _bedrock_ok:
    st.success(T("bedrock_ok"), icon="🔑")
else:
    st.error(T("bedrock_missing"))
    st.markdown(
        "Add to <code>.streamlit/secrets.toml</code>:<br>"
        "<pre>AWS_ACCESS_KEY_ID_API = ...\nAWS_SECRET_ACCESS_KEY_API = ...\nAWS_BEDROCK_REGION = us-east-1</pre>",
        unsafe_allow_html=True,
    )

st.markdown("---")
_age = cache_age_str()
if _age:
    st.caption(T("cache_age", age=_age))
    st.caption(T("cache_refetch"))
else:
    st.caption(T("cache_none"))
if st.button(T("refresh_now"), key="force_refresh_btn", use_container_width=True,
             help=T("refresh_now_help")):
    st.session_state.force_refresh = True
    st.session_state.ccu_data      = []
    st.session_state.ai_report     = ""
    st.session_state.report_cache  = {}
    try:
        _cache_path().unlink(missing_ok=True)
    except Exception:
        pass
    st.rerun()
st.markdown("---")
st.caption(T("model_caption"))
st.caption(T("ccu_caption"))
st.caption(T("engagement_caption"))
st.markdown("---")
# Twitch credentials status
_twitch_ok = bool(st.secrets.get("TWITCH_CLIENT_ID"))
if _twitch_ok:
    st.success("✓ Twitch API connected", icon="📺")
else:
    st.caption("📺 Twitch viewers: add `TWITCH_CLIENT_ID` + `TWITCH_CLIENT_SECRET` to secrets to enable")
st.markdown("---")
# Show which games have historical CSV data loaded
_sb_roster_ids = frozenset(g["app_id"] for g in SHOOTER_ROSTER)
historical = load_all_historical(_sb_roster_ids)
hist_ids = set(historical.keys())
roster_ids = {g["app_id"] for g in SHOOTER_ROSTER}
loaded = hist_ids & roster_ids
missing = roster_ids - hist_ids
st.caption(T("csvs_loaded", n=len(loaded), total=len(roster_ids)))
if missing:
    missing_names = [g["name"] for g in SHOOTER_ROSTER if g["app_id"] in missing]
    st.caption(T("csv_missing", names=", ".join(missing_names)))
st.caption(T("csv_drop_hint", appid="{appid}"))
st.markdown("---")
st.markdown(T("upload_header"), unsafe_allow_html=False)
st.caption(T("upload_caption", appid="{appid}"))
_uploaded = st.file_uploader(
    "SteamDB CSVs",
    type="csv",
    accept_multiple_files=True,
    label_visibility="collapsed",
    key="csv_uploader",
)
if _uploaded:
    _changed = False
    for _f in _uploaded:
        _m = __import__("re").search(r"(\d+)", _f.name)
        if _m:
            _aid = int(_m.group(1))
            _bytes = _f.read()
            if st.session_state.uploaded_csvs.get(_aid) != _bytes:
                st.session_state.uploaded_csvs[_aid] = _bytes
                _changed = True
    if _changed:
        st.cache_data.clear()
        st.session_state.ccu_data = []
        st.rerun()
if st.session_state.uploaded_csvs:
    _names = [g["name"] for g in SHOOTER_ROSTER
              if g["app_id"] in st.session_state.uploaded_csvs]
    st.success(T("upload_loaded", n=len(st.session_state.uploaded_csvs),
                 names=", ".join(_names)))


st.markdown("---")

# ─────────────────────────────────────────────────────────────
# BACKGROUND SCHEDULER LOG
# ─────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="section-header">
  <span class="dot"></span>{T("admin_scheduler_header")}
</div>
""", unsafe_allow_html=True)
st.caption(T("admin_scheduler_desc"))

_log_path = _archive_dir() / "scheduler.log"
if _log_path.exists():
    try:
        _log_lines = _log_path.read_text(encoding="utf-8").splitlines()
        _recent = _log_lines[-20:]
        st.markdown(f"**{T('admin_log_header')}**")
        st.code("\n".join(_recent) or "(empty)", language=None)
        if st.button(T("admin_log_clear"), key="clear_scheduler_log"):
            try:
                _log_path.unlink()
                st.rerun()
            except Exception as _e:
                st.error(f"Could not clear log: {_e}")
    except Exception as _e:
        st.error(f"Could not read scheduler log: {_e}")
else:
    st.info(T("admin_log_none"))

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# CONNECTIVITY CHECK
# ─────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="section-header">
  <span class="dot"></span>{T("conn_check_header")}
</div>
""", unsafe_allow_html=True)
st.caption(T("conn_check_desc"))

if st.button(T("conn_check_btn"), key="run_connectivity_check"):
    with st.spinner(T("conn_check_running")):
        _probe_results = run_connectivity_probe()
    for _pr in _probe_results:
        if _pr["ok"] is None:
            st.caption(f"⚪ **{_pr['api']}** — {_pr['detail']}")
        elif _pr["ok"]:
            st.success(f"**{_pr['api']}** — {_pr['detail']}", icon="✅")
        else:
            st.error(f"**{_pr['api']}** — {_pr['detail']}", icon="❌")

render_footer()
