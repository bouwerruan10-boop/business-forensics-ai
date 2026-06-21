"""POPIA s14 retention purge — deletes only analyses genuinely past the threshold,
never recent ones; dry-run never deletes. Isolated temp DB."""
import pytest
import services.database as db


@pytest.fixture
def tmpdb(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_PATH", tmp_path / "ret.db")
    db.init_db()
    return db


def _backdate(d, aid, created_at):
    with d._lock:
        conn = d._get_conn()
        conn.execute("UPDATE analyses SET created_at=? WHERE id=?", (created_at, aid))
        conn.commit(); conn.close()


def _seed(d):
    d.create_analysis("old1", {"company_name": "Old A"}, file_count=0, owner="operator")
    d.create_analysis("old2", {"company_name": "Old B"}, file_count=0, owner="operator")
    d.create_analysis("new1", {"company_name": "New"}, file_count=0, owner="operator")
    _backdate(d, "old1", "2020-01-01T00:00:00Z")
    _backdate(d, "old2", "2021-06-15T12:00:00Z")
    # new1 keeps its real (now) created_at


def test_dry_run_counts_but_does_not_delete(tmpdb):
    _seed(tmpdb)
    res = tmpdb.purge_old_analyses(365, dry_run=True)
    assert res["candidates"] == 2 and res["deleted"] == 0 and res["dry_run"] is True
    assert tmpdb.count_analyses() == 3   # nothing deleted


def test_purge_deletes_old_keeps_recent(tmpdb):
    _seed(tmpdb)
    res = tmpdb.purge_old_analyses(365)
    assert res["deleted"] == 2
    # 3 rows -> 1: the two backdated rows are gone, the recent one survives
    assert tmpdb.count_analyses() == 1
    remaining = {r.get("id") or r.get("analysis_id") for r in tmpdb.list_analyses()}
    assert remaining == {"new1"}


def test_no_recent_ever_deleted(tmpdb):
    tmpdb.create_analysis("recent", {"company_name": "Z"}, file_count=0, owner="operator")
    res = tmpdb.purge_old_analyses(1)   # 1-day retention; a just-created row must survive
    assert res["deleted"] == 0 and tmpdb.count_analyses() == 1


def test_retention_days_clamped_to_min_one(tmpdb):
    tmpdb.create_analysis("old", {"company_name": "Q"}, file_count=0, owner="operator")
    _backdate(tmpdb, "old", "2019-01-01T00:00:00Z")
    res = tmpdb.purge_old_analyses(0)   # clamped to 1 -> the 2019 row is purged, today's wouldn't be
    assert res["deleted"] == 1


def test_empty_db_is_safe(tmpdb):
    res = tmpdb.purge_old_analyses(365)
    assert res["candidates"] == 0 and res["deleted"] == 0
