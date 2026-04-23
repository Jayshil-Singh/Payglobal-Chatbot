@echo off
chcp 65001 >nul
title PayGlobal - Bulk Document Ingestion
color 0A
echo.
echo  ============================================================
echo   PayGlobal AI Assistant - Bulk Document Ingestion
echo  ============================================================
echo.
echo  This will ingest all PDFs and DOCX files from:
echo.
echo    Option 1: data\raw\          (default folder)
echo    Option 2: Any folder you specify below
echo.
echo  NOTE: Already-ingested files will be SKIPPED automatically.
echo        Only new or modified files will be processed.
echo.

REM Activate venv
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Ask user for folder choice
set /p FOLDER="Enter folder path (or press ENTER for data\raw): "

if "%FOLDER%"=="" (
    set FOLDER=data\raw
    echo.
    echo  Using default folder: data\raw
    echo.
    echo  *** IMPORTANT ***
    echo  If data\raw is empty, copy your PayGlobal PDFs/DOCX
    echo  into this folder first, then re-run this script.
    echo.
    if not exist "data\raw\*.pdf" (
        if not exist "data\raw\*.docx" (
            echo  WARNING: No PDF or DOCX files found in data\raw\
            echo  Copy your documents there and run again.
            echo.
            pause
            exit /b 0
        )
    )
)

REM Ask for batch size
echo.
set /p BATCH="Chunks per batch [ENTER = 100, use 30 for low-RAM PC]: "
if "%BATCH%"=="" set BATCH=100

echo.
echo  ============================================================
echo   Starting ingestion... (safe to stop and restart anytime)
echo   Progress is saved after every file.
echo  ============================================================
echo.

python ingest.py --folder "%FOLDER%" --batch-size %BATCH%

echo.
echo  ============================================================
echo   Done! Start the chatbot with run.bat
echo  ============================================================
pause
