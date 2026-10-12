@echo off
powershell.exe -NoProfile -File "%~dp0ctl.ps1" %1
exit /b %errorlevel%
