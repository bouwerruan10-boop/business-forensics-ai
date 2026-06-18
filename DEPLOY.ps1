# ─────────────────────────────────────────────────────────────────────────────
# Business Forensics AI — Full Deployment Script
# Run this in PowerShell from the project folder:
#   Right-click DEPLOY.ps1 → "Run with PowerShell"
# ─────────────────────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

function Write-Step { param($n, $msg) Write-Host "`n[$n] $msg" -ForegroundColor Cyan }
function Write-OK   { param($msg)     Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Warn { param($msg)     Write-Host "  ! $msg" -ForegroundColor Yellow }
function Write-Fail { param($msg)     Write-Host "  ✗ $msg" -ForegroundColor Red }
function Pause-ForUser { param($msg)  Write-Host "`n  >>> $msg" -ForegroundColor Magenta; Read-Host "  Press Enter when done" }

Write-Host @"

  ╔══════════════════════════════════════════════════════╗
  ║    Business Forensics AI — Deployment Assistant      ║
  ║    Steps: GitHub Push → Railway Backend → Vercel UI  ║
  ╚══════════════════════════════════════════════════════╝

"@ -ForegroundColor White

# ═══════════════════════════════════════════════════════════════════
# STEP 1 — GitHub Push
# ═══════════════════════════════════════════════════════════════════
Write-Step 1 "GITHUB — Push code"

Set-Location $ProjectRoot

# Check git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Fail "Git not found. Install from https://git-scm.com and re-run."
    exit 1
}
Write-OK "Git found: $(git --version)"

# Init if not a repo
if (-not (Test-Path ".git")) {
    git init
    git branch -M main
    Write-OK "Git repository initialised"
} else {
    Write-OK "Git repository already initialised"
}

# Configure identity
git config user.email "bouwer.ruan10@gmail.com"
git config user.name  "Ruan Bouwer"

# Stage and commit
git add -A
$status = git status --short
if ($status) {
    git commit -m "Initial commit — Business Forensics AI v2"
    Write-OK "Files committed"
} else {
    Write-OK "Nothing new to commit"
}

# GitHub remote
Write-Host ""
Write-Host "  You need a GitHub repo to push to." -ForegroundColor Yellow
Write-Host "  1. Go to: https://github.com/new" -ForegroundColor Yellow
Write-Host "  2. Name it: business-forensics-ai" -ForegroundColor Yellow
Write-Host "  3. Set it to Private, leave everything else blank, click Create" -ForegroundColor Yellow
Pause-ForUser "Create the GitHub repo now, then come back here"

$repoUrl = Read-Host "  Paste the GitHub repo URL (e.g. https://github.com/yourname/business-forensics-ai)"
$repoUrl = $repoUrl.Trim()

if ($repoUrl -eq "") {
    Write-Fail "No URL entered. Skipping GitHub push."
} else {
    # Remove existing remote if wrong
    $existing = git remote get-url origin 2>$null
    if ($existing -and $existing -ne $repoUrl) {
        git remote remove origin
    }
    if (-not (git remote get-url origin 2>$null)) {
        git remote add origin $repoUrl
    }

    Write-Host "  Pushing to GitHub... (a browser window may open for authentication)" -ForegroundColor Yellow
    git push -u origin main
    Write-OK "Code pushed to GitHub: $repoUrl"
    $global:GitHubUrl = $repoUrl
}

# ═══════════════════════════════════════════════════════════════════
# STEP 2 — Railway Backend
# ═══════════════════════════════════════════════════════════════════
Write-Step 2 "RAILWAY — Deploy FastAPI backend"

Write-Host @"

  Railway hosts the Python backend (free tier, no credit card needed).

  1. Go to: https://railway.app
  2. Sign up / log in with GitHub
  3. Click "New Project" → "Deploy from GitHub repo"
  4. Select: business-forensics-ai
  5. Click "Add variables" and add these:

     ANTHROPIC_API_KEY = (your Claude API key)
     MODEL             = claude-sonnet-4-6
     MAX_TOKENS        = 4096
     MOCK_MODE         = false
     RATE_LIMIT        = 10/hour

  6. Under Settings → General → Root Directory: set to "backend"
  7. Railway auto-detects the Procfile and deploys automatically
  8. Copy the generated URL (e.g. https://business-forensics-ai-xyz.railway.app)

"@ -ForegroundColor Yellow

Pause-ForUser "Deploy on Railway, copy the backend URL, then come back here"

$railwayUrl = Read-Host "  Paste your Railway backend URL (e.g. https://xyz.railway.app)"
$railwayUrl = $railwayUrl.Trim().TrimEnd("/")
if ($railwayUrl -eq "") {
    $railwayUrl = "https://your-railway-backend.railway.app"
    Write-Warn "No URL entered — using placeholder. Update VITE_API_URL in Vercel manually."
} else {
    Write-OK "Railway backend URL saved: $railwayUrl"
}

# Update vercel.json with real Railway URL
$vercelJson = Get-Content "$ProjectRoot\frontend\vercel.json" -Raw
$vercelJson = $vercelJson -replace "https://your-railway-backend-url\.railway\.app", $railwayUrl
Set-Content "$ProjectRoot\frontend\vercel.json" $vercelJson -NoNewline
Write-OK "frontend/vercel.json updated with Railway URL"

# Commit the updated vercel.json
Set-Location $ProjectRoot
git add frontend/vercel.json
git commit -m "chore: set Railway backend URL in vercel.json" 2>$null
git push 2>$null
Write-OK "Pushed updated vercel.json to GitHub"

# ═══════════════════════════════════════════════════════════════════
# STEP 3 — Vercel Frontend
# ═══════════════════════════════════════════════════════════════════
Write-Step 3 "VERCEL — Deploy React frontend"

# Check npm
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Warn "npm not found — skipping Vercel CLI. Deploy manually at vercel.com"
} else {
    Write-OK "npm found: $(npm --version)"

    # Install Vercel CLI if needed
    $vercelInstalled = Get-Command vercel -ErrorAction SilentlyContinue
    if (-not $vercelInstalled) {
        Write-Host "  Installing Vercel CLI..." -ForegroundColor Yellow
        npm install -g vercel
        Write-OK "Vercel CLI installed"
    } else {
        Write-OK "Vercel CLI already installed"
    }

    # Deploy frontend
    Set-Location "$ProjectRoot\frontend"
    Write-Host "  Deploying frontend to Vercel..." -ForegroundColor Yellow
    Write-Host "  (A browser will open to log in to your Vercel account)" -ForegroundColor Yellow
    Write-Host ""

    vercel --prod `
        --yes `
        --env "VITE_API_URL=$railwayUrl"

    Write-OK "Frontend deployed to Vercel!"
}

# ═══════════════════════════════════════════════════════════════════
# DONE
# ═══════════════════════════════════════════════════════════════════
Set-Location $ProjectRoot

Write-Host @"


  ╔══════════════════════════════════════════════════════╗
  ║  Deployment Complete!                                ║
  ║                                                      ║
  ║  Backend:  $($railwayUrl.PadRight(40))  ║
  ║  Frontend: check Vercel dashboard for live URL       ║
  ║                                                      ║
  ║  Test: open your Vercel URL → click Try Demo         ║
  ╚══════════════════════════════════════════════════════╝

"@ -ForegroundColor Green

Read-Host "Press Enter to close"
