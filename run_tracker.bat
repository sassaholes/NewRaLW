@echo off
setlocal

REM Pass all command-line arguments to tracker.py
py "%~dp0tracker.py" %*

endlocal
