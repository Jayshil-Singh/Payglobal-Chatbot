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

streamlit run app.py --server.headless false --browser.gatherUsageStats false

pause
