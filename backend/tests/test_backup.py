"""Tests for the DB backup/restore service (Tier 1.5). Uses temp SQLite DBs - no env, no live DB."""
import sqlite3

from services.backup import create_backup, list_backups, prune_backups, restore_backup


def _make_db(path, rows):
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    conn.executemany("INSERT INTO t (v) VALUES (?)", [(r,) for r in rows])
    conn.commit()
    conn.close()


def _count(path):
    conn = sqlite3.connect(str(path))
    try:
        return conn.execute("SELECT COUNT(*) FROM t").fetchone()[0]
    finally:
        conn.close()


def test_create_backup_is_a_consistent_copy(tmp_path):
    db = tmp_path / "live.db"
    _make_db(db, ["a", "b", "c"])
    bdir = tmp_path / "backups"
    snap = create_backup(db_path=db, backup_dir=bdir)
    assert snap.exists()
    assert snap.parent == bdir
    assert _count(snap) == 3   # snapshot has the same data


def test_create_backup_missing_db_raises(tmp_path):
    try:
        create_backup(db_path=tmp_path / "nope.db", backup_dir=tmp_path / "b")
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_list_backups_newest_first(tmp_path):
    db = tmp_path / "live.db"; _make_db(db, ["x"])
    bdir = tmp_path / "b"
    a = create_backup(db_path=db, backup_dir=bdir)
    b = create_backup(db_path=db, backup_dir=bdir)  # same second -> -1 suffix, sorts after
    names = [d["name"] for d in list_backups(bdir)]
    assert set(names) == {a.name, b.name}
    assert names == sorted(names, reverse=True)


def test_list_backups_missing_dir_is_empty(tmp_path):
    assert list_backups(tmp_path / "does-not-exist") == []


def test_prune_keeps_n_most_recent(tmp_path):
    db = tmp_path / "live.db"; _make_db(db, ["x"])
    bdir = tmp_path / "b"
    for _ in range(5):
        create_backup(db_path=db, backup_dir=bdir)
    removed = prune_backups(2, backup_dir=bdir)
    remaining = list_backups(bdir)
    assert len(remaining) == 2
    assert len(removed) == 3


def test_restore_replaces_db_and_keeps_safety_copy(tmp_path):
    db = tmp_path / "live.db"
    _make_db(db, ["a", "b"])                 # 2 rows
    bdir = tmp_path / "b"
    snap = create_backup(db_path=db, backup_dir=bdir)   # snapshot of the 2-row state
    # now mutate the live DB to 4 rows
    conn = sqlite3.connect(str(db)); conn.executemany("INSERT INTO t (v) VALUES (?)", [("c",), ("d",)]); conn.commit(); conn.close()
    assert _count(db) == 4
    restore_backup(snap, db_path=db)
    assert _count(db) == 2                    # restored to snapshot state
    # a pre-restore safety copy of the 4-row state should exist alongside
    safety = list(tmp_path.glob("live.db.pre-restore-*"))
    assert len(safety) == 1 and _count(safety[0]) == 4


def test_restore_missing_snapshot_raises(tmp_path):
    db = tmp_path / "live.db"; _make_db(db, ["a"])
    try:
        restore_backup(tmp_path / "ghost.db", db_path=db)
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_restore_rejects_corrupt_snapshot_without_touching_live_db(tmp_path):
    db = tmp_path / "live.db"; _make_db(db, ["a", "b"])
    bad = tmp_path / "corrupt.db"; bad.write_bytes(b"not a sqlite file" * 50)
    try:
        restore_backup(bad, db_path=db)
        assert False, "expected restore to reject the corrupt snapshot"
    except Exception:
        pass
    assert _count(db) == 2          # live DB untouched
    assert not list(tmp_path.glob("live.db.pre-restore-*"))  # no safety copy written


def test_prune_keep_zero_removes_all(tmp_path):
    db = tmp_path / "live.db"; _make_db(db, ["a"])
    bdir = tmp_path / "b"
    for _ in range(3):
        create_backup(db_path=db, backup_dir=bdir)
    removed = prune_backups(0, backup_dir=bdir)
    assert len(removed) == 3 and list_backups(bdir) == []
