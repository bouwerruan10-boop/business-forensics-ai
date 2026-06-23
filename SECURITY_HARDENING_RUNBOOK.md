# Security Hardening Runbook (Imara)

Account-level hygiene that only the account owner can perform (Claude can't, and
shouldn't, enter credentials or change account settings). Code-side controls are
already in place; this closes the account/repo gaps. Do these in order.

## Status snapshot (as of this runbook)

| Control | State | Action |
|---|---|---|
| GitHub 2FA | **OFF** (flagged priority) | Enable — section 1 |
| `main` branch protection | **NONE** | Add solo-safe ruleset — section 2 |
| GitHub secret scanning + push protection | confirm ON | section 3 |
| gitleaks CI gate | ✅ present (`.gitleaks.toml`) | none |
| Railway 2FA | confirm | section 4 |
| Vercel 2FA | confirm | section 4 |
| Proprietary LICENSE / NOTICE / NDA | ✅ present | none |

## 1. Enable GitHub 2FA (do this first)

1. GitHub → profile picture (top-right) → **Settings**.
2. Left sidebar **Access → Password and authentication**.
3. Under **Two-factor authentication** → **Enable two-factor authentication**.
4. Choose a **TOTP authenticator app** (Authy, 1Password, Google Authenticator) — GitHub recommends TOTP over SMS.
5. Scan the QR code, enter the 6-digit code.
6. **Save the recovery codes** somewhere safe (a password manager) — this is how you get back in if you lose the device.
7. Optional: add a passkey/security key as a backup method.

> Note: GitHub has required 2FA for code contributors since 2023; enabling it removes the risk of an eventual forced lock-out and protects the repo from account takeover.

## 2. Protect `main` with a solo-safe ruleset

Use a **ruleset** (the modern replacement for branch-protection rules). The goal is to stop accidental history loss **without** requiring pull-request reviews — requiring PRs would break the direct-push `push_imara.bat` workflow.

1. Repo → **Settings → Rules → Rulesets → New branch ruleset**.
2. **Name:** `main-protect`. **Enforcement status:** Active.
3. **Target branches:** Add target → **Include default branch** (`main`).
4. **Enable these rules:**
   - ✅ **Restrict deletions** (can't delete `main`)
   - ✅ **Block force pushes** (can't rewrite history)
   - ✅ **Require status checks to pass** → add the **gitleaks** check (and the test workflow if present) so a secret-leaking or failing push is rejected.
5. **Do NOT enable** "Require a pull request before merging" — you push directly to `main` via `push_imara.bat`; a PR requirement would block every push.
6. **Bypass list:** add yourself (repo admin) so you're never locked out of an emergency direct push.
7. **Create**.

Verify: `push_imara.bat` still pushes successfully after the ruleset is active (it should — direct pushes are allowed; only force-push/delete are blocked).

## 3. Secret scanning + push protection

1. Repo → **Settings → Code security**.
2. Enable **Secret scanning** and **Push protection** (push protection blocks a commit that contains a detected secret before it lands).
3. This complements the local `.gitleaks.toml` CI gate — defence in depth (local gate + GitHub-side scan).

## 4. Railway + Vercel 2FA

- **Railway:** Account → **Settings → Security/2FA** → enable TOTP. Railway holds `ANTHROPIC_API_KEY` and the DB volume — protect it.
- **Vercel:** Account → **Settings → Authentication / Two-Factor** → enable. Vercel holds the deploy pipeline and `VITE_API_URL`.

## What stays code-side (already done — no action)

- `.gitleaks.toml` + gitleaks CI gate (pre-merge secret scan).
- Proprietary `LICENSE`, `NOTICE`, NDA/ToU, "Ask" extraction guard.
- Operator-auth gate on the app (401 + CORS-readable), fail-closed login.
- SafeJSONResponse + sanitise-on-write/read; hash-chained audit log.

## Re-verify after changes

- 2FA: log out / back in → prompted for the TOTP code.
- Ruleset: try `git push --force` to `main` → should be **rejected**; a normal `push_imara.bat` → **succeeds**.
- Push protection: it only triggers on a real secret; don't test with a live key.
