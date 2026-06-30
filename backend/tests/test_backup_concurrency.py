"""Concurrency regression: a backup running concurrently with analysis writes must not
raise "database is locked".

The process-wide database._lock serialises intra-process DB ops, but services/backup.py
opens its OWN connections (the SQLite online-backup API holds a SHARED read-lock on the
live DB during a snapshot) and so bypasses that lock. Before the fix, _get_conn() set no
busy_timeout, so a write commit (save_report / append_audit) that collided with a backup's
read-lock failed INSTANTLY -> the report was lost and the audit chain append crashed. This
would surface precisely when BACKUP_ENABLED is switched on. The busy_timeout makes the
writer wait for the short-lived read-lock to clear instead. Pin it so the class can't return.
"""
import importlib
import threading


def _reload_with_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BF_DB_PATH", str(tmp_path / "concurrency.db"))
    import services.database as d
    import services.backup as b
    importlib.reload(d)
    importlib.reload(b)
    return d, b


def test_busy_timeout_is_set_on_connections(monkeypatch, tmp_path):
    d, _ = _reload_with_db(monkeypatch, tmp_path)
    try:
        d.init_db()
        conn = d._get_conn()
        try:
            assert conn.execute("PRAGMA busy_timeout").fetchone()[0] >= 1000
        finally:
            conn.close()
    finally:
        importlib.reload(d)


def test_concurrent_backup_and_writes_never_lock(monkeypatch, tmp_path):
    d, b = _reload_with_db(monkeypatch, tmp_path)
    try:
        d.init_db()
        for i in range(20):
            d.create_analysis("a%d" % i, {"company_name": "C%d" % i})

        errors = []

        def writer():
            for i in range(40):
                try:
                    d.save_report("a%d" % (i % 20), {"imara_score": 50, "blob": "x" * 2000})
                    d.append_audit({"analysis_id": "a%d" % (i % 20), "event": "score", "n": i})
                except Exception as e:  # noqa: BLE001 - we WANT to catch + classify any error
                    errors.append(("write", type(e).__name__, str(e)))

        def backupper():
            for _ in range(15):
                try:
                    b.create_backup()
                    b.prune_backups(3)
                except Exception as e:  # noqa: BLE001
                    errors.append(("backup", type(e).__name__, str(e)))

        threads = [threading.Thread(target=writer) for _ in range(3)]
        threads += [threading.Thread(target=backupper) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        locked = [e for e in errors if "locked" in e[2].lower()]
        assert not locked, "database-is-locked under concurrent backup+write: " + repr(locked[:5])
        assert not errors, "unexpected errors under concurrency: " + repr(errors[:5])
    finally:
        importlib.reload(d)
        importlib.reload(b)
