"""
backup.py - consistent SQLite snapshots for disaster recovery (Tier 1.5).

The Railway persistent volume survives redeploys but is NOT backed up - losing
the volume loses every analysis, share link, and the tamper-evident audit chain.
This module takes point-in-time snapshots using SQLite's ONLINE backup API (a
consistent copy that is safe under concurrent writes; no global lock needed),
rotates them, and restores from one.

Durability honesty: snapshots default to a `backups/` dir beside the live DB (the
SAME volume), which protects against accidental drops / corruption / bad
migrations but NOT against losing the whole volume. For true off-volume
durability set BACKUP_DIR to a second mount, or copy snapshots off-site (see
BACKUP_RESTORE.md). Pure, dependency-free, fully unit-testable.
"""
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from services.database import get_db_path

_TS_FMT = "%Y%m%dT%H%M%SZ"
_PREFIX = "analyses-"
_SUFFIX = ".db"
_BUSY_TIMEOUT_MS = 5000   # wait for a concurrent write commit to clear instead of failing fast


def _connect(path):
    """A connection that waits (rather than raising 'database is locked') when the live DB
    is momentarily write-locked by a concurrent analysis commit."""
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA busy_timeout = {}".format(_BUSY_TIMEOUT_MS))
    return conn


def get_backup_dir():
    env = os.environ.get("BACKUP_DIR")
    if env:
        return Path(env)
    return get_db_path().parent / "backups"


def _online_backup(src_path, dst_path):
    """Consistent snapshot src_path -> dst_path via the sqlite3 online backup API."""
    dst_path = Path(dst_path)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    src = _connect(src_path)
    try:
        dst = _connect(dst_path)
        try:
            with dst:
                src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def create_backup(db_path=None, backup_dir=None):
    """Write a timestamped consistent snapshot; returns its Path."""
    db_path = Path(db_path) if db_path else get_db_path()
    backup_dir = Path(backup_dir) if backup_dir else get_backup_dir()
    if not db_path.exists():
        raise FileNotFoundError("database not found at {}".format(db_path))
    ts = datetime.now(timezone.utc).strftime(_TS_FMT)
    target = backup_dir / "{}{}{}".format(_PREFIX, ts, _SUFFIX)
    n = 1
    while target.exists():   # two runs in the same second
        target = backup_dir / "{}{}-{}{}".format(_PREFIX, ts, n, _SUFFIX)
        n += 1
    _online_backup(db_path, target)
    return target


def list_backups(backup_dir=None):
    """Newest-first list of snapshots: {path, name, bytes, modified}."""
    backup_dir = Path(backup_dir) if backup_dir else get_backup_dir()
    if not backup_dir.exists():
        return []
    out = []
    for p in backup_dir.glob("{}*{}".format(_PREFIX, _SUFFIX)):
        try:
            st = p.stat()
        except OSError:
            continue
        out.append({
            "path": str(p), "name": p.name, "bytes": st.st_size,
            "modified": datetime.fromtimestamp(st.st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    out.sort(key=lambda d: d["name"], reverse=True)   # timestamped names sort lexically
    return out


def prune_backups(keep, backup_dir=None):
    """Delete all but the `keep` most recent snapshots; returns removed paths."""
    keep = max(0, int(keep))
    removed = []
    for d in list_backups(backup_dir)[keep:]:
        try:
            Path(d["path"]).unlink()
            removed.append(d["path"])
        except OSError:
            pass
    return removed


def restore_backup(src, db_path=None):
    """Replace the live DB with a snapshot. Verifies the snapshot's integrity,
    saves a consistent safety copy of the current DB first, then swaps atomically.
    Best run with the service paused (see BACKUP_RESTORE.md)."""
    src = Path(src)
    db_path = Path(db_path) if db_path else get_db_path()
    if not src.exists():
        raise FileNotFoundError("backup not found: {}".format(src))
    chk = _connect(src)
    try:
        row = chk.execute("PRAGMA integrity_check").fetchone()
        if not row or row[0] != "ok":
            raise ValueError("snapshot failed integrity_check: {}".format(row))
    finally:
        chk.close()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        ts = datetime.now(timezone.utc).strftime(_TS_FMT)
        safety = db_path.with_name(db_path.name + ".pre-restore-" + ts)
        _online_backup(db_path, safety)
    tmp = db_path.with_name(db_path.name + ".restoring")
    _online_backup(src, tmp)
    os.replace(str(tmp), str(db_path))
    return db_path
