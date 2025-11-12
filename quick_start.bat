@echo off
REM Quick Start Script for Telegram Backup Tool (Windows)

echo ==========================================
echo Telegram Group Backup ^& Recovery Tool
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo X Python is not installed. Please install Python 3.7 or higher.
    pause
    exit /b 1
)

echo + Python is installed

REM Check if .env file exists
if not exist .env (
    echo.
    echo ! No .env file found. Creating from template...
    copy .env.example .env
    echo.
    echo Please edit the .env file with your Telegram API credentials:
    echo    1. Go to https://my.telegram.org
    echo    2. Get your API_ID and API_HASH
    echo    3. Edit .env and fill in your credentials
    echo.
    pause
)

REM Load environment variables from .env
for /f "tokens=*" %%a in ('type .env ^| findstr /v "^#"') do set %%a

REM Check if credentials are set
if "%TELEGRAM_API_ID%"=="" (
    echo X Telegram credentials not set in .env file
    pause
    exit /b 1
)
if "%TELEGRAM_API_HASH%"=="" (
    echo X Telegram credentials not set in .env file
    pause
    exit /b 1
)

echo + Telegram credentials loaded

REM Check if dependencies are installed
echo.
echo Checking dependencies...
python -c "import telethon" >nul 2>&1
if errorlevel 1 (
    echo ! Dependencies not installed. Installing...
    pip install -r requirements.txt
) else (
    echo + Dependencies are installed
)

echo.
echo ==========================================
echo Setup complete! Choose an option:
echo ==========================================
echo.
echo 1^) Retrieve deleted messages ^(within 48 hours^)
echo 2^) Backup current messages
echo 3^) Restore messages to new group
echo 4^) Exit
echo.

set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" (
    echo.
    python 1_retrieve_deleted_messages.py
) else if "%choice%"=="2" (
    echo.
    python 2_backup_current_messages.py
) else if "%choice%"=="3" (
    echo.
    python 3_restore_messages.py
) else if "%choice%"=="4" (
    echo Exiting...
    exit /b 0
) else (
    echo Invalid choice
    pause
    exit /b 1
)

pause
