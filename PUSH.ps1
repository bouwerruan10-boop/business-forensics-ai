$ProjectRoot = $PSScriptRoot
$RepoUrl = "https://github.com/bouwerruan10-boop/business-forensics-ai.git"

Write-Host ""
Write-Host "Pushing Business Forensics AI to GitHub..." -ForegroundColor Cyan
Write-Host ""

Set-Location $ProjectRoot
Write-Host "Working in: $ProjectRoot" -ForegroundColor Gray

# Delete broken .git folder and start fresh
if (Test-Path ".git") {
    Write-Host "Removing old .git folder..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force ".git"
    Write-Host "Removed" -ForegroundColor Green
}

# Init fresh repo
git init
git branch -M main
Write-Host "Git initialised" -ForegroundColor Green

# Set identity
git config user.email "bouwer.ruan10@gmail.com"
git config user.name "Ruan Bouwer"

# Stage all files
git add -A
Write-Host "Files staged" -ForegroundColor Green

# Commit
git commit -m "Initial commit Business Forensics AI v2"
Write-Host "Committed" -ForegroundColor Green

# Set remote and push
git remote add origin $RepoUrl
Write-Host "Remote set" -ForegroundColor Green

Write-Host ""
Write-Host "Pushing to GitHub - a browser may open to log in..." -ForegroundColor Yellow
Write-Host ""
git push -u origin main --force

Write-Host ""
Write-Host "Done! Repo: https://github.com/bouwerruan10-boop/business-forensics-ai" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to close"
