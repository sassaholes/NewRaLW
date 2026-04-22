@echo off
setlocal

REM If no args were provided, print help and an example instead of exiting silently.
if "%~1"=="" (
  echo Usage:
  echo   run_tracker.bat --artist "Adele" --song "Hello" --max-results 20
  echo.
  py "%~dp0tracker.py" --help
  echo.
  echo Example:
  echo   run_tracker.bat --artist "Adele" --song "Hello" --max-results 20 --out results.json
  pause
  exit /b 1
)

py -m py_compile "%~dp0tracker.py"
if errorlevel 1 (
  echo.
  echo tracker.py has a syntax error. Please update/re-download the project files.
  pause
  exit /b 1
)

REM Pass all command-line arguments to tracker.py
py "%~dp0tracker.py" %*

endlocal
