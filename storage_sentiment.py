"""
storage_sentiment.py — Postgres-backed persistence for the Sentiment Analysis Studio.

Connection is via DATABASE_URL in st.secrets (standard Postgres DSN).

Example secrets.toml entry:
    DATABASE_URL = "postgresql://user:password@host:5432/dbname"

On Supabase: use the Session mode connection string from
Settings → Database → Connection string → URI  (port 5432, NOT 6543).

Install dependency (use the binary wheel — no pg_config / libpq-dev required):
    pip install psycopg2-binary

Run this SQL once in your database before first use:

    CREATE TABLE IF NOT EXISTS sentiment_projects (
        owner        TEXT        NOT NULL,
        name         TEXT        NOT NULL,
        doc_names    JSONB       DEFAULT '[]',
        col_config   JSONB       DEFAULT '{}',
        results_json JSONB       DEFAULT '{}',
        chat_history JSONB       DEFAULT '[]',
        updated_at   TIMESTAMPTZ DEFAULT NOW(),
        PRIMARY KEY (owner, name)
    );
    CREATE INDEX IF NOT EXISTS idx_sentiment_projects_owner
        ON sentiment_projects (owner);

Column reference
────────────────
owner        — authenticated user email (from OTP auth)
name         — project name, chosen by user
doc_names    — JSON list of uploaded file names belonging to this project
col_config   — JSON dict mapping filename → chosen text column + batch size
               e.g. {"myfile.xlsx": {"col": "Title", "batch": 20}}
results_json — JSON dict mapping filename → list of per-row sentiment dicts
               (same structure as the analysed_dfs DataFrames, serialised)
chat_history — JSON list of {"role": "user"|"assistant", "content": "..."} dicts
updated_at   — auto-updated timestamp on every save
"""

import json
import streamlit as st
from contextlib import contextmanager

# psycopg2-binary ships its own libpq and requires no system pg_config.
# Fall back to the source build (psycopg2) if somehow only that is installed.
try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    raise ImportError(
        "psycopg2-binary is required. Install it with:\n"
        "    pip install psycopg2-binary"
    )


# ── Connection ────────────────────────────────────────────────────────────────

@contextmanager
def _get_conn():
    url = st.secrets.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "DATABASE_URL not set in secrets.toml.\n"
            "Add: DATABASE_URL = \"postgresql://user:pass@host:5432/dbname\""
        )
    conn = psycopg2.connect(
        url,
        sslmode="require",
        options="-c statement_timeout=30000",
    )
    conn.autocommit = False
    psycopg2.extras.register_default_jsonb(conn)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db():
    """Create the sentiment_projects table and index if they do not exist."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sentiment_projects (
                    owner        TEXT        NOT NULL,
                    name         TEXT        NOT NULL,
                    doc_names    JSONB       DEFAULT '[]',
                    col_config   JSONB       DEFAULT '{}',
                    results_json JSONB       DEFAULT '{}',
                    chat_history JSONB       DEFAULT '[]',
                    updated_at   TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (owner, name)
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_sentiment_projects_owner
                ON sentiment_projects (owner)
            """)


# ── Project listing ───────────────────────────────────────────────────────────

def get_projects(owner: str) -> list:
    """
    Return a list of project summary dicts for the given owner, ordered by name.
    Each dict contains: name, doc_names, updated_at (ISO string).
    """
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT name, doc_names, updated_at
                   FROM sentiment_projects
                   WHERE owner = %s
                   ORDER BY name""",
                (owner,),
            )
            return [
                {
                    **dict(r),
                    "updated_at": r["updated_at"].isoformat() if r["updated_at"] else "",
                }
                for r in cur.fetchall()
            ]


def project_exists(owner: str, name: str) -> bool:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM sentiment_projects WHERE owner = %s AND name = %s",
                (owner, name),
            )
            return cur.fetchone() is not None


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_project(owner: str, name: str):
    """Insert a new empty project row. Silently ignores duplicates."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO sentiment_projects (owner, name)
                   VALUES (%s, %s)
                   ON CONFLICT DO NOTHING""",
                (owner, name),
            )


def rename_project(owner: str, old_name: str, new_name: str):
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE sentiment_projects
                   SET name = %s, updated_at = NOW()
                   WHERE owner = %s AND name = %s""",
                (new_name, owner, old_name),
            )


def delete_project(owner: str, name: str):
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM sentiment_projects WHERE owner = %s AND name = %s",
                (owner, name),
            )


# ── Load / Save ───────────────────────────────────────────────────────────────

def load_project(owner: str, name: str) -> dict | None:
    """
    Load a project's full state.
    Returns a dict with keys:
        doc_names    — list of file names
        col_config   — dict of {filename: {col, batch}}
        results_json — dict of {filename: list[row_dict]}
        chat_history — list of {role, content} dicts
    Returns None if the project does not exist.
    """
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT doc_names, col_config, results_json, chat_history
                   FROM sentiment_projects
                   WHERE owner = %s AND name = %s""",
                (owner, name),
            )
            row = cur.fetchone()

    if not row:
        return None

    return {
        "doc_names":    row["doc_names"]    or [],
        "col_config":   row["col_config"]   or {},
        "results_json": row["results_json"] or {},
        "chat_history": row["chat_history"] or [],
    }


def save_project(
    owner: str,
    name: str,
    doc_names: list | None = None,
    col_config: dict | None = None,
    results_json: dict | None = None,
    chat_history: list | None = None,
):
    """
    Upsert all project fields.
    Passing None for any argument preserves the existing DB value via COALESCE.
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sentiment_projects
                    (owner, name, doc_names, col_config, results_json,
                     chat_history, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (owner, name) DO UPDATE SET
                    doc_names    = COALESCE(EXCLUDED.doc_names,
                                            sentiment_projects.doc_names),
                    col_config   = COALESCE(EXCLUDED.col_config,
                                            sentiment_projects.col_config),
                    results_json = COALESCE(EXCLUDED.results_json,
                                            sentiment_projects.results_json),
                    chat_history = COALESCE(EXCLUDED.chat_history,
                                            sentiment_projects.chat_history),
                    updated_at   = NOW()
            """, (
                owner,
                name,
                json.dumps(doc_names)    if doc_names    is not None else None,
                json.dumps(col_config)   if col_config   is not None else None,
                json.dumps(results_json) if results_json is not None else None,
                json.dumps(chat_history) if chat_history is not None else None,
            ))