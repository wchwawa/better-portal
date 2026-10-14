@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
 echo Install Python 3.10 or newer from python.org with the Python launcher.
 pause
 exit /b 2
)
py -3 -m venv .venv
if errorlevel 1 exit /b 2
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 2
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 (
 echo Offline tests failed. Do not start the live experiment.
 pause
 exit /b 2
)
echo Install Npcap from https://npcap.com/#download if needed.
echo Setup complete. Double-click Start-Windows.cmd to open the guided setup.
echo Accept the Windows permission prompt. The wizard saves your addresses and language.
pause
