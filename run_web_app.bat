@echo off
setlocal

echo Starting web app server...
echo URL: http://127.0.0.1:8000
echo.
echo If the browser does not open automatically, copy/paste this URL:
echo   http://127.0.0.1:8000
echo.

start "" "http://127.0.0.1:8000"
py "%~dp0web_app.py"

echo.
echo Web app exited. If it did not start, confirm Python is installed and 'py' works in Command Prompt.
pause
endlocal
