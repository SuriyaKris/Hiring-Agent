@echo off
REM ============================================================
REM start_backend.bat
REM Double-click this file OR run it from PowerShell to start
REM the backend. It creates the venv if needed.
REM ============================================================

SET PROJECT_DIR=%~dp0
SET BACKEND_DIR=%PROJECT_DIR%backend
SET VENV_PYTHON=%BACKEND_DIR%\venv\Scripts\python.exe
SET VENV_PIP=%BACKEND_DIR%\venv\Scripts\pip.exe

echo.
echo  4CECloud AI Hiring Agent - Backend Startup
echo  ==========================================

REM Step 1: Check Python
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo  ERROR: Python not found.
    echo  Download Python 3.11 from https://www.python.org/downloads/
    echo  Make sure to check "Add python.exe to PATH" during install.
    pause
    exit /b 1
)

REM Step 2: Create venv if missing
IF NOT EXIST "%VENV_PYTHON%" (
    echo  Creating virtual environment...
    python -m venv "%BACKEND_DIR%\venv"
    IF ERRORLEVEL 1 (
        echo  ERROR: Failed to create venv.
        pause
        exit /b 1
    )
    echo  Virtual environment created.
)

REM Step 3: Install dependencies
echo  Installing/verifying packages...
"%VENV_PIP%" install -r "%BACKEND_DIR%\requirements.txt" --quiet
IF ERRORLEVEL 1 (
    echo  ERROR: pip install failed. See error above.
    pause
    exit /b 1
)
echo  Packages OK.

REM Step 4: Seed mock data if DB doesn't exist
IF NOT EXIST "%BACKEND_DIR%\hiring_agent.db" (
    echo  Seeding mock candidates...
    "%VENV_PYTHON%" "%PROJECT_DIR%scripts\seed_mock.py"
)

REM Step 5: Start server
echo.
echo  Starting backend on http://localhost:8000
echo  API docs: http://localhost:8000/docs
echo  Press Ctrl+C to stop.
echo.
cd /d "%BACKEND_DIR%"
"%VENV_PYTHON%" -m uvicorn main:app --reload --port 8000
pause
