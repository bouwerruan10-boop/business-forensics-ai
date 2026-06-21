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
    # 1) Explicit override.
    if os.environ.get("BF_DB_PATH"):
        return Path(os.environ["BF_DB_PATH"])
    # 2) Railway persistent volume (set automatically when a volume is attached) —
    #    keeps analyses/reports/share-links across redeploys instead of an ephemeral FS.
    vol = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
    if vol:
        try:
            p = Path(vol) / "analyses.db"
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
        except OSError:
            pass
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


def _add_owner_column(conn, table):
    """Idempotent: add the multi-tenancy 'owner' column to an existing table."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info({})".format(table)).fetchall()]
    if "owner" not in cols:
        conn.execute("ALTER TABLE {} ADD COLUMN owner TEXT NOT NULL DEFAULT 'operator'".format(table))


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
                    file_count      INTEGER DEFAULT 0,
                    owner           TEXT    NOT NULL DEFAULT 'operator'
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
            for _t in ("analyses", "shares"):
                pass  # tables created below; owner migration runs after
            conn.execute("""
                CREATE TABLE IF NOT EXISTS shares (
                    token       TEXT PRIMARY KEY,
                    analysis_id TEXT NOT NULL,
                    expires_at  TEXT,
                    revoked     INTEGER NOT NULL DEFAULT 0,
                    created_at  TEXT NOT NULL,
                    owner       TEXT NOT NULL DEFAULT 'operator'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS outcomes (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id  TEXT NOT NULL,
                    outcome_type TEXT NOT NULL,
                    label        INTEGER,
                    value        REAL,
                    note         TEXT,
                    source       TEXT,
                    recorded_at  TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decision_audit (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id  TEXT NOT NULL,
                    created_at   TEXT NOT NULL,
                    record_json  TEXT NOT NULL,
                    record_hash  TEXT NOT NULL,
                    prev_hash    TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_analysis ON decision_audit (analysis_id)")
            _add_owner_column(conn, "analyses")
            _add_owner_column(conn, "shares")
            conn.commit()
        finally:
            conn.close()


def create_analysis(analysis_id: str, profile: dict, file_count: int = 0, owner: str = "operator"):
    """Insert a new analysis record in 'processing' state."""
    now = _utcnow()
    with _lock:
        conn = _get_conn()
        try:
            conn.execute("""
                INSERT OR IGNORE INTO analyses
                    (id, company_name, industry_key, annual_revenue,
                     headcount, currency, country, primary_concern,
                     status, created_at, file_count, owner)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'processing', ?, ?, ?)
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
                owner,
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


def create_share(analysis_id: str, expires_at: str | None = None, owner: str = "operator") -> str:
    """Create an opaque public share token for an analysis (optional ISO expiry)."""
    token = secrets.token_urlsafe(16)
    now = _utcnow()
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                "INSERT INTO shares (token, analysis_id, expires_at, revoked, created_at, owner) "
                "VALUES (?, ?, ?, 0, ?, ?)", (token, analysis_id, expires_at, now, owner))
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


def get_analysis(analysis_id: str, owner: str | None = None) -> dict | None:
    """Return a single analysis row as a dict, or None. Optional owner filter (multi-tenant)."""
    with _lock:
        conn = _get_conn()
        try:
            if owner:
                row = conn.execute("SELECT * FROM analyses WHERE id = ? AND owner = ?", (analysis_id, owner)).fetchone()
            else:
                row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
            if row is None:
                return None
            return _row_to_dict(row)
        finally:
            conn.close()


def recent_reports(limit: int = 50) -> list:
    """Load the most recent COMPLETED analyses with their full report (for fleet quality)."""
    with _lock:
        conn = _get_conn()
        try:
            rows = conn.execute(
                "SELECT id, created_at, report_json FROM analyses "
                "WHERE status = 'complete' AND report_json IS NOT NULL "
                "ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        finally:
            conn.close()
    out = []
    for r in rows:
        try:
            rep = json.loads(r["report_json"])
        except Exception:
            continue
        out.append({"analysis_id": r["id"], "created_at": r["created_at"], "report": rep})
    return out


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
            from services.jsonsafe import finite_safe
            return finite_safe(json.loads(row["report_json"]))
        finally:
            conn.close()


def list_analyses(limit: int = 100, offset: int = 0, owner: str | None = None) -> list[dict]:
    """
    Return recent analyses ordered by created_at DESC.
    Excludes the full report_json blob — use get_report() for that.
    """
    with _lock:
        conn = _get_conn()
        try:
            _where = "WHERE owner = ?" if owner else ""
            _params = ([owner, limit, offset] if owner else [limit, offset])
            rows = conn.execute(
                "SELECT id, company_name, industry_key, annual_revenue, headcount, currency, "
                "country, primary_concern, status, error, created_at, completed_at, file_count "
                "FROM analyses {} ORDER BY created_at DESC LIMIT ? OFFSET ?".format(_where),
                _params).fetchall()
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


def record_outcome(analysis_id, outcome_type, label=None, value=None, note="", source=""):
    """Record a real-world outcome for an analysis (the raw material for calibration):
    outcome_type e.g. 'default'|'repaid'|'funded'|'declined'|'external_score'; label is a
    binary 1=bad/default / 0=good when applicable; value carries a numeric (e.g. bureau score)."""
    from datetime import datetime, timezone
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                "INSERT INTO outcomes (analysis_id, outcome_type, label, value, note, source, recorded_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (analysis_id, outcome_type, label, value, note, source,
                 datetime.now(timezone.utc).isoformat()))
            conn.commit()
        finally:
            conn.close()
    return True


def outcomes_with_scores():
    """Join binary-labelled outcomes to their analysis's stored Imara Score —
    [(analysis_id, imara_score, label)] — the input to discrimination/calibration."""
    with _lock:
        conn = _get_conn()
        try:
            rows = conn.execute(
                "SELECT o.analysis_id AS aid, o.label AS label, a.report_json AS rj "
                "FROM outcomes o JOIN analyses a ON a.id = o.analysis_id "
                "WHERE o.label IS NOT NULL AND a.report_json IS NOT NULL").fetchall()
        finally:
            conn.close()
    out = []
    for r in rows:
        try:
            rep = json.loads(r["rj"])
        except Exception:
            continue
        sc = rep.get("imara_score")
        if sc is not None:
            out.append({"analysis_id": r["aid"], "imara_score": sc, "label": int(r["label"])})
    return out


# ── Decision audit log (append-only, hash-chained — governance/AI-Act evidence) ──
def _sha256(text: str) -> str:
    import hashlib
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def append_audit(record: dict) -> dict:
    """Append a hash-chained decision record. Append-only (never updated/deleted).
    Returns {record_hash, prev_hash, created_at}."""
    import json as _json
    now = _utcnow()
    body = _json.dumps(record, sort_keys=True, default=str)
    with _lock:
        conn = _get_conn()
        try:
            prev = conn.execute("SELECT record_hash FROM decision_audit ORDER BY id DESC LIMIT 1").fetchone()
            prev_hash = prev["record_hash"] if prev else None
            record_hash = _sha256((prev_hash or "") + "|" + body)
            conn.execute(
                "INSERT INTO decision_audit (analysis_id, created_at, record_json, record_hash, prev_hash) VALUES (?,?,?,?,?)",
                (record.get("analysis_id", ""), now, body, record_hash, prev_hash))
            conn.commit()
            return {"record_hash": record_hash, "prev_hash": prev_hash, "created_at": now}
        finally:
            conn.close()


def _audit_rows(where="", params=()):
    import json as _json
    with _lock:
        conn = _get_conn()
        try:
            rows = conn.execute("SELECT * FROM decision_audit " + where, params).fetchall()
        finally:
            conn.close()
    out = []
    for r in rows:
        d = _json.loads(r["record_json"])
        d["record_hash"] = r["record_hash"]; d["prev_hash"] = r["prev_hash"]; d["created_at"] = r["created_at"]
        out.append(d)
    return out


def get_audit(analysis_id: str) -> list:
    return _audit_rows("WHERE analysis_id=? ORDER BY id", (analysis_id,))


def list_audit(limit: int = 100) -> list:
    return _audit_rows("ORDER BY id DESC LIMIT ?", (int(limit),))


def verify_audit_chain() -> dict:
    """Recompute the hash chain to confirm the audit log has not been tampered with."""
    with _lock:
        conn = _get_conn()
        try:
            rows = conn.execute("SELECT record_json, record_hash, prev_hash FROM decision_audit ORDER BY id").fetchall()
        finally:
            conn.close()
    prev = None
    for i, r in enumerate(rows):
        expect = _sha256((prev or "") + "|" + r["record_json"])
        if r["prev_hash"] != prev or r["record_hash"] != expect:
            return {"intact": False, "broken_at_index": i, "records": len(rows)}
        prev = r["record_hash"]
    return {"intact": True, "records": len(rows)}
