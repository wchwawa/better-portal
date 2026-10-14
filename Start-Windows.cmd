@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
  echo Run Setup-Windows.cmd first.
  pause
  exit /b 2
)
".venv\Scripts\python.exe" portal_windows_launcher.py
exit /b %errorlevel%
