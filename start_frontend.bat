@echo off
REM ============================================================
REM start_frontend.bat
REM Double-click this OR run from PowerShell to start the UI.
REM ============================================================

SET PROJECT_DIR=%~dp0
SET FRONTEND_DIR=%PROJECT_DIR%frontend

echo.
echo  4CECloud AI Hiring Agent - Frontend Startup
echo  ============================================

REM Check Node/npm
call npm --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo  ERROR: npm not found.
    echo  Download Node.js from https://nodejs.org/en/download
    echo  Choose the LTS Windows Installer, install, then restart this window.
    pause
    exit /b 1
)

cd /d "%FRONTEND_DIR%"

IF NOT EXIST "node_modules" (
    echo  Installing npm packages [first time only]...
    call npm install
)

echo.
echo  Starting frontend on http://localhost:5173
echo  Press Ctrl+C to stop.
echo.
call npm run dev
pause
