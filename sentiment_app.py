"""
Sentiment Analysis Studio
=========================
Run with:  streamlit run sentiment_app.py

Required secrets (.streamlit/secrets.toml):
    ANTHROPIC_API_KEY      = "sk-ant-..."
    COOKIE_SIGNING_KEY     = "change-me-to-a-random-string"
    ALLOWED_DOMAIN         = "@yourdomain.com"
    AWS_SES_REGION         = "us-east-1"
    AWS_ACCESS_KEY_ID      = "..."
    AWS_SECRET_ACCESS_KEY  = "..."
    EMAIL_FROM             = "noreply@yourdomain.com"
"""

import io
import base64
import hashlib
import hmac
import json
import random
import re
import time

import streamlit as st

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Sentiment Analysis Studio",
    page_icon=":material/sentiment_satisfied:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;700;800;900&family=Poppins:wght@300;400;500;600&display=swap');

:root,html[data-theme="light"],html[data-theme="dark"],[data-theme="light"],[data-theme="dark"] {
    color-scheme: dark !important;
    --bg:#0a0c1a;--surface:#0f1120;--surface2:#141728;--surface3:#1a1e30;
    --border:#232640;--border-hi:#323760;
    --blue:#4080ff;--blue-lo:#1a3acc;--blue-glow:rgba(64,128,255,0.16);--blue-glow-hi:rgba(64,128,255,0.32);
    --text:#eef0fa;--text-dim:#b8bcd4;--muted:#5a5f82;
    --pos:#20c65a;--pos-dim:rgba(32,198,90,0.14);
    --neg:#ff3d52;--neg-dim:rgba(255,61,82,0.14);
    --amber:#f0a500;--amber-dim:rgba(240,165,0,0.14);
}
html,body{background:var(--bg)!important;color:var(--text)!important;color-scheme:dark!important;}
.stApp,.stApp>div,section[data-testid="stAppViewContainer"],section[data-testid="stAppViewContainer"]>div,
div[data-testid="stMain"],div[data-testid="stVerticalBlock"],div[data-testid="stHorizontalBlock"],
.main .block-container,.block-container{background-color:var(--bg)!important;color:var(--text)!important;}
*,*::before,*::after{font-family:'Poppins',sans-serif;box-sizing:border-box;}
p,span,div,li,td,th,label,h1,h2,h3,h4,h5,h6,
.stMarkdown,.stMarkdown p,.stMarkdown span,
[data-testid="stText"],[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] li,[data-testid="stMarkdownContainer"] strong,
[data-testid="stMarkdownContainer"] em,[class*="css"]{color:var(--text)!important;}
.stCaption,[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{color:var(--muted)!important;}
code{background:var(--surface3)!important;color:var(--blue)!important;padding:0.1em 0.4em;border-radius:3px;}
#MainMenu,footer,header{visibility:hidden;}
[data-testid="stToolbar"]{display:none!important;}
[data-testid="stDecoration"]{display:none!important;}
header[data-testid="stHeader"]{display:none!important;}
h1{font-size:2rem!important;font-weight:700!important;color:#f1f5f9!important;
   letter-spacing:-.02em!important;margin-bottom:.15rem!important;}
::-webkit-scrollbar{width:5px;height:5px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:var(--border-hi);border-radius:4px;}
::-webkit-scrollbar-thumb:hover{background:var(--muted);}

/* SECTION HEADER */
.section-header{display:flex;align-items:center;gap:0.55rem;font-family:'Inter Tight',sans-serif;
    font-size:0.72rem;font-weight:800;letter-spacing:0.18em;text-transform:uppercase;
    color:var(--text-dim)!important;margin:1.6rem 0 0.9rem;}
.section-header .dot{width:6px;height:6px;border-radius:50%;background:var(--blue);flex-shrink:0;}

/* BUTTONS */
.stButton>button{background:var(--blue)!important;color:#fff!important;border:none!important;
    border-radius:6px!important;font-family:'Inter Tight',sans-serif!important;font-size:0.78rem!important;
    font-weight:800!important;letter-spacing:0.12em!important;text-transform:uppercase!important;
    padding:0.5rem 1.5rem!important;transition:background 0.15s,box-shadow 0.15s,transform 0.1s!important;
    box-shadow:0 2px 10px rgba(64,128,255,0.3)!important;}
.stButton>button:hover{background:#2d6aee!important;box-shadow:0 4px 18px rgba(64,128,255,0.45)!important;transform:translateY(-1px)!important;}
.stButton>button:active{transform:translateY(0px)!important;}
.stButton>button:disabled{background:var(--surface3)!important;color:var(--muted)!important;box-shadow:none!important;transform:none!important;}
.stDownloadButton>button{background:transparent!important;color:var(--blue)!important;
    border:1px solid rgba(64,128,255,0.35)!important;border-radius:6px!important;
    font-family:'Inter Tight',sans-serif!important;font-size:0.72rem!important;
    font-weight:700!important;letter-spacing:0.1em!important;text-transform:uppercase!important;}
.stDownloadButton>button:hover{background:var(--blue-glow)!important;border-color:var(--blue)!important;}

/* FORM CONTROLS */
.stTextInput input,.stTextArea textarea{background:var(--bg)!important;border:1px solid var(--border)!important;
    border-radius:6px!important;color:var(--text)!important;font-family:'Poppins',sans-serif!important;
    font-size:0.88rem!important;caret-color:var(--blue)!important;}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:var(--blue)!important;box-shadow:0 0 0 3px var(--blue-glow)!important;}
div[data-baseweb="select"]>div,div[data-baseweb="select"]>div>div{background:var(--bg)!important;border-color:var(--border)!important;color:var(--text)!important;}
div[data-baseweb="select"] span,div[data-baseweb="select"] input{color:var(--text)!important;}
div[data-baseweb="menu"],div[data-baseweb="popover"]{background:var(--surface2)!important;border:1px solid var(--border-hi)!important;box-shadow:0 8px 32px rgba(0,0,0,0.5)!important;}
div[data-baseweb="menu"] li,div[data-baseweb="menu"] [role="option"]{color:var(--text)!important;background:transparent!important;}
div[data-baseweb="menu"] li:hover,div[data-baseweb="menu"] [aria-selected="true"]{background:var(--surface3)!important;}

/* TABS */
button[data-baseweb="tab"]{font-family:'Inter Tight',sans-serif!important;font-size:0.72rem!important;
    font-weight:800!important;letter-spacing:0.14em!important;text-transform:uppercase!important;
    color:var(--muted)!important;background:transparent!important;}
button[data-baseweb="tab"][aria-selected="true"]{color:var(--blue)!important;}
div[data-baseweb="tab-highlight"]{background:var(--blue)!important;}
div[data-baseweb="tab-border"]{background:var(--border)!important;}

/* FILE UPLOADER */
[data-testid="stFileUploader"]{background:var(--surface2)!important;border:1px dashed var(--border-hi)!important;border-radius:8px!important;}
[data-testid="stFileUploader"]:hover{border-color:var(--blue)!important;}
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] p{color:var(--muted)!important;}

/* METRIC CARD */
.metric-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1.2rem;text-align:center;}
.metric-card h3{color:var(--muted)!important;font-size:0.62rem;margin:0 0 0.4rem;text-transform:uppercase;letter-spacing:0.18em;font-weight:700;}
.metric-card .value{font-family:'Inter Tight',sans-serif;font-size:1.8rem;font-weight:900;color:var(--text)!important;}
.metric-card .sub{font-size:0.72rem;color:var(--muted)!important;}
.c-pos{color:var(--pos)!important;} .c-neg{color:var(--neg)!important;}
.c-neu{color:#90cdf4!important;}   .c-amb{color:var(--amber)!important;}

/* PROGRESS */
.stProgress>div>div{background:var(--blue)!important;}

/* AUTH */
.auth-wrap{max-width:420px;margin:5rem auto;padding:2.5rem 2.5rem 2rem;background:var(--surface);
    border:1px solid var(--border);border-top:3px solid var(--blue);border-radius:0 0 10px 10px;}
.auth-logo{font-family:'Inter Tight',sans-serif;font-size:1.3rem;font-weight:900;
    letter-spacing:0.12em;color:var(--blue)!important;margin-bottom:0.2rem;}
.auth-title{font-family:'Inter Tight',sans-serif;font-size:1rem;font-weight:700;
    color:var(--text)!important;margin-bottom:0.25rem;}
.auth-sub{font-size:0.8rem;color:var(--muted)!important;margin-bottom:1.5rem;}
.auth-note{font-size:0.72rem;color:var(--muted)!important;margin-top:1rem;text-align:center;line-height:1.5;}

/* SIDEBAR */
[data-testid="stSidebar"]{background:#0f172a!important;border-right:1px solid #1e293b!important;}
[data-testid="stSidebar"] *{color:#cbd5e1!important;}
[data-testid="stSidebar"] .block-container{padding:1.25rem 1rem!important;max-width:100%!important;}
.sidebar-section{font-size:.7rem;font-weight:600;text-transform:uppercase;
    letter-spacing:.1em;color:#64748b;margin:1.2rem 0 .4rem;display:block;}
.block-container{padding:1.5rem 2rem 3rem!important;max-width:1400px!important;margin:0 auto!important;}

/* FILE BADGE */
.file-badge{display:inline-flex;align-items:center;gap:0.4rem;background:var(--surface2);
    border:1px solid var(--border-hi);border-radius:5px;padding:0.25rem 0.65rem;
    font-size:0.72rem;color:var(--text-dim)!important;margin:0.2rem 0.2rem 0 0;}
.file-badge .ext{font-family:'Inter Tight',sans-serif;font-weight:800;font-size:0.65rem;
    color:var(--blue)!important;letter-spacing:0.06em;}

/* FOOTER */
.footer{margin-top:4rem;padding:1.5rem 0;border-top:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}
.footer-brand{font-family:'Inter Tight',sans-serif;font-size:0.72rem;font-weight:900;letter-spacing:0.18em;color:var(--muted)!important;}
.footer-note{font-size:0.65rem;color:var(--muted)!important;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# DEPENDENCY CHECKS
# ─────────────────────────────────────────────────────────────

try:
    import anthropic as _anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# ─────────────────────────────────────────────────────────────
# POSTGRES PROJECT STORAGE
# ─────────────────────────────────────────────────────────────

try:
    from storage_sentiment import (
        init_db as _init_db,
        get_projects, project_exists, create_project,
        rename_project, delete_project, load_project, save_project,
    )
    _init_db()
    DB_AVAILABLE = True
except Exception as _db_err:
    DB_AVAILABLE = False
    _db_err_msg = str(_db_err)

# ─────────────────────────────────────────────────────────────
# SECRETS
# ─────────────────────────────────────────────────────────────

claude_key     = st.secrets.get("ANTHROPIC_API_KEY", "")
ALLOWED_DOMAIN = st.secrets.get("ALLOWED_DOMAIN", "@segaamerica.com")

# ─────────────────────────────────────────────────────────────
# OTP AUTH — identical pattern to documentcompare.py
# ─────────────────────────────────────────────────────────────

OTP_EXPIRY_SECS    = 600  # 10 minutes
COOKIE_EXPIRY_DAYS = 7
MAX_OTP_ATTEMPTS   = 5


def _send_otp(email: str, code: str) -> bool:
    try:
        import boto3
        from botocore.exceptions import ClientError
        ses = boto3.client(
            "ses",
            region_name=st.secrets.get("AWS_SES_REGION", "us-east-1"),
            aws_access_key_id=st.secrets.get("AWS_ACCESS_KEY_ID", ""),
            aws_secret_access_key=st.secrets.get("AWS_SECRET_ACCESS_KEY", ""),
        )
        ses.send_email(
            Source=st.secrets.get("EMAIL_FROM", f"noreply{ALLOWED_DOMAIN}"),
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": "Sentiment Studio — Your verification code", "Charset": "UTF-8"},
                "Body": {
                    "Text": {
                        "Data": (
                            f"Your Sentiment Analysis Studio verification code is: {code}\n\n"
                            "This code expires in 10 minutes.\n"
                            "If you didn't request this, you can safely ignore this email."
                        ),
                        "Charset": "UTF-8",
                    },
                    "Html": {
                        "Data": f"""
<div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:32px 24px;">
  <div style="font-size:20px;font-weight:900;letter-spacing:0.1em;color:#4080ff;margin-bottom:4px;">SENTIMENT STUDIO</div>
  <div style="font-size:13px;color:#444;margin-bottom:28px;">AI-Powered Analysis Platform</div>
  <div style="font-size:14px;color:#222;margin-bottom:16px;">Your verification code is:</div>
  <div style="font-size:42px;font-weight:900;letter-spacing:0.18em;color:#1a1a2e;
              background:#f0f4ff;border-radius:8px;padding:18px 24px;
              display:inline-block;margin-bottom:24px;">{code}</div>
  <div style="font-size:12px;color:#888;">
    This code expires in 10 minutes.<br>
    If you didn't request this, you can safely ignore this email.
  </div>
</div>""",
                        "Charset": "UTF-8",
                    },
                },
            },
        )
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False


def _make_token(email: str) -> str:
    secret  = st.secrets.get("COOKIE_SIGNING_KEY", "fallback-change-this")
    expiry  = int(time.time()) + (COOKIE_EXPIRY_DAYS * 86400)
    payload = f"{email}|{expiry}"
    sig     = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}|{sig}".encode()).decode()


def _verify_token(token: str) -> "str | None":
    try:
        secret   = st.secrets.get("COOKIE_SIGNING_KEY", "fallback-change-this")
        decoded  = base64.urlsafe_b64decode(token.encode()).decode()
        email, expiry_str, sig = decoded.rsplit("|", 2)
        payload  = f"{email}|{expiry_str}"
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        if int(time.time()) > int(expiry_str):
            return None
        return email
    except Exception:
        return None


# ── Read token from URL query param ──────────────────────────
_url_token   = st.query_params.get("t", "")
_token_email = _verify_token(_url_token) if _url_token else None

# ── Auth session state ────────────────────────────────────────
for _k, _v in [
    ("auth_verified",  False),
    ("auth_email",     ""),
    ("auth_token",     ""),
    ("otp_code",       ""),
    ("otp_email",      ""),
    ("otp_expiry",     0),
    ("otp_sent",       False),
    ("otp_attempts",   0),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

if _token_email and not st.session_state.auth_verified:
    st.session_state.auth_verified = True
    st.session_state.auth_email    = _token_email
    st.session_state.auth_token    = _url_token

# ── Login gate ────────────────────────────────────────────────
if not st.session_state.auth_verified:
    _lc, _mc, _rc = st.columns([1, 2, 1])
    with _mc:
        st.markdown("""
        <div class="auth-wrap">
          <div class="auth-logo">SENTIMENT STUDIO</div>
          <div class="auth-title">Sign in to continue</div>
          <div class="auth-sub">Enter your work email to receive a one-time verification code.</div>
        </div>
        """, unsafe_allow_html=True)

        if not st.session_state.otp_sent:
            _email_input = st.text_input(
                "Email address",
                placeholder=f"you{ALLOWED_DOMAIN}",
                label_visibility="collapsed",
                key="auth_email_input",
            )
            if st.button("Send verification code", use_container_width=True):
                if _email_input:
                    if not _email_input.strip().lower().endswith(ALLOWED_DOMAIN):
                        st.error(f"Access restricted to {ALLOWED_DOMAIN} addresses.")
                    else:
                        _code = str(random.randint(100000, 999999))
                        if _send_otp(_email_input.strip().lower(), _code):
                            st.session_state.otp_code     = _code
                            st.session_state.otp_email    = _email_input.strip().lower()
                            st.session_state.otp_expiry   = time.time() + OTP_EXPIRY_SECS
                            st.session_state.otp_sent     = True
                            st.session_state.otp_attempts = 0
                            st.rerun()
        else:
            st.info(f"Code sent to **{st.session_state.otp_email}** — check your inbox.")
            _code_input = st.text_input(
                "6-digit code", placeholder="123456",
                label_visibility="collapsed", max_chars=6,
                key="auth_code_input",
            )
            if st.button("Verify code", use_container_width=True):
                if _code_input:
                    if st.session_state.otp_attempts >= MAX_OTP_ATTEMPTS:
                        st.error("Too many attempts. Please request a new code.")
                        st.session_state.otp_sent = False
                    elif time.time() > st.session_state.otp_expiry:
                        st.error("Code expired. Please request a new one.")
                        st.session_state.otp_sent = False
                    elif _code_input.strip() != st.session_state.otp_code:
                        st.session_state.otp_attempts += 1
                        _rem = MAX_OTP_ATTEMPTS - st.session_state.otp_attempts
                        st.error(f"Incorrect code. {_rem} attempt{'s' if _rem != 1 else ''} remaining.")
                    else:
                        st.session_state.auth_verified = True
                        st.session_state.auth_email    = st.session_state.otp_email
                        st.session_state.otp_code      = ""
                        _tok = _make_token(st.session_state.auth_email)
                        st.session_state.auth_token    = _tok
                        st.query_params["t"]           = _tok
                        st.rerun()

            if st.button("← Use a different email", key="auth_back"):
                st.session_state.otp_sent = False
                st.session_state.otp_code = ""
                st.rerun()

        st.markdown(
            f'<div class="auth-note">Restricted to <code>{ALLOWED_DOMAIN}</code> addresses.<br>'
            f'Codes expire after 10 minutes · Sessions last {COOKIE_EXPIRY_DAYS} days.</div>',
            unsafe_allow_html=True,
        )
    st.stop()

# ─────────────────────────────────────────────────────────────
# APP SESSION STATE  (init before any widgets)
# ─────────────────────────────────────────────────────────────

OWNER = st.session_state.auth_email

for _k, _v in [
    ("datasets",        {}),
    ("analysed_dfs",    {}),
    ("chat_history",    []),
    ("chat_pending",    False),
    ("analysis_done",   False),
    ("active_project",  ""),
    ("col_config",      {}),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─────────────────────────────────────────────────────────────
# PROJECT HELPERS
# ─────────────────────────────────────────────────────────────

def _load_project(name: str):
    if not DB_AVAILABLE:
        return
    data = load_project(OWNER, name)
    if not data:
        return
    st.session_state["active_project"] = name

    # doc_names — file names belonging to this project
    stored_names = data.get("doc_names", [])

    # Keep only datasets/results that still belong to this project
    st.session_state["datasets"] = {
        k: v for k, v in st.session_state["datasets"].items() if k in stored_names
    }

    # Restore analysed DataFrames from results_json if not already in session
    import pandas as pd
    results = data.get("results_json", {})
    for fname, rows in results.items():
        if fname not in st.session_state["analysed_dfs"] and rows:
            try:
                st.session_state["analysed_dfs"][fname] = pd.DataFrame(rows)
            except Exception:
                pass

    # Restore column/batch config choices
    st.session_state["col_config"] = data.get("col_config", {})

    # Restore chat history
    st.session_state["chat_history"] = data.get("chat_history", [])

    st.session_state["analysis_done"] = bool(st.session_state["analysed_dfs"])

def _clear_project():
    st.session_state["active_project"]  = ""
    st.session_state["datasets"]        = {}
    st.session_state["analysed_dfs"]    = {}
    st.session_state["chat_history"]    = []
    st.session_state["col_config"]      = {}
    st.session_state["analysis_done"]   = False

def _save_current_project():
    ap = st.session_state.get("active_project", "")
    if not ap or not DB_AVAILABLE:
        return
    save_project(
        OWNER, ap,
        doc_names=list(st.session_state.get("datasets", {}).keys()),
    )

# ─────────────────────────────────────────────────────────────
# SIDEBAR — user info + sign-out + projects
# ─────────────────────────────────────────────────────────────

with st.sidebar:
    # App title
    st.markdown(
        "<div style='font-size:1rem;font-weight:700;color:#f1f5f9;margin-bottom:.25rem;'>Sentiment Studio</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='font-size:.65rem;color:#475569;text-transform:uppercase;letter-spacing:.1em;margin-bottom:1rem;'>AI-Powered Analysis Platform</div>",
        unsafe_allow_html=True,
    )

    # User + sign out
    st.markdown(
        f'<div style="font-size:.6rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;'
        f'color:#5a5f82;margin-bottom:.3rem;">Signed in</div>'
        f'<div style="font-size:.7rem;font-weight:600;color:#b8bcd4;margin-bottom:.75rem;">'
        f'{OWNER}</div>',
        unsafe_allow_html=True,
    )
    if st.button("Sign out", key="sign_out_btn"):
        st.query_params.clear()
        for _k in ["auth_verified", "auth_email", "auth_token",
                   "otp_sent", "otp_code", "otp_email", "otp_expiry", "otp_attempts"]:
            st.session_state[_k] = False if _k == "auth_verified" else ""
        st.rerun()

    st.markdown("<hr style='border:none;border-top:1px solid #232640;margin:.5rem 0 1rem;'>",
                unsafe_allow_html=True)

    # Projects section
    st.markdown(
        "<div style='font-size:.6rem;font-weight:700;letter-spacing:.12em;"
        "text-transform:uppercase;color:#475569;margin-bottom:.3rem;'>Projects</div>",
        unsafe_allow_html=True,
    )

    if not DB_AVAILABLE:
        st.warning(f"⚠️ Database unavailable. ({_db_err_msg})")
    else:
        # Sync URL param → session on first load
        _qp_proj = st.query_params.get("project", "")
        _all_proj = get_projects(OWNER)
        _proj_names = [p["name"] for p in _all_proj]

        if _qp_proj and _qp_proj in _proj_names and not st.session_state.get("active_project"):
            _load_project(_qp_proj)

        _active = st.session_state.get("active_project", "")

        _opts = ["— select a project —"] + _proj_names + ["＋ New project"]
        _def  = _opts.index(_active) if _active in _opts else 0
        _sel  = st.selectbox("Project", _opts, index=_def, label_visibility="collapsed",
                             key="project_selector")

        if _sel == "＋ New project":
            _new_name = st.text_input("Project name", placeholder="e.g. Q3 Analysis",
                                      key="new_proj_name")
            if st.button("Create project", use_container_width=True, type="primary"):
                _nn = _new_name.strip()
                if not _nn:
                    st.error("Enter a project name.")
                elif project_exists(OWNER, _nn):
                    st.error(f"'{_nn}' already exists.")
                else:
                    create_project(OWNER, _nn)
                    _clear_project()
                    _load_project(_nn)
                    st.query_params["project"] = _nn
                    st.rerun()

        elif _sel == "— select a project —":
            if _active:
                _clear_project()
                st.query_params.pop("project", None)
                st.rerun()

        elif _sel != _active:
            _clear_project()
            _load_project(_sel)
            st.query_params["project"] = _sel
            st.rerun()

        # Active project actions
        if _active and _active in _proj_names:
            _proj_meta = next((p for p in _all_proj if p["name"] == _active), {})
            _updated   = (_proj_meta.get("updated_at", "")[:16].replace("T", " ") + " UTC"
                          if _proj_meta.get("updated_at") else "unsaved")
            st.caption(f"Last saved: {_updated}")

            _col_save, _col_rename, _col_del = st.columns([3, 2, 1])

            with _col_save:
                if st.button("💾 Save", use_container_width=True,
                             help="Save current state to this project"):
                    _results = {
                        fname: df.to_dict("records")
                        for fname, df in st.session_state.get("analysed_dfs", {}).items()
                    }
                    save_project(
                        OWNER, _active,
                        doc_names=list(st.session_state.get("datasets", {}).keys()),
                        col_config=st.session_state.get("col_config", {}),
                        results_json=_results,
                        chat_history=st.session_state.get("chat_history", []),
                    )
                    st.toast(f'Saved "{_active}"', icon="✅")

            with _col_rename:
                if st.button("✏️", help="Rename project", use_container_width=True):
                    st.session_state["_renaming_proj"] = True

            with _col_del:
                if st.button("🗑", help="Delete project", use_container_width=True):
                    st.session_state["_confirm_del_proj"] = True

            # Rename UI
            if st.session_state.pop("_renaming_proj", False):
                _rn = st.text_input("New name", value=_active, key="_rename_proj_input")
                if st.button("Rename", key="_rename_proj_confirm"):
                    try:
                        rename_project(OWNER, _active, _rn.strip())
                        _clear_project()
                        _load_project(_rn.strip())
                        st.query_params["project"] = _rn.strip()
                        st.rerun()
                    except Exception as _re:
                        st.error(str(_re))

            # Delete confirmation UI
            if st.session_state.pop("_confirm_del_proj", False):
                st.warning(f"Delete **{_active}**? This cannot be undone.")
                _dc1, _dc2 = st.columns(2)
                with _dc1:
                    if st.button("Yes, delete", type="primary", key="_del_proj_yes"):
                        delete_project(OWNER, _active)
                        _clear_project()
                        st.query_params.pop("project", None)
                        st.rerun()
                with _dc2:
                    if st.button("Cancel", key="_del_proj_no"):
                        st.rerun()

    st.markdown(
        "<hr style='border:none;border-top:1px solid #1e293b;margin:.75rem 0 .5rem;'>",
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────
# GATE: require active project
# ─────────────────────────────────────────────────────────────

if DB_AVAILABLE and not st.session_state.get("active_project"):
    st.markdown(
        "<div style='text-align:center;padding:4rem 2rem;color:#475569;'>"
        "<div style='font-size:2.5rem;margin-bottom:1rem;'>📁</div>"
        "<div style='font-size:1.1rem;font-weight:600;color:#94a3b8;margin-bottom:.5rem;'>"
        "No project selected</div>"
        "<div style='font-size:.85rem;'>Select an existing project or create a new one in the sidebar to get started.</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.stop()

# ─────────────────────────────────────────────────────────────
# PAGE HEADER
# ─────────────────────────────────────────────────────────────

st.markdown(
    "<h1>Sentiment Analysis Studio</h1>"
    "<div style='font-size:.78rem;color:#475569;margin-bottom:1.5rem;'>"
    "Upload datasets &nbsp;·&nbsp; Run Claude-powered analysis &nbsp;·&nbsp; Explore dashboard &nbsp;·&nbsp; Chat with your data"
    "</div>",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────
# UPLOAD PANEL  (main page — files register immediately on rerun)
# ─────────────────────────────────────────────────────────────

st.markdown('<div class="section-header"><span class="dot"></span>UPLOAD DATASETS</div>',
            unsafe_allow_html=True)

_up_col, _info_col = st.columns([3, 2], gap="large")

with _up_col:
    uploaded = st.file_uploader(
        "Drop XLSX files here or click to browse",
        type=["xlsx"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        key="main_uploader",
    )
    # ── FIX: process uploads immediately inside the same column block ──
    if uploaded:
        _changed = False
        for _f in uploaded:
            if _f.name not in st.session_state.datasets:
                st.session_state.datasets[_f.name] = pd.read_excel(_f)
                _changed = True
        if _changed:
            st.rerun()  # rerun so info_col reflects new state instantly

with _info_col:
    if st.session_state.get("datasets"):
        st.markdown('<div style="font-size:0.65rem;font-weight:800;letter-spacing:0.2em;'
                    'text-transform:uppercase;color:var(--muted);">Loaded files</div>',
                    unsafe_allow_html=True)
        badges = "".join(
            f'<span class="file-badge"><span class="ext">XLSX</span>&nbsp;{fn}&nbsp;'
            f'<span style="color:var(--muted);">({len(df):,} rows)</span></span>'
            for fn, df in st.session_state.datasets.items()
        )
        st.markdown(badges + "<br>", unsafe_allow_html=True)
        if st.button("🗑 Clear all files", key="clear_files"):
            st.session_state.datasets     = {}
            st.session_state.analysed_dfs = {}
            st.session_state.analysis_done = False
            st.rerun()
    else:
        st.markdown(
            '<div style="font-size:0.8rem;color:var(--muted);padding-top:0.5rem;">'
            'Upload one or more <code>.xlsx</code> files to get started.</div>',
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────────────────────
# API KEY CHECK
# ─────────────────────────────────────────────────────────────

if not claude_key:
    st.error("⚠️  `ANTHROPIC_API_KEY` not set in `.streamlit/secrets.toml`.")
    st.stop()

if not ANTHROPIC_AVAILABLE:
    st.error("⚠️  Run: `pip install anthropic`")
    st.stop()

client = _anthropic.AnthropicBedrock(
    aws_access_key   = st.secrets.get("AWS_ACCESS_KEY_ID_API", ""),
    aws_secret_key   = st.secrets.get("AWS_SECRET_ACCESS_KEY_API", ""),
    aws_region       = st.secrets.get("AWS_BEDROCK_REGION", "us-east-1"),
)

if not st.session_state.datasets:
    st.info("⬆️ Upload one or more XLSX files above to get started.")
    st.stop()

# ─────────────────────────────────────────────────────────────
# ANALYSIS HELPERS
# ─────────────────────────────────────────────────────────────

SENTIMENT_COLORS = {
    "positive": "#20c65a", "negative": "#ff3d52",
    "neutral":  "#90cdf4", "mixed":    "#f0a500", "unknown": "#5a5f82",
}


def detect_text_columns(df) -> list:
    prefer = ["title", "opening text", "hit sentence", "text", "content", "description", "body"]
    candidates = []
    for col in df.columns:
        if df[col].dtype == object:
            avg = df[col].dropna().head(5).astype(str).str.len().mean() or 0
            if avg > 20:
                candidates.append(col)
    candidates.sort(key=lambda c: next((i for i, p in enumerate(prefer) if p in c.lower()), 999))
    return candidates


def build_prompt(texts: list, col_name: str) -> str:
    numbered = "\n".join(f"{i+1}. {t[:500]}" for i, t in enumerate(texts))
    return f"""Analyse the sentiment of each text below (column: "{col_name}").
Return ONLY a valid JSON array — no preamble, no markdown fences — with one object per text in the same order.
Each object must have exactly:
  "sentiment": one of "positive","negative","neutral","mixed"
  "score":     float -1.0 to 1.0
  "confidence":float 0.0–1.0
  "reason":    one concise sentence (max 15 words)

Texts:
{numbered}

JSON array:"""


def analyse_batch(texts: list, col_name: str) -> list:
    msg = client.messages.create(
        model="us.anthropic.claude-haiku-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": build_prompt(texts, col_name)}],
    )
    raw = msg.content[0].text.strip()
    m   = re.search(r'\[[\s\S]*\]', raw)
    if m:
        return json.loads(m.group())
    return [{"sentiment": "unknown", "score": 0.0, "confidence": 0.0, "reason": "parse error"}] * len(texts)


def run_analysis(df, col: str, batch_size: int = 20, progress_cb=None):
    df    = df.copy()
    texts = df[col].fillna("").astype(str).tolist()
    results, total_batches = [], (len(texts) + batch_size - 1) // batch_size
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        results.extend(analyse_batch(batch, col))
        if progress_cb:
            progress_cb((i + len(batch)) / len(texts), i // batch_size + 1, total_batches)
        if i + batch_size < len(texts):
            time.sleep(0.25)
    rdf = pd.DataFrame(results)
    for c in ["sentiment", "score", "confidence", "reason"]:
        if c not in rdf.columns:
            rdf[c] = None
    df["sentiment"]            = rdf["sentiment"].values
    df["sentiment_score"]      = pd.to_numeric(rdf["score"],      errors="coerce")
    df["sentiment_confidence"] = pd.to_numeric(rdf["confidence"], errors="coerce")
    df["sentiment_reason"]     = rdf["reason"].values
    return df


def sentiment_summary(df) -> dict:
    if "sentiment" not in df.columns:
        return {}
    return {
        "counts":    df["sentiment"].value_counts().to_dict(),
        "total":     len(df),
        "avg_score": df["sentiment_score"].mean() if "sentiment_score" in df.columns else 0,
    }


# ─────────────────────────────────────────────────────────────
# MAIN TABS
# ─────────────────────────────────────────────────────────────

tab_analysis, tab_dashboard, tab_chat = st.tabs(["🔬  ANALYSIS", "📊  DASHBOARD", "💬  CHAT"])

# ══════════════════════════════════════════════════════════════
# TAB 1 — ANALYSIS
# ══════════════════════════════════════════════════════════════

with tab_analysis:
    st.markdown('<div class="section-header"><span class="dot"></span>CONFIGURE DATASETS</div>', unsafe_allow_html=True)

    dataset_configs = {}
    for fname, df in st.session_state.datasets.items():
        with st.expander(f"📄 {fname}  —  {len(df):,} rows × {len(df.columns)} cols", expanded=True):
            text_cols = detect_text_columns(df)
            if not text_cols:
                st.warning("No suitable text columns detected.")
                continue
            # Restore saved col choice if available
            _saved_cfg  = st.session_state.get("col_config", {}).get(fname, {})
            _saved_col  = _saved_cfg.get("col", text_cols[0])
            _col_default = _saved_col if _saved_col in text_cols else text_cols[0]
            _saved_batch = _saved_cfg.get("batch", 20)

            col_choice = st.selectbox("Text column to analyse", text_cols,
                                      index=text_cols.index(_col_default),
                                      key=f"col_{fname}")
            c1, c2 = st.columns(2)
            n_rows = c1.slider("Max rows (0 = all)", 0, len(df), min(500, len(df)), key=f"rows_{fname}")
            batch  = c2.select_slider("Batch size", options=[5, 10, 20, 30, 50],
                                       value=_saved_batch if _saved_batch in [5,10,20,30,50] else 20,
                                       key=f"batch_{fname}")
            # Keep col_config in sync so Save captures the latest choices
            st.session_state["col_config"][fname] = {"col": col_choice, "batch": batch}
            dataset_configs[fname] = {"col": col_choice, "n_rows": n_rows or len(df), "batch": batch}

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀  RUN SENTIMENT ANALYSIS", use_container_width=True):
        for fname, cfg in dataset_configs.items():
            df_sub = st.session_state.datasets[fname].head(cfg["n_rows"]).copy()
            st.markdown(
                f'<div class="section-header"><span class="dot"></span>{fname} — <code>{cfg["col"]}</code></div>',
                unsafe_allow_html=True,
            )
            status_txt = st.empty()
            prog_bar   = st.progress(0)

            def _cb(pct, bn, bt, fname=fname):
                prog_bar.progress(pct)
                status_txt.markdown(f"Batch {bn}/{bt} — {int(pct*100)}% complete")

            try:
                df_result = run_analysis(df_sub, cfg["col"], cfg["batch"], _cb)
                st.session_state.analysed_dfs[fname] = df_result
                prog_bar.progress(1.0)
                status_txt.markdown(f"✅ {len(df_result):,} rows analysed")
            except Exception as e:
                st.error(f"Error: {e}")

        st.session_state.analysis_done = True
        st.success("🎉 All analyses complete!")

        # Auto-save results to active project if one is selected
        _ap = st.session_state.get("active_project", "")
        if _ap and DB_AVAILABLE:
            _results_to_save = {
                fname: df.to_dict("records")
                for fname, df in st.session_state.analysed_dfs.items()
            }
            save_project(
                OWNER, _ap,
                doc_names=list(st.session_state.datasets.keys()),
                col_config=st.session_state.get("col_config", {}),
                results_json=_results_to_save,
            )
            st.toast(f'Auto-saved to "{_ap}"', icon="💾")

    if st.session_state.analysed_dfs:
        st.markdown('<div class="section-header"><span class="dot"></span>RESULTS PREVIEW</div>', unsafe_allow_html=True)
        for fname, df in st.session_state.analysed_dfs.items():
            with st.expander(f"📋 {fname}"):
                show = [c for c in ["title", "Opening Text", "Hit Sentence", "sentiment",
                                     "sentiment_score", "sentiment_confidence", "sentiment_reason"]
                        if c in df.columns]
                st.dataframe(df[show].head(50), use_container_width=True)
                buf = io.BytesIO()
                df.to_excel(buf, index=False)
                st.download_button(
                    f"⬇  Download {fname} with sentiment", buf.getvalue(),
                    file_name=f"sentiment_{fname}",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_{fname}",
                )

# ══════════════════════════════════════════════════════════════
# TAB 2 — DASHBOARD
# ══════════════════════════════════════════════════════════════

with tab_dashboard:
    if not st.session_state.analysed_dfs:
        st.info("Run the analysis first to see the dashboard.")
    elif not PLOTLY_AVAILABLE:
        st.error("Run: `pip install plotly`")
    else:
        st.markdown('<div class="section-header"><span class="dot"></span>ANALYTICS OVERVIEW</div>', unsafe_allow_html=True)

        ds_names = list(st.session_state.analysed_dfs.keys())
        sel = st.selectbox("Dataset", ["All datasets"] + ds_names)

        if sel == "All datasets":
            parts = []
            for fn, df in st.session_state.analysed_dfs.items():
                tmp = df.copy(); tmp["_source"] = fn; parts.append(tmp)
            plot_df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
        else:
            plot_df = st.session_state.analysed_dfs[sel].copy()
            plot_df["_source"] = sel

        if not plot_df.empty and "sentiment" in plot_df.columns:
            total = len(plot_df)
            pos = (plot_df["sentiment"] == "positive").sum()
            neg = (plot_df["sentiment"] == "negative").sum()
            neu = (plot_df["sentiment"] == "neutral").sum()
            avg_s = plot_df["sentiment_score"].mean() if "sentiment_score" in plot_df.columns else 0

            c1, c2, c3, c4, c5 = st.columns(5)
            for cw, label, val, css in [
                (c1, "Total Rows", f"{total:,}", ""),
                (c2, "Positive",   f"{pos:,}<br><span class='sub'>{pos/total*100:.1f}%</span>", "c-pos"),
                (c3, "Negative",   f"{neg:,}<br><span class='sub'>{neg/total*100:.1f}%</span>", "c-neg"),
                (c4, "Neutral",    f"{neu:,}<br><span class='sub'>{neu/total*100:.1f}%</span>", "c-neu"),
                (c5, "Avg Score",  f"{avg_s:+.3f}", "c-pos" if avg_s >= 0 else "c-neg"),
            ]:
                cw.markdown(
                    f'<div class="metric-card"><h3>{label}</h3><div class="value {css}">{val}</div></div>',
                    unsafe_allow_html=True,
                )
            st.markdown("<br>", unsafe_allow_html=True)

            BG = "#0f1120"
            def _lay(fig, title=""):
                fig.update_layout(
                    paper_bgcolor=BG, plot_bgcolor=BG, font_color="#eef0fa",
                    title_text=title, title_font_size=13, title_font_family="Inter Tight",
                    xaxis=dict(gridcolor="#232640"), yaxis=dict(gridcolor="#232640"),
                    legend=dict(bgcolor="rgba(0,0,0,0)", font_color="#b8bcd4"),
                )
                return fig

            r1, r2 = st.columns(2)
            with r1:
                sc = plot_df["sentiment"].value_counts().reset_index()
                sc.columns = ["sentiment", "count"]
                fig = px.pie(sc, values="count", names="sentiment", hole=0.42,
                             color="sentiment", color_discrete_map=SENTIMENT_COLORS)
                st.plotly_chart(_lay(fig, "SENTIMENT DISTRIBUTION"), use_container_width=True)
            with r2:
                if sel == "All datasets":
                    grp = plot_df.groupby(["_source", "sentiment"]).size().reset_index(name="count")
                    fig = px.bar(grp, x="_source", y="count", color="sentiment",
                                 barmode="group", color_discrete_map=SENTIMENT_COLORS)
                    st.plotly_chart(_lay(fig, "BY DATASET"), use_container_width=True)
                else:
                    fig = px.histogram(plot_df, x="sentiment_score", nbins=40,
                                       color_discrete_sequence=["#4080ff"])
                    st.plotly_chart(_lay(fig, "SCORE DISTRIBUTION"), use_container_width=True)

            date_cols = [c for c in plot_df.columns if "date" in c.lower() and c != "_source"]
            r3, r4 = st.columns(2)
            with r3:
                if date_cols:
                    tmp = plot_df.copy()
                    tmp[date_cols[0]] = pd.to_datetime(tmp[date_cols[0]], errors="coerce")
                    tmp = tmp.dropna(subset=[date_cols[0]])
                    if not tmp.empty:
                        tmp["month"] = tmp[date_cols[0]].dt.to_period("M").astype(str)
                        ts = tmp.groupby(["month", "sentiment"]).size().reset_index(name="count")
                        fig = px.line(ts, x="month", y="count", color="sentiment",
                                      markers=True, color_discrete_map=SENTIMENT_COLORS)
                        st.plotly_chart(_lay(fig, "SENTIMENT OVER TIME"), use_container_width=True)
                else:
                    vdf = plot_df.dropna(subset=["sentiment_score"])
                    fig = px.violin(vdf, y="sentiment_score", x="sentiment",
                                    color="sentiment", box=True, color_discrete_map=SENTIMENT_COLORS)
                    st.plotly_chart(_lay(fig, "SCORE SPREAD"), use_container_width=True)
            with r4:
                if "sentiment_confidence" in plot_df.columns:
                    conf = plot_df.groupby("sentiment")["sentiment_confidence"].mean().reset_index()
                    conf.columns = ["sentiment", "avg_confidence"]
                    fig = px.bar(conf, x="sentiment", y="avg_confidence",
                                 color="sentiment", color_discrete_map=SENTIMENT_COLORS)
                    fig.update_yaxes(range=[0, 1])
                    st.plotly_chart(_lay(fig, "AVG CONFIDENCE"), use_container_width=True)

            if "platform" in plot_df.columns:
                plat = plot_df.groupby(["platform", "sentiment"]).size().reset_index(name="count")
                fig  = px.bar(plat, x="platform", y="count", color="sentiment",
                              barmode="stack", color_discrete_map=SENTIMENT_COLORS)
                st.plotly_chart(_lay(fig, "SENTIMENT BY PLATFORM"), use_container_width=True)

            if "sentiment_confidence" in plot_df.columns:
                low = plot_df[plot_df["sentiment_confidence"] < 0.6]
                if not low.empty:
                    st.markdown(
                        f'<div class="section-header"><span class="dot"></span>LOW-CONFIDENCE ROWS ({len(low):,})</div>',
                        unsafe_allow_html=True,
                    )
                    show = [c for c in ["title", "Opening Text", "Hit Sentence", "sentiment",
                                         "sentiment_score", "sentiment_confidence", "sentiment_reason", "_source"]
                            if c in low.columns]
                    st.dataframe(low[show].head(30), use_container_width=True)

# ══════════════════════════════════════════════════════════════
# TAB 3 — CHAT
# ══════════════════════════════════════════════════════════════

with tab_chat:
    st.markdown(
        '<div class="section-header"><span class="dot"></span>CHAT WITH CLAUDE'
        '<span style="color:var(--muted);font-size:.7rem;font-weight:400;"> '
        '— ask anything about your datasets and results</span></div>',
        unsafe_allow_html=True,
    )

    def _build_system() -> str:
        lines = ["You are a data analyst assistant. The user has uploaded these datasets:\n"]
        for fname, df in st.session_state.datasets.items():
            lines.append(f"• {fname}: {len(df):,} rows, columns: {', '.join(df.columns.tolist())}")
        if st.session_state.analysed_dfs:
            lines.append("\nSentiment analysis results:")
            for fname, df in st.session_state.analysed_dfs.items():
                if "sentiment" in df.columns:
                    summ = sentiment_summary(df)
                    lines.append(
                        f"  {fname}: {summ['total']:,} rows | "
                        + ", ".join(f"{k}: {v}" for k, v in summ["counts"].items())
                        + f" | avg score: {summ['avg_score']:+.3f}"
                    )
                    sample_cols = [c for c in ["title", "Opening Text", "Hit Sentence",
                                                "sentiment", "sentiment_score", "sentiment_reason"]
                                   if c in df.columns]
                    lines.append(f"    Sample: {json.dumps(df[sample_cols].head(10).to_dict('records'), default=str)}")
        else:
            lines.append("\nNo sentiment analysis has been run yet.")
        return "\n".join(lines)

    # Render history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Suggested prompts
    if not st.session_state.chat_history:
        _suggs = [
            "What are the key sentiment trends?",
            "Which dataset has the most negative content?",
            "Summarise the overall analysis",
            "Compare sentiment across platforms",
            "Which rows have the lowest confidence?",
            "What is the average sentiment score?",
        ]
        _sc = st.columns(3)
        for i, s in enumerate(_suggs):
            if _sc[i % 3].button(s, key=f"sug_{i}"):
                st.session_state.chat_history.append({"role": "user", "content": s})
                st.session_state.chat_pending = True
                st.rerun()

    # Stream pending reply
    if st.session_state.chat_pending:
        st.session_state.chat_pending = False
        _api_msgs = [{"role": m["role"], "content": m["content"]}
                     for m in st.session_state.chat_history]
        try:
            with st.chat_message("assistant"):
                _reply = ""
                _ph    = st.empty()
                with client.messages.stream(
                    model="us.anthropic.claude-haiku-4-6",
                    max_tokens=1000,
                    system=_build_system(),
                    messages=_api_msgs,
                ) as _stream:
                    for _delta in _stream.text_stream:
                        _reply += _delta
                        _ph.markdown(_reply + "▌")
                _ph.markdown(_reply)
            st.session_state.chat_history.append({"role": "assistant", "content": _reply})
            # Auto-save chat to active project
            _ap = st.session_state.get("active_project", "")
            if _ap and DB_AVAILABLE:
                save_project(OWNER, _ap,
                             chat_history=st.session_state.chat_history)
        except _anthropic.AuthenticationError:
            st.error("Invalid API key.")
        except _anthropic.RateLimitError:
            st.error("Rate limit reached. Wait a moment and try again.")
        except Exception as _e:
            st.error(f"Chat error: {type(_e).__name__}: {_e}")

    _user_msg = st.chat_input("Ask Claude about your datasets and sentiment results…")
    if _user_msg:
        st.session_state.chat_history.append({"role": "user", "content": _user_msg})
        st.session_state.chat_pending = True
        st.rerun()

    if st.session_state.chat_history:
        if st.button("Clear chat history", key="clear_chat"):
            st.session_state.chat_history = []
            st.session_state.chat_pending = False
            st.rerun()

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="footer">
  <div class="footer-brand">SENTIMENT ANALYSIS STUDIO</div>
  <div class="footer-note">Powered by Claude · Data processed locally · Internal use only</div>
</div>
""", unsafe_allow_html=True)