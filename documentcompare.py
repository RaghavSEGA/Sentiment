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

/* FOCUS CHIP ROW */
.focus-chip > button {
    background: var(--surface) !important; color: var(--text-dim) !important;
    border: 1px solid var(--border) !important; border-radius: 6px !important;
    font-family: 'Inter Tight', sans-serif !important; font-size: .78rem !important;
    font-weight: 700 !important; letter-spacing: .1em !important; text-transform: uppercase !important;
    padding: .4rem 1.1rem !important; min-height: unset !important; height: auto !important;
    line-height: 1.5 !important; transition: border-color .15s, color .15s, background .15s !important;
    box-shadow: none !important; width: 100% !important;
}
.focus-chip > button:hover { background: var(--surface2) !important; border-color: var(--blue) !important; color: var(--text) !important; transform: none !important; box-shadow: none !important; }

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
                lines.append(f"[Sheet: {sheet.title}]")
                for row in sheet.iter_rows(values_only=True):
                    cells = [str(c) if c is not None else "" for c in row]
                    if any(c.strip() for c in cells):
                        lines.append("\t".join(cells))
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
# QUICK FOCUS CHIPS
# ─────────────────────────────────────────────────────────────

QUICK_FOCUSES = ["Key Differences", "Risk & Compliance", "Tone & Style", "Data & Numbers", "Agreements & Gaps"]

st.markdown('<div style="margin-bottom:.35rem;font-size:.6rem;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--muted);">Quick focus</div>', unsafe_allow_html=True)
_chip_cols = st.columns(len(QUICK_FOCUSES))
_chip_clicked = None
for _ci, _label in enumerate(QUICK_FOCUSES):
    with _chip_cols[_ci]:
        st.markdown('<div class="focus-chip">', unsafe_allow_html=True)
        if st.button(_label, key=f"chip_{_ci}"):
            _chip_clicked = _label
        st.markdown('</div>', unsafe_allow_html=True)

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

# ── Options row ───────────────────────────────────────────────
opt1, opt2 = st.columns([3, 2])

with opt1:
    st.markdown('<div class="field-label">Comparison Focus</div>', unsafe_allow_html=True)
    focus_options = [
        "Key Differences & Similarities",
        "Risk & Compliance",
        "Tone & Writing Style",
        "Data & Numbers",
        "Agreements & Gaps",
        "Executive Summary",
        "Custom (describe below)",
    ]
    # Pre-fill from chip click
    _focus_idx = 0
    if _chip_clicked:
        _label_map = {
            "Key Differences":    "Key Differences & Similarities",
            "Risk & Compliance":  "Risk & Compliance",
            "Tone & Style":       "Tone & Writing Style",
            "Data & Numbers":     "Data & Numbers",
            "Agreements & Gaps":  "Agreements & Gaps",
        }
        _mapped = _label_map.get(_chip_clicked, "")
        if _mapped in focus_options:
            _focus_idx = focus_options.index(_mapped)

    focus = st.selectbox("focus", focus_options, index=_focus_idx, label_visibility="collapsed")

with opt2:
    st.markdown('<div class="field-label">Output Tone</div>', unsafe_allow_html=True)
    tone = st.selectbox("tone", [
        "Analytical & detailed",
        "Executive brief",
        "Plain language",
        "Legal / formal",
    ], label_visibility="collapsed")

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

st.markdown("<br>", unsafe_allow_html=True)
btn_col, _ = st.columns([1, 5])
with btn_col:
    compare_clicked = st.button(
        "COMPARE DOCUMENTS",
        disabled=not (file_a and file_b and claude_key and ANTHROPIC_AVAILABLE),
        width="stretch",
    )

st.markdown("</div>", unsafe_allow_html=True)  # close upload-block

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
- Do not add generic preamble or sign-off — go straight into the analysis"""

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
                "No preamble, no sign-off."
            ),
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for delta in stream.text_stream:
                full_text += delta
                result_placeholder.markdown(
                    f'<div class="result-card">{full_text}▌</div>',
                    unsafe_allow_html=True,
                )

        result_placeholder.markdown(
            f'<div class="result-card">{full_text}</div>',
            unsafe_allow_html=True,
        )
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
    st.markdown(
        f'<div class="result-card">{st.session_state.comparison_result}</div>',
        unsafe_allow_html=True,
    )

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
    _dl1, _dl2, _ = st.columns([1, 1, 4])
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
        _html_body = st.session_state.comparison_result.replace("\n", "<br>")
        _html_doc  = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<title>Document Comparison</title>
<style>
body{{font-family:'Segoe UI',Arial,sans-serif;max-width:860px;margin:40px auto;padding:0 24px;color:#1a1a2e;line-height:1.7;}}
h2{{font-size:1.35rem;color:#1e3a8a;margin-top:1.8rem;border-left:4px solid #3b82f6;padding-left:.6rem;}}
h3{{font-size:1.1rem;color:#1e40af;margin-top:1.3rem;}}
p{{margin:.6rem 0 1rem;}} ul,ol{{margin:.4rem 0 1rem 1.4rem;}}
li{{margin-bottom:.3rem;}} strong{{color:#0f172a;}}
.header{{background:linear-gradient(135deg,#1e3a8a,#1d4ed8);color:#fff;padding:2rem 2.5rem;border-radius:8px;margin-bottom:2rem;}}
.header h1{{color:#fff;font-size:1.5rem;margin:0 0 .3rem;}}
.header p{{color:rgba(255,255,255,.75);margin:0;font-size:.88rem;}}
</style></head><body>
<div class="header">
  <h1>Document Comparison Report</h1>
  <p>{st.session_state.doc_a_name}  ⇄  {st.session_state.doc_b_name}</p>
</div>
{st.session_state.comparison_result}
</body></html>"""
        st.download_button(
            "⬇ HTML (.html)",
            data=_html_doc.encode("utf-8"),
            file_name=f"{_fname}.html",
            mime="text/html",
            width="stretch",
            key="dl_html",
        )

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

Answer follow-up questions concisely and specifically. Reference the actual document content. Use markdown where it adds clarity."""

    # Render chat history
    for _msg in st.session_state.chat_history:
        with st.chat_message(_msg["role"]):
            st.markdown(_msg["content"])

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
                        _ph.markdown(_reply + "▌")
                _ph.markdown(_reply)
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