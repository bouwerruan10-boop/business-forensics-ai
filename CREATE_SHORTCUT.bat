@echo off
title Creating Desktop Shortcut...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%USERPROFILE%\Desktop\Business Forensics AI.lnk'); $s.TargetPath = '%~dp0START.bat'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'Launch Business Forensics AI Platform'; $s.IconLocation = '%SystemRoot%\System32\shell32.dll,43'; $s.Save()"
echo.
echo Shortcut created on your Desktop!
echo Look for "Business Forensics AI" on your Desktop.
echo.
pause
