@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  start "Music Usage Finder" cmd /k "py web_app.py"
) else (
  start "Music Usage Finder" cmd /k "python web_app.py"
)
timeout /t 2 >nul
start "" "http://127.0.0.1:8000"
endlocal
