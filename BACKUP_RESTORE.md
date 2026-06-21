# Imara — Database Backup & Restore Runbook

Imara's SQLite DB holds every analysis, share link, and the tamper-evident audit
chain. The Railway volume survives redeploys but is **not** itself backed up —
this is the disaster-recovery procedure (Tier 1.5).

## What the backup system does
- Takes **consistent point-in-time snapshots** using SQLite's online backup API
  (safe under concurrent writes — no downtime to snapshot).
- Names them `analyses-YYYYMMDDThhmmssZ.db`, newest-first.
- **Rotates** them (keeps `BACKUP_KEEP`, default 7).
- Runs on a **daemon thread**: one snapshot at startup, then every
  `BACKUP_INTERVAL_HOURS` (default 24).

## Activate (one step)
Set on the Railway backend service:

```
BACKUP_ENABLED=true
```

Optional:
| Var | Default | Purpose |
|---|---|---|
| `BACKUP_DIR` | `<db dir>/backups` | **Point at a second mount for true off-volume durability** |
| `BACKUP_INTERVAL_HOURS` | `24` | snapshot cadence |
| `BACKUP_KEEP` | `7` | how many to retain |

> **Durability note:** the default `backups/` dir sits on the **same volume** as
> the live DB. That protects against accidental drops, corruption, and bad
> migrations, but **not** against losing the whole volume. For real off-site
> safety, set `BACKUP_DIR` to a separate mount, or copy snapshots off with a cron
> / object-storage upload (the snapshot files are self-contained `.db` files).

## On-demand (admin-gated)
```
POST /api/admin/backup      # snapshot now + rotate; returns the list
GET  /api/admin/backups     # list snapshots (newest first)
```
Send the `X-Admin-Key` header (when `ADMIN_API_KEY` is set).

## Restore
Restoring **replaces the live DB**. It verifies the snapshot's integrity, saves a
consistent safety copy of the current DB (`analyses.db.pre-restore-<ts>`), then
swaps atomically.

**Best run with the service paused** (so no request is mid-write):

1. Pause the Railway service (or scale to 0).
2. From the backend dir:
   ```python
   from services.backup import list_backups, restore_backup
   list_backups()                       # find the snapshot you want
   restore_backup("<path-to-snapshot>") # safety copy is written automatically
   ```
3. Resume the service. Verify with `GET /api/admin/audit` that the audit chain
   reports `intact: true`.

If a restore went wrong, the `*.pre-restore-*` safety copy is the state from just
before the restore — `restore_backup()` it back.
