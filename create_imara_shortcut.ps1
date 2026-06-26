$ErrorActionPreference = 'Stop'
$url = 'https://business-forensics-ai.vercel.app'
$edge = @(
  (Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe'),
  (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'),
  (Join-Path $env:LocalAppData 'Microsoft\Edge\Application\msedge.exe')
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $edge) { Write-Host 'ERROR: Microsoft Edge not found - cannot create the app shortcut.'; exit 1 }
$icon = Join-Path $PSScriptRoot 'imara.ico'
$desktop = [Environment]::GetFolderPath('Desktop')
$lnkPath = Join-Path $desktop 'Imara.lnk'
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut($lnkPath)
$s.TargetPath = $edge
$s.Arguments = "--app=$url"
if (Test-Path $icon) { $s.IconLocation = $icon } else { Write-Host 'WARN: imara.ico not found; using default icon.' }
$s.Description = 'Imara - Business Intelligence'
$s.WorkingDirectory = Split-Path $edge
$s.Save()
Write-Host ''
Write-Host ('SUCCESS: Imara app shortcut created on your Desktop -> ' + $lnkPath)
Write-Host ('         (launches Edge app-mode: ' + $url + ')')
