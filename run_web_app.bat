@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py web_app.py
) else (
  python web_app.py
)
endlocal
