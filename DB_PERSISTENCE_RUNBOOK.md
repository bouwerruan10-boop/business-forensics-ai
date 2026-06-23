# DB Persistence Runbook (Railway)

Imara stores every analysis, full report, and share link in SQLite. On Railway's
default filesystem that file is **ephemeral** — wiped on each redeploy. Attaching a
**volume** makes it durable. The code already supports this; you just attach the volume.

## How the DB path is resolved (code — already done)

`backend/services/database._resolve_db_path()`, first writable wins:

1. `BF_DB_PATH` (explicit override)
2. `RAILWAY_VOLUME_MOUNT_PATH/analyses.db` — **auto-set by Railway when a volume is attached**
3. `backend/data/analyses.db` (local dev)
4. `/tmp/bf_analyses.db` (ephemeral fallback — **data lost on redeploy**)

The resolved path + tier is printed at startup: `[imara.db] <tier> -> <path> (persistent|EPHEMERAL)`.

## One-time setup (Ruan — Railway dashboard)

1. Open the Railway project → the **backend** service.
2. **Variables** tab → confirm there is **no** `BF_DB_PATH` set (so the volume path wins), or set `BF_DB_PATH` only if you want a custom location.
3. **Settings / Volumes** (or the **+ Volume** action) → **Create a volume** attached to the backend service.
4. Set the **mount path** to `/app/data` (the app's working dir is `/app`).
   - The Dockerfile runs as **root**, and Railway mounts volumes as root, so the app can write to it — no `RAILWAY_RUN_UID` needed.
5. **Deploy** (Railway redeploys when a volume is attached).

> Note: volumes mount at **runtime**, not build time — that's fine here, the DB is created at startup, not during the build.

## Verify it worked

- **Logs:** the deploy log should show `[imara.db] Railway persistent volume -> /app/data/analyses.db (persistent)`.
- **Endpoint:** `GET /api/admin/db-status` (admin key required) returns
  `{ "path": "/app/data/analyses.db", "tier": "Railway persistent volume", "persistent_across_redeploys": true, ... }`.
- **Smoke test:** run an analysis → redeploy → confirm the analysis still appears in the admin list. (Before the volume, it would vanish.)

## If it still shows EPHEMERAL

- The volume isn't attached, or its mount path isn't where the app writes. Re-check step 4 (mount path) and that no override (`BF_DB_PATH`) points elsewhere.
- A `/tmp/...` path in the log/endpoint means neither the volume nor `backend/data` was writable — fix the mount.

## Backups (optional, recommended)

`services/backup.py` reads `get_db_path()`, so any backup job automatically targets the
live (volume) DB. Consider a scheduled copy of `analyses.db` off-volume for disaster recovery.
