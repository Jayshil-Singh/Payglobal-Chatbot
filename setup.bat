@echo off
title PayGlobal AI Assistant — Setup
color 0B
echo.
echo  =============================================
echo   PayGlobal AI Assistant — First-Time Setup
echo  =============================================
echo.

REM Check Python (try py launcher first, then python)
py --version >nul 2>&1
if errorlevel 1 (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python not found. Please install Python 3.9+ first.
        pause
        exit /b 1
    )
    set PYTHON_CMD=python
) else (
    set PYTHON_CMD=py
)

REM Create .env from example
if not exist ".env" (
    copy ".env.example" ".env"
    echo [INFO] .env file created. Please edit it and add your OPENAI_API_KEY.
    echo.
    echo  IMPORTANT: Open .env with Notepad and set your API key:
    echo  OPENAI_API_KEY=sk-your-key-here
    echo.
    notepad .env
)

REM Create virtual environment
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

REM Activate and install
call venv\Scripts\activate.bat
echo [INFO] Installing dependencies...
pip install -r requirements.txt --quiet

echo.
echo  =============================================
echo   Setup complete! Run "run.bat" to start.
echo  =============================================
pause
