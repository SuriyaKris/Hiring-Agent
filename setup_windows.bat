@echo off
REM ============================================================
REM setup_windows.bat — Run this ONCE to set up everything.
REM Double-click or run from PowerShell.
REM ============================================================

SET PROJECT_DIR=%~dp0
SET BACKEND_DIR=%PROJECT_DIR%backend
SET VENV_PYTHON=%BACKEND_DIR%\venv\Scripts\python.exe

echo.
echo  4CECloud AI Hiring Agent - First Time Setup
echo  ============================================
echo.

REM ── Check Python ─────────────────────────────────────────────
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo  ERROR: Python not found.
    echo.
    echo  Please install Python 3.11:
    echo  https://www.python.org/downloads/release/python-3119/
    echo.
    echo  During install, CHECK these boxes:
    echo    [x] Add python.exe to PATH
    echo    [x] pip
    echo.
    pause
    exit /b 1
)
FOR /F "tokens=*" %%i IN ('python --version') DO echo  Python found: %%i

REM ── Check Node/npm ───────────────────────────────────────────
npm --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo.
    echo  WARNING: npm not found. Frontend will not work.
    echo  Download Node.js LTS from https://nodejs.org/en/download
    echo  Install it, then re-run this script.
    echo.
    echo  Continuing with backend setup only...
) ELSE (
    FOR /F "tokens=*" %%i IN ('npm --version') DO echo  npm found: v%%i
)

REM ── Copy .env if missing ─────────────────────────────────────
IF NOT EXIST "%PROJECT_DIR%.env" (
    IF EXIST "%PROJECT_DIR%.env.example" (
        copy "%PROJECT_DIR%.env.example" "%PROJECT_DIR%.env" >nul
        echo  Created .env from .env.example
    )
) ELSE (
    echo  .env already exists
)

REM ── Create venv ──────────────────────────────────────────────
IF NOT EXIST "%VENV_PYTHON%" (
    echo  Creating Python virtual environment...
    python -m venv "%BACKEND_DIR%\venv"
    IF ERRORLEVEL 1 ( echo  ERROR creating venv & pause & exit /b 1 )
    echo  Virtual environment created.
) ELSE (
    echo  Virtual environment already exists.
)

REM ── Install packages ─────────────────────────────────────────
echo.
echo  Installing Python packages (this takes 2-3 minutes first time)...
"%BACKEND_DIR%\venv\Scripts\pip.exe" install -r "%BACKEND_DIR%\requirements.txt"
IF ERRORLEVEL 1 (
    echo.
    echo  ERROR: Package install failed.
    echo  Try: Make sure you have internet access and Python 3.11
    pause
    exit /b 1
)

REM ── Set POC mode ─────────────────────────────────────────────
echo.
echo  Setting POC mode (free Groq LLM)...
"%VENV_PYTHON%" "%PROJECT_DIR%scripts\switch_provider.py" poc

REM ── Initialize database ───────────────────────────────────────
echo.
echo  Initializing database...
"%VENV_PYTHON%" "%PROJECT_DIR%scripts\seed_mock.py"

REM ── npm install ──────────────────────────────────────────────
npm --version >nul 2>&1
IF NOT ERRORLEVEL 1 (
    echo.
    echo  Installing frontend packages...
    cd /d "%PROJECT_DIR%frontend"
    npm install --silent
    cd /d "%PROJECT_DIR%"
    echo  Frontend packages installed.
)

REM ── Done ─────────────────────────────────────────────────────
echo.
echo  ============================================
echo   Setup complete!
echo  ============================================
echo.
echo  NEXT STEPS:
echo.
echo  1. Set your FREE Groq API key:
echo     Get one at: https://console.groq.com
echo     Then run:
echo       python scripts\switch_provider.py set-groq YOUR_KEY
echo.
echo  2. Start backend:    double-click start_backend.bat
echo  3. Start frontend:   double-click start_frontend.bat
echo.
echo  4. Open: http://localhost:5173
echo.
pause
