@echo off
setlocal
title PayGlobal AI Assistant — Reset Admin Password
color 0B

echo.
echo  =============================================
echo   Reset Admin Password (Local)
echo  =============================================
echo.
echo  This will reset (or create) the admin user in data\payglobal.db
echo.

set /p NEWPASS=Enter new admin password (will be visible): 
if "%NEWPASS%"=="" (
  echo [ERROR] Password cannot be empty.
  pause
  exit /b 1
)

py -3 scripts\reset_admin_password.py --username admin --password "%NEWPASS%"
if errorlevel 1 (
  echo [ERROR] Reset failed.
  pause
  exit /b 1
)

echo.
echo [OK] Done. Start the app and sign in as: admin
echo.
pause
endlocal

