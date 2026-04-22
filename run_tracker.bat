@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  set "PYEXE=py"
) else (
  set "PYEXE=python"
)

%PYEXE% -m py_compile tracker.py >nul 2>nul
if errorlevel 1 (
  echo Python files failed to compile. Please re-download/update project files.
  pause
  exit /b 1
)

%PYEXE% tracker.py %*

endlocal
