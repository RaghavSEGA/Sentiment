"""
Document Comparator — SEGA-branded Streamlit App
=================================================
Run with:  streamlit run doc_compare.py

Required:  pip install streamlit anthropic python-docx openpyxl pymupdf
"""

import io
import base64
import tempfile
import os

import streamlit as st

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="SEGA Doc Comparator",
    page_icon=":material/compare:",
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
    --amber:        #f0a500;
    --amber-dim:    rgba(240,165,0,0.14);
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

/* Ensure markdown bold/italic render correctly and are never overridden */
[data-testid="stMarkdownContainer"] strong,
[data-testid="stMarkdownContainer"] b { font-weight: 700 !important; font-style: normal !important; }
[data-testid="stMarkdownContainer"] em,
[data-testid="stMarkdownContainer"] i { font-style: italic !important; font-weight: normal !important; }
[data-testid="stMarkdownContainer"] strong em,
[data-testid="stMarkdownContainer"] em strong { font-weight: 700 !important; font-style: italic !important; }

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

/* UPLOAD ZONE */
.upload-block {
    background: var(--surface);
    border: 1px solid var(--border);
    border-top: 2px solid var(--blue);
    border-radius: 0 0 10px 10px;
    padding: 1.4rem 1.75rem 1.25rem;
    margin: 1.25rem 0 0;
}
.field-label { font-size: 0.58rem; font-weight: 700; letter-spacing: 0.22em; text-transform: uppercase; color: var(--muted) !important; margin-bottom: 0.3rem; }

/* FILE BADGE */
.file-badge {
    display: inline-flex; align-items: center; gap: 0.5rem;
    background: var(--surface2); border: 1px solid var(--border-hi);
    border-radius: 6px; padding: 0.4rem 0.85rem;
    font-size: 0.78rem; color: var(--text-dim) !important; margin-top: 0.3rem;
}
.file-badge .ext { font-family: 'Inter Tight', sans-serif; font-weight: 800; font-size: 0.7rem; color: var(--blue) !important; letter-spacing: 0.08em; }

/* FORM CONTROLS */
.stTextArea textarea {
    background: var(--bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    color: var(--text) !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: 0.88rem !important;
    caret-color: var(--blue) !important;
}
.stTextArea textarea:focus {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 3px var(--blue-glow) !important;
}
textarea::placeholder { color: var(--muted) !important; opacity: 0.6 !important; }

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
.stButton > button:disabled { background: var(--surface3) !important; color: var(--muted) !important; box-shadow: none !important; transform: none !important; }

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

/* RESULT CARD */
.result-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.5rem 1.75rem;
    margin-top: 1.25rem;
    line-height: 1.75;
}
.result-card h2, .result-card h3 {
    font-family: 'Inter Tight', sans-serif !important;
    font-weight: 800 !important;
    letter-spacing: -0.01em !important;
    color: var(--text) !important;
}

/* PROGRESS */
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

/* FILE UPLOADER */
[data-testid="stFileUploader"] {
    background: var(--surface2) !important;
    border: 1px dashed var(--border-hi) !important;
    border-radius: 8px !important;
    padding: 0.5rem !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--blue) !important;
}
[data-testid="stFileUploaderDropzone"] {
    background: transparent !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] p {
    color: var(--muted) !important;
}

/* EMPTY STATE */
.empty-state { text-align: center; padding: 5rem 2rem; }
.empty-title { font-family: 'Inter Tight', sans-serif; font-size: 1.6rem; font-weight: 900; letter-spacing: -0.02em; color: var(--border-hi) !important; margin-bottom: 0.75rem; }
.empty-sub { font-size: 0.88rem; color: var(--muted) !important; max-width: 400px; margin: 0 auto; line-height: 1.65; }

/* FOOTER */
.footer { margin-top: 4rem; padding: 1.5rem 0; border-top: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
.footer-brand { font-family: 'Inter Tight', sans-serif; font-size: 0.72rem; font-weight: 900; letter-spacing: 0.18em; color: var(--muted) !important; }
.footer-note { font-size: 0.65rem; color: var(--muted) !important; }
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
    import docx as _docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import openpyxl as _openpyxl
    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False

try:
    import fitz as _fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# ─────────────────────────────────────────────────────────────
# TEXT EXTRACTION
# ─────────────────────────────────────────────────────────────

def extract_text(uploaded_file) -> tuple[str, str]:
    """
    Returns (text_content, file_type) from an uploaded Streamlit file.
    file_type is one of: 'pdf', 'docx', 'xlsx', 'unknown'
    """
    name = uploaded_file.name.lower()
    raw  = uploaded_file.read()

    if name.endswith(".pdf"):
        if not PDF_AVAILABLE:
            return "[ERROR: PyMuPDF not installed — run: pip install pymupdf]", "pdf"
        try:
            doc  = _fitz.open(stream=raw, filetype="pdf")
            text = "\n\n".join(page.get_text() for page in doc)
            doc.close()
            return text.strip() or "[PDF contained no extractable text]", "pdf"
        except Exception as e:
            return f"[PDF extraction error: {e}]", "pdf"

    elif name.endswith(".docx"):
        if not DOCX_AVAILABLE:
            return "[ERROR: python-docx not installed — run: pip install python-docx]", "docx"
        try:
            doc  = _docx.Document(io.BytesIO(raw))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            return text.strip() or "[DOCX contained no extractable text]", "docx"
        except Exception as e:
            return f"[DOCX extraction error: {e}]", "docx"

    elif name.endswith((".xlsx", ".xls")):
        if not XLSX_AVAILABLE:
            return "[ERROR: openpyxl not installed — run: pip install openpyxl]", "xlsx"
        try:
            wb    = _openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
            lines = []
            for sheet in wb.worksheets:
                lines.append(f"\n[Sheet: {sheet.title}]")
                for row in sheet.iter_rows():
                    for cell in row:
                        if cell.value is not None and str(cell.value).strip():
                            coord = f"{sheet.title}!{cell.coordinate}"
                            lines.append(f"{coord}: {cell.value}")
            wb.close()
            return "\n".join(lines).strip() or "[XLSX contained no extractable text]", "xlsx"
        except Exception as e:
            return f"[XLSX extraction error: {e}]", "xlsx"

    else:
        return "[Unsupported file type]", "unknown"


def truncate(text: str, max_chars: int = 40_000) -> str:
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + f"\n\n[… {len(text) - max_chars:,} characters omitted for brevity …]\n\n" + text[-half:]


# ─────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────

for key, default in [
    ("comparison_result", ""),
    ("chat_history",      []),
    ("chat_pending",      False),
    ("doc_a_text",        ""),
    ("doc_b_text",        ""),
    ("doc_a_name",        ""),
    ("doc_b_name",        ""),
    ("last_focus",        ""),
    ("last_tone",         ""),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─────────────────────────────────────────────────────────────
# API KEY
# ─────────────────────────────────────────────────────────────

claude_key = st.secrets.get("ANTHROPIC_API_KEY", "")

# ─────────────────────────────────────────────────────────────
# TOP NAV
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="topbar">
  <div class="topbar-logo"><span class="seg">SEGA</span> DOC COMPARATOR</div>
  <div class="topbar-divider"></div>
  <div class="topbar-label">Document Intelligence Platform</div>
  <div class="topbar-pill">Beta</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
  <div class="hero-title">DOCUMENT <span class="accent">COMPARE</span></div>
  <div class="hero-sub">Upload two documents — PDFs, Word files, or spreadsheets — and get a detailed AI-powered comparison across any dimension you choose.</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# API KEY STATUS
# ─────────────────────────────────────────────────────────────

if not claude_key:
    st.markdown("""
<div style="background:var(--surface);border:1px solid var(--border);border-top:2px solid var(--neg);
border-radius:0 0 8px 8px;padding:1rem 1.5rem;margin-bottom:1rem;">
<div style="font-size:.62rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;
color:var(--neg);margin-bottom:.5rem;">Missing API Key</div>
<div style="font-size:.82rem;color:var(--text-dim);line-height:1.7;">
Add the following to <code>.streamlit/secrets.toml</code> in your project folder:
<pre style="background:var(--bg);border:1px solid var(--border);border-radius:6px;
padding:.75rem 1rem;margin:.6rem 0 0;font-size:.8rem;color:var(--blue);">ANTHROPIC_API_KEY = "sk-ant-your-key-here"</pre>
Then restart the app.
</div>
</div>
""", unsafe_allow_html=True)
elif not ANTHROPIC_AVAILABLE:
    st.markdown("""
<div style="background:var(--surface);border:1px solid var(--border);border-top:2px solid var(--neg);
border-radius:0 0 8px 8px;padding:1rem 1.5rem;margin-bottom:1rem;">
<div style="font-size:.62rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;
color:var(--neg);margin-bottom:.5rem;">Missing Dependency</div>
<div style="font-size:.82rem;color:var(--text-dim);">Run: <code>pip install anthropic</code></div>
</div>
""", unsafe_allow_html=True)
else:
    st.markdown("""
<div style="display:flex;gap:1rem;margin-bottom:.75rem;flex-wrap:wrap;">
  <div style="background:var(--pos-dim);border:1px solid rgba(32,198,90,.25);border-radius:6px;
  padding:.4rem 1rem;font-size:.68rem;font-weight:600;color:var(--pos);">✓ Anthropic API connected</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# UPLOAD BLOCK
# ─────────────────────────────────────────────────────────────

st.markdown('<div class="upload-block">', unsafe_allow_html=True)

col_a, col_sep, col_b = st.columns([5, 0.3, 5])

with col_a:
    st.markdown('<div class="field-label">Document A</div>', unsafe_allow_html=True)
    file_a = st.file_uploader(
        "doc_a", label_visibility="collapsed",
        type=["pdf", "docx", "xlsx"],
        key="uploader_a",
    )
    if file_a:
        ext_a = file_a.name.rsplit(".", 1)[-1].upper()
        st.markdown(
            f'<div class="file-badge"><span class="ext">{ext_a}</span>{file_a.name}</div>',
            unsafe_allow_html=True,
        )

with col_sep:
    st.markdown('<div style="display:flex;align-items:center;justify-content:center;height:100%;padding-top:1.5rem;font-size:1.4rem;color:var(--muted);">⇄</div>', unsafe_allow_html=True)

with col_b:
    st.markdown('<div class="field-label">Document B</div>', unsafe_allow_html=True)
    file_b = st.file_uploader(
        "doc_b", label_visibility="collapsed",
        type=["pdf", "docx", "xlsx"],
        key="uploader_b",
    )
    if file_b:
        ext_b = file_b.name.rsplit(".", 1)[-1].upper()
        st.markdown(
            f'<div class="file-badge"><span class="ext">{ext_b}</span>{file_b.name}</div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ── Selector card styles ──────────────────────────────────────
st.markdown("""
<style>
div[data-testid="stRadio"] > label { display: none; }
div[data-testid="stRadio"] > div {
    display: flex !important;
    flex-direction: column !important;
    gap: 0.4rem !important;
}
div[data-testid="stRadio"] > div > label {
    display: flex !important;
    align-items: flex-start !important;
    gap: 0.6rem !important;
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 7px !important;
    padding: 0.55rem 0.85rem !important;
    cursor: pointer !important;
    transition: border-color 0.15s, background 0.15s !important;
}
div[data-testid="stRadio"] > div > label:hover {
    border-color: var(--border-hi) !important;
    background: var(--surface2) !important;
}
div[data-testid="stRadio"] > div > label[data-checked="true"] {
    border-color: var(--blue) !important;
    background: var(--blue-glow) !important;
}
div[data-testid="stRadio"] > div > label > div:first-child {
    margin-top: 2px !important;
    flex-shrink: 0 !important;
}
div[data-testid="stRadio"] > div > label > div:first-child > div {
    width: 14px !important;
    height: 14px !important;
    border: 2px solid var(--border-hi) !important;
    border-radius: 50% !important;
    background: transparent !important;
}
div[data-testid="stRadio"] > div > label[data-checked="true"] > div:first-child > div {
    border-color: var(--blue) !important;
    background: var(--blue) !important;
    box-shadow: 0 0 0 3px var(--blue-glow) !important;
}
.opt-title {
    font-family: 'Inter Tight', sans-serif;
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--text) !important;
    line-height: 1.3;
}
.opt-desc {
    font-size: 0.68rem;
    color: var(--muted) !important;
    line-height: 1.4;
    margin-top: 1px;
}
</style>
""", unsafe_allow_html=True)

# ── Options layout ────────────────────────────────────────────
opt1, opt2, opt3 = st.columns([3, 2, 1.5])

with opt1:
    st.markdown('<div class="field-label">Comparison Focus</div>', unsafe_allow_html=True)
    focus_options = [
        "Comprehensive Assessment",
        "Key Differences & Similarities",
        "Risk & Compliance",
        "Tone & Writing Style",
        "Data & Numbers",
        "Agreements & Gaps",
        "Executive Summary",
        "Custom (describe below)",
    ]
    _focus_descs = {
        "Comprehensive Assessment":       "Full structured analysis across all dimensions",
        "Key Differences & Similarities": "What changed, what stayed the same",
        "Risk & Compliance":              "Obligations, gaps, and legal exposure",
        "Tone & Writing Style":           "Language, framing, and rhetorical approach",
        "Data & Numbers":                 "Every figure, metric, and statistic compared",
        "Agreements & Gaps":              "Where documents align and where they diverge",
        "Executive Summary":              "Tight briefing, top findings only",
        "Custom (describe below)":        "Define your own comparison focus",
    }
    focus = st.radio(
        "focus",
        focus_options,
        index=0,
        format_func=lambda x: x,
        label_visibility="collapsed",
        captions=[_focus_descs[o] for o in focus_options],
    )

with opt2:
    st.markdown('<div class="field-label">Output Tone</div>', unsafe_allow_html=True)
    tone_options = [
        "Analytical & detailed",
        "Executive brief",
        "Plain language",
        "Legal / formal",
    ]
    _tone_descs = {
        "Analytical & detailed": "Thorough, evidence-backed, fully structured",
        "Executive brief":       "Lead with the headline, 400–600 words max",
        "Plain language":        "Clear and jargon-free, for any audience",
        "Legal / formal":        "Precise, numbered sections, flags obligations",
    }
    tone = st.radio(
        "tone",
        tone_options,
        index=0,
        label_visibility="collapsed",
        captions=[_tone_descs[o] for o in tone_options],
    )

with opt3:
    st.markdown('<div class="field-label">&nbsp;</div>', unsafe_allow_html=True)
    compare_clicked = st.button(
        "COMPARE DOCUMENTS",
        disabled=not (file_a and file_b and claude_key and ANTHROPIC_AVAILABLE),
        width="stretch",
    )

model = "claude-sonnet-4-6"

# Custom focus text area (conditional)
custom_focus = ""
if focus == "Custom (describe below)":
    st.markdown('<div class="field-label" style="margin-top:.75rem;">Describe your comparison focus</div>', unsafe_allow_html=True)
    custom_focus = st.text_area(
        "custom_focus", label_visibility="collapsed",
        placeholder="e.g. Compare the pricing structures and payment terms in both documents...",
        height=80,
    )

st.markdown("</div>", unsafe_allow_html=True)  # close upload-block

# ─────────────────────────────────────────────────────────────
# MARKDOWN RENDER HELPER
# ─────────────────────────────────────────────────────────────

import re as _re

def _escape_dollars(text: str) -> str:
    """Escape bare $ signs so Streamlit doesn't treat them as LaTeX delimiters."""
    # Replace $ not already escaped, not inside code blocks
    return _re.sub(r'(?<!\\)\$', r'\\$', text)

# ─────────────────────────────────────────────────────────────
# COMPARISON LOGIC
# ─────────────────────────────────────────────────────────────

if compare_clicked and file_a and file_b:
    # Reset state for fresh comparison
    st.session_state.comparison_result = ""
    st.session_state.chat_history      = []
    st.session_state.chat_pending      = False

    with st.spinner("Extracting document contents…"):
        file_a.seek(0)
        text_a, type_a = extract_text(file_a)
        file_b.seek(0)
        text_b, type_b = extract_text(file_b)

    st.session_state.doc_a_text = text_a
    st.session_state.doc_b_text = text_b
    st.session_state.doc_a_name = file_a.name
    st.session_state.doc_b_name = file_b.name
    st.session_state.last_focus = focus
    st.session_state.last_tone  = tone

    # Build prompt
    actual_focus = custom_focus.strip() if focus == "Custom (describe below)" and custom_focus.strip() else focus

    focus_instructions = {
        "Comprehensive Assessment": """Deliver a full, structured comparison across every meaningful dimension:

## 1. Most Significant Differences
Identify and explain the 4-6 most impactful differences between the documents. For each: state what changed, quote the specific language from both documents, and explain the significance.

## 2. Numerical & Data Comparison
List every figure, metric, date, percentage, and statistic that appears in both documents. Present them in a table (Metric | Document A | Document B | Delta). Flag any discrepancies or contradictions.

## 3. Comprehensiveness Assessment
Which document is more complete? For each major topic area, state whether Document A, Document B, or both cover it — and note anything present in one that is entirely absent from the other.

## 4. Tone & Framing
How does the language and framing differ? Note any tonal shifts, changes in confidence or hedging, or differences in how key facts are presented.

## 5. Agreements & Alignment
Where do the documents agree, reinforce, or directly echo each other? Quote matching language where relevant.

## 6. Summary Verdict
One paragraph: which document is more authoritative / complete / reliable, and why? What is the single most important thing a reader should know about the difference between these two documents?

Be exhaustive. Quote directly. Use tables for any comparative data.""",

        "Key Differences & Similarities": """Compare the two documents thoroughly:
1. List the 5-7 most significant differences — be specific, cite sections or values
2. List 3-5 meaningful similarities or areas of alignment
3. Which document is more comprehensive, and in what respects?
4. Are there any contradictions or conflicts between the documents?
5. What is the most critical difference a decision-maker should know about?""",

        "Risk & Compliance": """Analyse both documents from a risk and compliance perspective:
1. Identify all risk-related clauses, obligations, or statements in each document
2. Compare the risk profiles — which document carries more risk and for whom?
3. Highlight any compliance gaps, missing protections, or ambiguous language
4. Flag any terms that could be problematic legally or operationally
5. What are the top 3 risk differences between the documents?""",

        "Tone & Writing Style": """Compare the writing style and tone of both documents:
1. Describe the overall tone of each (formal/informal, assertive/hedging, technical/plain)
2. Compare complexity: readability, sentence structure, jargon density
3. How does the framing of key topics differ between documents?
4. Which document is more persuasive, and what techniques does it use?
5. Are there notable differences in how uncertainty or caveats are expressed?""",

        "Data & Numbers": """Extract and compare all numerical content:
1. List all key figures, statistics, dates, percentages and metrics from each document
2. Where the same metric appears in both, compare the values — are they consistent?
3. Identify discrepancies or contradictions in numerical data
4. Which document provides more quantitative evidence, and is it more credible?
5. Summarise the financial or quantitative picture each document paints""",

        "Agreements & Gaps": """Map the alignment and divergence between both documents:
1. Where do the documents agree or reinforce each other? Quote specific language
2. Where do they diverge — is it in scope, terms, assumptions, or conclusions?
3. What topics does one document address that the other ignores?
4. Are there any direct contradictions that need to be resolved?
5. If these documents were to be reconciled into one, what would be the sticking points?""",

        "Executive Summary": """Provide a tight executive briefing:
1. One-sentence summary of each document's purpose
2. The 3 most important differences — lead with the highest-stakes one
3. The 3 strongest points of alignment
4. Bottom-line recommendation: how should a decision-maker use these documents together?
Keep it under 500 words. Every sentence must earn its place.""",
    }

    focus_text = focus_instructions.get(actual_focus, f"""Compare the documents with this specific focus: {actual_focus}

Provide a thorough, structured analysis addressing the user's stated focus. Use concrete evidence from the documents — quote specific language, cite figures, and name sections. Be direct and analytical.""")

    tone_map = {
        "Analytical & detailed":
            "Write in a precise, analytical tone. Use structured headers and sub-points. Support every claim with specific evidence from the documents. Be thorough.",
        "Executive brief":
            "Write as a concise executive briefing. Lead with the single most important finding. Use headers and bullets. Total length: 400-600 words max.",
        "Plain language":
            "Write in plain, accessible language. Avoid jargon. Explain any technical terms. Aim for clarity over comprehensiveness.",
        "Legal / formal":
            "Write in formal, precise language suitable for legal or contractual review. Use structured numbered sections. Flag ambiguities and obligations explicitly.",
    }

    _xlsx_rule = ""
    if type_a == "xlsx" or type_b == "xlsx":
        _xlsx_rule = "\n- EXCEL FILES: For every difference found in a spreadsheet, state the exact sheet name and cell reference (e.g. Sheet1!B4, Financial Model!C12). Do not describe a change without citing its precise location."

    prompt = f"""You are a senior document analyst. You will compare two documents in depth.

═══════════════════════════════════
DOCUMENT A: {file_a.name}
═══════════════════════════════════
{truncate(text_a)}

═══════════════════════════════════
DOCUMENT B: {file_b.name}
═══════════════════════════════════
{truncate(text_b)}

═══════════════════════════════════
YOUR TASK
═══════════════════════════════════
{focus_text}

OUTPUT TONE: {tone_map.get(tone, tone_map["Analytical & detailed"])}

HARD RULES:
- Every observation must be grounded in specific content from the documents
- Quote directly from the documents when making claims about language or tone
- Use clear markdown headers (##) for sections
- Do NOT attempt to find explanations or give suggestions to the user regarding what was changed
- Do not add generic preamble or sign-off — go straight into the analysis{_xlsx_rule}"""

    # Stream the response
    st.markdown('<div class="section-header"><span class="dot"></span>COMPARISON RESULT</div>', unsafe_allow_html=True)
    result_placeholder = st.empty()
    full_text = ""

    try:
        client = _anthropic.Anthropic(api_key=claude_key)
        with client.messages.stream(
            model=model,
            max_tokens=4096,
            system=(
                "You are a senior document analyst. "
                "Respond only with your analysis in well-structured markdown. "
                "No preamble, no sign-off. "
                "IMPORTANT FORMATTING RULES: "
                "1. Use **bold** only for standalone words or short phrases — never wrap text containing $, numbers, or punctuation in * or ** as this breaks rendering. "
                "2. When quoting values or figures (e.g. $49.6M), write them as plain text, not inside asterisks. "
                "3. For inline quotes from documents use double quotes (\") not asterisk-italic. "
                "4. Use ## for section headers and ### for sub-headers. "
                "5. Use markdown tables for any comparative data."
            ),
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for delta in stream.text_stream:
                full_text += delta
                result_placeholder.markdown(_escape_dollars(full_text) + "▌")

        result_placeholder.markdown(_escape_dollars(full_text))
        st.session_state.comparison_result = full_text

    except _anthropic.AuthenticationError:
        st.error("Invalid Anthropic API key — check your secrets.toml.")
    except _anthropic.RateLimitError:
        st.error("Rate limit reached. Wait a moment and try again.")
    except _anthropic.APIConnectionError as e:
        st.error(f"Could not reach the Anthropic API. Check your internet connection.\nDetail: {e}")
    except Exception as e:
        st.error(f"Unexpected error: {type(e).__name__}: {e}")

# ─────────────────────────────────────────────────────────────
# RESULTS PANEL (persisted from previous run)
# ─────────────────────────────────────────────────────────────

elif st.session_state.comparison_result:
    st.markdown('<div class="section-header"><span class="dot"></span>COMPARISON RESULT</div>', unsafe_allow_html=True)
    st.markdown(_escape_dollars(st.session_state.comparison_result))

# ─────────────────────────────────────────────────────────────
# DOWNLOAD + CHAT (shown when result exists)
# ─────────────────────────────────────────────────────────────

if st.session_state.comparison_result:
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Downloads ─────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:.62rem;font-weight:700;letter-spacing:.18em;'
        'text-transform:uppercase;color:var(--muted);margin-bottom:.5rem;">'
        'DOWNLOAD REPORT</div>',
        unsafe_allow_html=True,
    )
    _dl1, _dl2, _dl3 = st.columns([1, 1, 1])
    _fname = f"comparison_{st.session_state.doc_a_name[:20]}_{st.session_state.doc_b_name[:20]}".replace(" ", "_")

    with _dl1:
        st.download_button(
            "⬇ Markdown (.md)",
            data=st.session_state.comparison_result,
            file_name=f"{_fname}.md",
            mime="text/markdown",
            width="stretch",
            key="dl_md",
        )

    with _dl2:
        try:
            import markdown as _mdlib
            _html_body = _mdlib.markdown(
                st.session_state.comparison_result,
                extensions=["extra", "nl2br", "tables"]
            )
        except ImportError:
            import re as _re
            _html_body = st.session_state.comparison_result.replace("\n", "<br>")
        _html_doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<title>Document Comparison</title>
<style>
body{{font-family:'Segoe UI',Arial,sans-serif;max-width:860px;margin:40px auto;padding:0 24px;color:#1a1a2e;line-height:1.7;}}
h1{{font-size:1.7rem;color:#1e3a8a;margin-top:2rem;}}
h2{{font-size:1.35rem;color:#1e3a8a;margin-top:1.8rem;border-left:4px solid #3b82f6;padding-left:.6rem;}}
h3{{font-size:1.1rem;color:#1e40af;margin-top:1.3rem;}}
p{{margin:.6rem 0 1rem;}}ul,ol{{margin:.4rem 0 1rem 1.4rem;}}
li{{margin-bottom:.3rem;}}strong{{color:#0f172a;font-weight:700;}}
table{{border-collapse:collapse;width:100%;margin:1rem 0;}}
th{{background:#1e3a8a;color:#fff;padding:8px 12px;text-align:left;}}
td{{padding:7px 12px;border:1px solid #dde;}}
tr:nth-child(even){{background:#f0f4ff;}}
.header{{background:linear-gradient(135deg,#1e3a8a,#1d4ed8);color:#fff;padding:2rem 2.5rem;border-radius:8px;margin-bottom:2rem;}}
.header h1{{color:#fff;font-size:1.5rem;margin:0 0 .3rem;border:none;}}
.header p{{color:rgba(255,255,255,.75);margin:0;font-size:.88rem;}}
</style></head><body>
<div class="header">
  <h1>Document Comparison Report</h1>
  <p>{st.session_state.doc_a_name}  ⇄  {st.session_state.doc_b_name}</p>
</div>
{_html_body}
</body></html>"""
        st.download_button(
            "⬇ HTML (.html)",
            data=_html_doc.encode("utf-8"),
            file_name=f"{_fname}.html",
            mime="text/html",
            width="stretch",
            key="dl_html",
        )

    with _dl3:
        def _make_pdf(md_text, doc_a, doc_b):
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import cm
                from reportlab.lib import colors
                from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                                HRFlowable, Table, TableStyle)
                from reportlab.lib.enums import TA_LEFT, TA_CENTER
                import io as _io, re as _re

                buf = _io.BytesIO()
                doc = SimpleDocTemplate(buf, pagesize=letter,
                    leftMargin=2*cm, rightMargin=2*cm,
                    topMargin=2*cm, bottomMargin=2*cm)

                styles = getSampleStyleSheet()
                s_h1   = ParagraphStyle("h1", parent=styles["Normal"],
                    fontSize=14, fontName="Helvetica-Bold", spaceBefore=14,
                    spaceAfter=4, textColor=colors.HexColor("#1e3a8a"))
                s_h2   = ParagraphStyle("h2", parent=styles["Normal"],
                    fontSize=12, fontName="Helvetica-Bold", spaceBefore=10,
                    spaceAfter=3, textColor=colors.HexColor("#1e40af"))
                s_h3   = ParagraphStyle("h3", parent=styles["Normal"],
                    fontSize=11, fontName="Helvetica-Bold", spaceBefore=8,
                    spaceAfter=2, textColor=colors.HexColor("#374151"))
                s_body = ParagraphStyle("body", parent=styles["Normal"],
                    fontSize=9.5, fontName="Helvetica", leading=14, spaceAfter=5)
                s_bull = ParagraphStyle("bull", parent=s_body,
                    leftIndent=14, bulletIndent=4)
                s_note = ParagraphStyle("note", parent=styles["Normal"],
                    fontSize=8, fontName="Helvetica-Oblique",
                    textColor=colors.HexColor("#6b7280"))

                def inline(text):
                    # Convert **bold** and *italic* to reportlab tags
                    text = _re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
                    text = _re.sub(r'\*(.+?)\*',     r'<i>\1</i>', text)
                    text = _re.sub(r'`(.+?)`', r'<font name="Courier">\1</font>', text)
                    return text

                story = []

                # Header banner
                hdr_data = [[
                    Paragraph('<b><font color="white" size="14">Document Comparison Report</font></b>', styles["Normal"]),
                ],[
                    Paragraph(f'<font color="#cbd5e1" size="9">{doc_a}  ⇄  {doc_b}</font>', styles["Normal"]),
                ]]
                hdr_tbl = Table(hdr_data, colWidths=["100%"])
                hdr_tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#1e3a8a")),
                    ("TOPPADDING",    (0,0), (-1,-1), 10),
                    ("BOTTOMPADDING",(0,0), (-1,-1), 10),
                    ("LEFTPADDING",  (0,0), (-1,-1), 14),
                    ("RIGHTPADDING", (0,0), (-1,-1), 14),
                    ("ROUNDEDCORNERS", [6]),
                ]))
                story.append(hdr_tbl)
                story.append(Spacer(1, 14))

                lines = md_text.split("\n")
                i = 0
                while i < len(lines):
                    line = lines[i]

                    # Table detection
                    if "|" in line and i + 1 < len(lines) and "|" in lines[i+1] and "---" in lines[i+1]:
                        tbl_lines = []
                        while i < len(lines) and "|" in lines[i]:
                            tbl_lines.append(lines[i])
                            i += 1
                        # Parse rows (skip separator)
                        rows = []
                        for tl in tbl_lines:
                            if _re.match(r"^\s*\|[-: |]+\|\s*$", tl):
                                continue
                            cells = [c.strip() for c in tl.strip().strip("|").split("|")]
                            rows.append(cells)
                        if rows:
                            max_cols = max(len(r) for r in rows)
                            for r in rows:
                                while len(r) < max_cols: r.append("")
                            col_w = (17 * cm) / max_cols
                            para_rows = []
                            for ri, row in enumerate(rows):
                                para_row = []
                                for ci, cell in enumerate(row):
                                    txt = inline(cell)
                                    sty = ParagraphStyle("tc",
                                        parent=styles["Normal"],
                                        fontSize=8.5, fontName="Helvetica-Bold" if ri==0 else "Helvetica",
                                        textColor=colors.white if ri==0 else colors.HexColor("#1a1a2e"),
                                        leading=12)
                                    para_row.append(Paragraph(txt, sty))
                                para_rows.append(para_row)
                            t = Table(para_rows, colWidths=[col_w]*max_cols)
                            t.setStyle(TableStyle([
                                ("BACKGROUND",    (0,0), (-1,0),  colors.HexColor("#1e3a8a")),
                                ("BACKGROUND",    (0,1), (-1,-1), colors.white),
                                ("ROWBACKGROUNDS",(0,1), (-1,-1),
                                 [colors.HexColor("#f0f4ff"), colors.white]),
                                ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#c7d2fe")),
                                ("TOPPADDING",    (0,0), (-1,-1), 4),
                                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                                ("LEFTPADDING",   (0,0), (-1,-1), 6),
                                ("RIGHTPADDING",  (0,0), (-1,-1), 6),
                            ]))
                            story.append(t)
                            story.append(Spacer(1, 6))
                        continue

                    if line.startswith("### "):
                        story.append(Paragraph(inline(line[4:]), s_h3))
                    elif line.startswith("## "):
                        story.append(HRFlowable(width="100%", thickness=0.5,
                            color=colors.HexColor("#c7d2fe"), spaceAfter=2))
                        story.append(Paragraph(inline(line[3:]), s_h2))
                    elif line.startswith("# "):
                        story.append(Paragraph(inline(line[2:]), s_h1))
                    elif line.startswith("- ") or line.startswith("* "):
                        story.append(Paragraph("• " + inline(line[2:]), s_bull))
                    elif _re.match(r"^\d+\.\s", line):
                        txt = _re.sub(r"^\d+\.\s*", "", line)
                        story.append(Paragraph("• " + inline(txt), s_bull))
                    elif line.strip() == "" or line.strip() == "---":
                        story.append(Spacer(1, 4))
                    else:
                        story.append(Paragraph(inline(line), s_body))
                    i += 1

                doc.build(story)
                return buf.getvalue()
            except Exception as e:
                return None

        _pdf_bytes = _make_pdf(
            st.session_state.comparison_result,
            st.session_state.doc_a_name,
            st.session_state.doc_b_name,
        )
        if _pdf_bytes:
            st.download_button(
                "⬇ PDF (.pdf)",
                data=_pdf_bytes,
                file_name=f"{_fname}.pdf",
                mime="application/pdf",
                width="stretch",
                key="dl_pdf",
            )
        else:
            st.warning("PDF generation failed — install `reportlab`")

    # ── Follow-up Chat ────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div class="section-header"><span class="dot"></span>FOLLOW-UP CHAT'
        '<span style="color:var(--muted);font-size:.7rem;font-weight:400;"> '
        '— ask Claude anything about these documents</span></div>',
        unsafe_allow_html=True,
    )

    def _build_chat_system():
        return f"""You are a senior document analyst. You have already compared two documents and produced a report. The user wants to ask follow-up questions.

DOCUMENT A ({st.session_state.doc_a_name}):
{truncate(st.session_state.doc_a_text, 15000)}

DOCUMENT B ({st.session_state.doc_b_name}):
{truncate(st.session_state.doc_b_text, 15000)}

COMPARISON REPORT ALREADY PRODUCED:
{st.session_state.comparison_result[:3000]}{"…[truncated]" if len(st.session_state.comparison_result) > 3000 else ""}

Answer follow-up questions concisely and specifically. Reference the actual document content. Use markdown where it adds clarity. Do not wrap text containing $, numbers, or punctuation inside * or ** — write figures as plain text and use double quotes for inline document quotes."""

    # Render chat history
    for _msg in st.session_state.chat_history:
        with st.chat_message(_msg["role"]):
            st.markdown(_escape_dollars(_msg["content"]))

    # Stream pending reply
    if st.session_state.chat_pending and claude_key:
        st.session_state.chat_pending = False
        _api_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_history
        ]
        try:
            _chat_client = _anthropic.Anthropic(api_key=claude_key)
            with st.chat_message("assistant"):
                _reply = ""
                _ph    = st.empty()
                with _chat_client.messages.stream(
                    model=model,
                    max_tokens=2048,
                    system=_build_chat_system(),
                    messages=_api_messages,
                ) as _stream:
                    for _delta in _stream.text_stream:
                        _reply += _delta
                        _ph.markdown(_escape_dollars(_reply) + "▌")
                _ph.markdown(_escape_dollars(_reply))
            st.session_state.chat_history.append({"role": "assistant", "content": _reply})
        except _anthropic.AuthenticationError:
            st.error("Invalid API key.")
        except _anthropic.RateLimitError:
            st.error("Rate limit reached. Wait a moment and try again.")
        except Exception as _e:
            st.error(f"Chat error: {type(_e).__name__}: {_e}")

    # Chat input
    _user_msg = st.chat_input("Ask a question about the documents…", key="chat_input")
    if _user_msg:
        st.session_state.chat_history.append({"role": "user", "content": _user_msg})
        st.session_state.chat_pending = True
        st.rerun()

    # Clear chat
    if st.session_state.chat_history:
        if st.button("Clear chat history", key="clear_chat"):
            st.session_state.chat_history = []
            st.session_state.chat_pending = False
            st.rerun()

# ─────────────────────────────────────────────────────────────
# EMPTY STATE
# ─────────────────────────────────────────────────────────────

elif not (file_a and file_b):
    st.markdown("""
<div class="empty-state">
  <div class="empty-title">UPLOAD TWO DOCUMENTS</div>
  <div class="empty-sub">
    Drop a PDF, DOCX, or XLSX into each slot above, choose your comparison focus,
    then click <strong style="color:var(--blue);">Compare Documents</strong>.
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="footer">
  <div class="footer-brand">SEGA DOC COMPARATOR</div>
  <div class="footer-note">Powered by Claude · Documents processed locally · Internal use only</div>
</div>
""", unsafe_allow_html=True)