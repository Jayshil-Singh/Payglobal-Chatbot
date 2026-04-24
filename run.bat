@echo off
title PayGlobal AI Assistant
color 0B
echo.
echo  =============================================
echo   Starting PayGlobal AI Assistant...
echo  =============================================
echo.

REM Activate venv if it exists, otherwise use global Python
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Runtime hardening to reduce unexpected watcher exits on Windows
set "STREAMLIT_SERVER_FILE_WATCHER_TYPE=none"
set "PYTHONUTF8=1"

py -3 -m streamlit run app.py --server.headless false --browser.gatherUsageStats false --server.fileWatcherType none

pause
