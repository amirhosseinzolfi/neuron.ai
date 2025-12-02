@echo off
REM Blue Psychology Test API - Startup Script for Windows
REM This script checks dependencies and starts the FastAPI server

echo ==================================================
echo Blue Psychology Test API Server
echo ==================================================
echo.

REM Check if Python is installed
echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% found
echo.

REM Check if pip is installed
echo Checking pip installation...
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pip is not installed
    echo Please install pip
    pause
    exit /b 1
)
echo [OK] pip is installed
echo.

REM Check if FastAPI is installed
echo Checking FastAPI installation...
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] FastAPI not found
    echo Installing dependencies...
    pip install -r requirements.txt
    
    if %errorlevel% equ 0 (
        echo [OK] Dependencies installed successfully
    ) else (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
) else (
    echo [OK] FastAPI is installed
)
echo.

REM Check if database is initialized
echo Checking database...
if not exist "bot.db" (
    echo [WARNING] Database not found, initializing...
    python -c "import db; db.init_db()"
    echo [OK] Database initialized
) else (
    echo [OK] Database found
)
echo.

REM Ask for port
set /p PORT="Which port would you like to use? [default: 8000]: "
if "%PORT%"=="" set PORT=8000
echo.

REM Start server
echo ==================================================
echo Starting API Server on port %PORT%
echo ==================================================
echo.
echo Access points:
echo   API Base:          http://localhost:%PORT%
echo   Documentation:     http://localhost:%PORT%/docs
echo   Alternative Docs:  http://localhost:%PORT%/redoc
echo   Health Check:      http://localhost:%PORT%/health
echo.
echo Press Ctrl+C to stop the server
echo ==================================================
echo.

REM Change to api directory
cd /d "%~dp0\.."

REM Start the server
python api.py

pause
