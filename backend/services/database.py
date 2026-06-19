"""
SQLite persistence for Business Forensics AI.
Stores every analysis: status, profile, full JSON report, timestamps.
Thread-safe via a module-level lock (FastAPI runs background tasks in a thread pool).
"""
import sqlite3
import json
import threading
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path


# Database file location — resolved at startup:
# 1. BF_DB_PATH env var (explicit override)
# 2. backend/data/analyses.db (default, works on Windows/Mac/Linux)
# 3. /tmp/bf_analyses.db (fallback if backend dir isn't writable, e.g. network mount)
def _resolve_db_path() -> Path:
    if os.environ.get("BF_DB_PATH"):
        return Path(os.environ["BF_DB_PATH"])
    # Default: sibling data/ folder next to services/
    default = Path(__file__).parent.parent / "data" / "analyses.db"
    try:
        default.parent.mkdir(parents=True, exist_ok=True)
        # Quick write-test
        test = default.parent / ".write_test"
        test.write_text("ok")
        test.unlink()
        return default
    except OSError:
        # Network mount or read-only filesystem — use temp dir
        return Path("/tmp/bf_analyses.db")

_DB_PATH = _resolve_db_path()
_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    """Return a connection with row_factory set for dict-like access."""
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist. Call once at startup."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        conn = _get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id              TEXT PRIMARY KEY,
                    company_name    TEXT,
                    industry_key    TEXT,
                    annual_revenue  REAL,
                    headcount       INTEGER,
                    currency        TEXT,
                    country         TEXT,
                    primary_concern TEXT,
                    status          TEXT    NOT NULL DEFAULT 'processing',
                    error           TEXT,
                    report_json     TEXT,
                    created_at      TEXT    NOT NULL,
                    completed_at    TEXT,
                    file_count      INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analyses_status
                ON analyses (status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analyses_created
                ON analyses (created_at DESC)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS shares (
                    token       TEXT PRIMARY KEY,
                    analysis_id TEXT NOT NULL,
                    expires_at  TEXT,
                    revoked     INTEGER NOT NULL DEFAULT 0,
                    created_at  TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()


def create_analysis(analysis_id: str, profile: dict, file_count: int = 0):
    """Insert a new analysis record in 'processing' state."""
    now = _utcnow()
    with _lock:
        conn = _get_conn()
        try:
            conn.execute("""
                INSERT OR IGNORE INTO analyses
                    (id, company_name, industry_key, annual_revenue,
                     headcount, currency, country, primary_concern,
                     status, created_at, file_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'processing', ?, ?)
            """, (
                analysis_id,
                profile.get("company_name", "Unknown"),
                profile.get("industry_key", "general"),
                float(profile.get("annual_revenue") or 0),
                int(profile.get("headcount") or 0),
                profile.get("currency", "ZAR"),
                profile.get("country", ""),
                profile.get("primary_concern", ""),
                now,
                file_count,
            ))
            conn.commit()
        finally:
            conn.close()


def save_report(analysis_id: str, report: dict):
    """Persist the completed report JSON and mark status = complete."""
    now = _utcnow()
    report_str = json.dumps(report, ensure_ascii=False)
    with _lock:
        conn = _get_conn()
        try:
            conn.execute("""
                UPDATE analyses
                SET status = 'complete',
                    report_json = ?,
                    completed_at = ?,
                    error = NULL
                WHERE id = ?
            """, (report_str, now, analysis_id))
            conn.commit()
        finally:
            conn.close()


def save_error(analysis_id: str, error: str):
    """Mark an analysis as failed and store the error message."""
    now = _utcnow()
    with _lock:
        conn = _get_conn()
        try:
            conn.execute("""
                UPDATE analyses
                SET status = 'error',
                    error = ?,
                    completed_at = ?
                WHERE id = ?
            """, (error[:2000], now, analysis_id))
            conn.commit()
        finally:
            conn.close()


def create_share(analysis_id: str, expires_at: str | None = None) -> str:
    """Create an opaque public share token for an analysis (optional ISO expiry)."""
    token = secrets.token_urlsafe(16)
    now = _utcnow()
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                "INSERT INTO shares (token, analysis_id, expires_at, revoked, created_at) "
                "VALUES (?, ?, ?, 0, ?)", (token, analysis_id, expires_at, now))
            conn.commit()
        finally:
            conn.close()
    return token


def resolve_share(token: str) -> str | None:
    """Return the analysis_id for a VALID share (exists, not revoked, not expired), else None."""
    with _lock:
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT analysis_id, expires_at, revoked FROM shares WHERE token = ?",
                (token,)).fetchone()
        finally:
            conn.close()
    if row is None or row["revoked"]:
        return None
    exp = row["expires_at"]
    if exp:
        try:
            if datetime.now(timezone.utc) > datetime.fromisoformat(exp):
                return None
        except Exception:
            pass
    return row["analysis_id"]


def revoke_share(token: str) -> bool:
    """Revoke a share token so its public link stops working. Returns True if a row changed."""
    with _lock:
        conn = _get_conn()
        try:
            cur = conn.execute("UPDATE shares SET revoked = 1 WHERE token = ?", (token,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def mark_interrupted_analyses() -> int:
    """Flag analyses still in 'processing' (orphaned by a server restart) as errored,
    so the frontend gets a clear state instead of polling a job that no longer exists.
    Call once at startup. Returns the number of rows updated."""
    now = _utcnow()
    with _lock:
        conn = _get_conn()
        try:
            cur = conn.execute(
                "UPDATE analyses SET status='error', "
                "error='Analysis was interrupted by a server restart. Please run it again.', "
                "completed_at=? WHERE status='processing'", (now,))
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()


def get_analysis(analysis_id: str) -> dict | None:
    """Return a single analysis row as a dict, or None if not found."""
    with _lock:
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM analyses WHERE id = ?", (analysis_id,)
            ).fetchone()
            if row is None:
                return None
            return _row_to_dict(row)
        finally:
            conn.close()


def get_report(analysis_id: str) -> dict | None:
    """Return the deserialized report dict, or None if not available."""
    with _lock:
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT report_json FROM analyses WHERE id = ?",
                (analysis_id,)
            ).fetchone()
            if row is None or not row["report_json"]:
                return None
            return json.loads(row["report_json"])
        finally:
            conn.close()


def list_analyses(limit: int = 100, offset: int = 0) -> list[dict]:
    """
    Return recent analyses ordered by created_at DESC.
    Excludes the full report_json blob — use get_report() for that.
    """
    with _lock:
        conn = _get_conn()
        try:
            rows = conn.execute("""
                SELECT id, company_name, industry_key, annual_revenue,
                       headcount, currency, country, primary_concern,
                       status, error, created_at, completed_at, file_count
                FROM analyses
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def count_analyses(status: str | None = None) -> int:
    """Count analyses, optionally filtered by status."""
    with _lock:
        conn = _get_conn()
        try:
            if status:
                row = conn.execute(
                    "SELECT COUNT(*) FROM analyses WHERE status = ?", (status,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()
            return row[0]
        finally:
            conn.close()


def delete_analysis(analysis_id: str) -> bool:
    """Delete an analysis record. Returns True if a row was deleted."""
    with _lock:
        conn = _get_conn()
        try:
            cur = conn.execute(
                "DELETE FROM analyses WHERE id = ?", (analysis_id,)
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


# ── Helpers ────────────────────────────────────────────────────────

def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    # Deserialise the report blob if present
    if d.get("report_json"):
        try:
            d["report"] = json.loads(d["report_json"])
        except Exception:
            d["report"] = None
        del d["report_json"]
    return d
