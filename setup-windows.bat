@echo off
REM AMC-TRADER Windows Installation Script
REM This script sets up AMC-TRADER on Windows systems

setlocal EnableDelayedExpansion
title AMC-TRADER Installation

set PROJECT_NAME=AMC-TRADER
set REPO_URL=https://github.com/yourusername/AMC-TRADER.git
set INSTALL_DIR=%USERPROFILE%\%PROJECT_NAME%
set PYTHON_MIN_VERSION=3.9
set NODE_MIN_VERSION=18

echo.
echo ========================================
echo AMC-TRADER Windows Installation
echo ========================================
echo.
echo This script will install AMC-TRADER on your Windows system
echo Installation directory: %INSTALL_DIR%
echo.

:CONFIRM
set /p CONTINUE="Continue with installation? (y/N): "
if /i "%CONTINUE%" neq "y" (
    echo Installation cancelled
    goto END
)

echo.
echo ========================================
echo Checking System Requirements
echo ========================================

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python 3 not found
    echo Please install Python 3.%PYTHON_MIN_VERSION% or higher from https://www.python.org/downloads/
    goto ERROR
) else (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v
    echo SUCCESS: Python !PYTHON_VERSION! detected
)

REM Check Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js not found
    echo Please install Node.js %NODE_MIN_VERSION% or higher from https://nodejs.org/
    goto ERROR
) else (
    for /f %%v in ('node --version 2^>^&1') do set NODE_VERSION=%%v
    echo SUCCESS: Node.js !NODE_VERSION! detected
)

REM Check npm
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: npm not found
    goto ERROR
) else (
    echo SUCCESS: npm detected
)

REM Check pip
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: pip not found
    goto ERROR
) else (
    echo SUCCESS: pip detected
)

REM Check git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: git not found
    echo Please install Git from https://git-scm.com/downloads
    goto ERROR
) else (
    echo SUCCESS: git detected
)

echo.
echo ========================================
echo Setting Up Repository
echo ========================================

if exist "%INSTALL_DIR%" (
    echo Directory exists, updating repository...
    cd /d "%INSTALL_DIR%"
    git pull origin main
    if %errorlevel% neq 0 goto ERROR
) else (
    echo Cloning repository...
    git clone "%REPO_URL%" "%INSTALL_DIR%"
    if %errorlevel% neq 0 goto ERROR
    cd /d "%INSTALL_DIR%"
)

echo.
echo ========================================
echo Setting Up Backend (Python)
echo ========================================

REM Create virtual environment
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 goto ERROR
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 goto ERROR

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 goto ERROR

REM Install backend dependencies
echo Installing Python dependencies...
cd backend
pip install -r requirements.txt
if %errorlevel% neq 0 goto ERROR
cd ..

echo.
echo ========================================
echo Setting Up Frontend (Node.js)
echo ========================================

cd frontend
echo Installing Node.js dependencies...
npm install
if %errorlevel% neq 0 goto ERROR

echo Building frontend...
npm run build
if %errorlevel% neq 0 goto ERROR
cd ..

echo.
echo ========================================
echo Setting Up Environment Configuration
echo ========================================

if not exist ".env" (
    if exist ".env.template" (
        copy .env.template .env >nul
        echo Environment file created from template
    ) else (
        echo Creating basic .env file...
        echo # Database Configuration > .env
        echo DATABASE_URL=postgresql://localhost:5432/amc_trader >> .env
        echo. >> .env
        echo # Redis Configuration >> .env
        echo REDIS_URL=redis://localhost:6379/0 >> .env
        echo. >> .env
        echo # API Keys (REQUIRED - Replace with your actual keys) >> .env
        echo ALPACA_API_KEY=your_alpaca_api_key_here >> .env
        echo ALPACA_SECRET_KEY=your_alpaca_secret_key_here >> .env
        echo ALPACA_BASE_URL=https://paper-api.alpaca.markets >> .env
        echo POLYGON_API_KEY=your_polygon_api_key_here >> .env
        echo CLAUDE_API_KEY=your_claude_api_key_here >> .env
        echo. >> .env
        echo # Application Configuration >> .env
        echo ENVIRONMENT=development >> .env
        echo DEBUG=true >> .env
    )
) else (
    echo Environment file already exists
)

echo.
echo ========================================
echo Creating Launch Scripts
echo ========================================

REM Backend launch script
echo @echo off > start-backend.bat
echo cd /d "%%~dp0" >> start-backend.bat
echo call venv\Scripts\activate.bat >> start-backend.bat
echo cd backend >> start-backend.bat
echo echo Starting AMC-TRADER Backend... >> start-backend.bat
echo echo Backend will be available at http://localhost:8000 >> start-backend.bat
echo python -m uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload >> start-backend.bat

REM Frontend launch script
echo @echo off > start-frontend.bat
echo cd /d "%%~dp0\frontend" >> start-frontend.bat
echo echo Starting AMC-TRADER Frontend... >> start-frontend.bat
echo echo Frontend will be available at http://localhost:3000 >> start-frontend.bat
echo npm run dev >> start-frontend.bat

REM Combined launch script
echo @echo off > start-amc-trader.bat
echo cd /d "%%~dp0" >> start-amc-trader.bat
echo. >> start-amc-trader.bat
echo echo Starting AMC-TRADER System... >> start-amc-trader.bat
echo echo This will start both backend and frontend services. >> start-amc-trader.bat
echo echo. >> start-amc-trader.bat
echo. >> start-amc-trader.bat
echo REM Check if .env file has been configured >> start-amc-trader.bat
echo findstr "your_.*_api_key_here" .env ^>nul 2^>nul >> start-amc-trader.bat
echo if not errorlevel 1 ^( >> start-amc-trader.bat
echo     echo WARNING: Please configure your API keys in .env file first! >> start-amc-trader.bat
echo     echo    Edit .env and replace placeholder values with your actual API keys. >> start-amc-trader.bat
echo     echo. >> start-amc-trader.bat
echo     pause >> start-amc-trader.bat
echo ^) >> start-amc-trader.bat
echo. >> start-amc-trader.bat
echo echo Starting backend server... >> start-amc-trader.bat
echo start "AMC-TRADER Backend" cmd /c start-backend.bat >> start-amc-trader.bat
echo. >> start-amc-trader.bat
echo timeout /t 5 /nobreak ^>nul >> start-amc-trader.bat
echo. >> start-amc-trader.bat
echo echo Starting frontend server... >> start-amc-trader.bat
echo start "AMC-TRADER Frontend" cmd /c start-frontend.bat >> start-amc-trader.bat
echo. >> start-amc-trader.bat
echo timeout /t 5 /nobreak ^>nul >> start-amc-trader.bat
echo. >> start-amc-trader.bat
echo echo. >> start-amc-trader.bat
echo echo AMC-TRADER is now running! >> start-amc-trader.bat
echo echo. >> start-amc-trader.bat
echo echo    Frontend: http://localhost:3000 >> start-amc-trader.bat
echo echo    Backend:  http://localhost:8000 >> start-amc-trader.bat
echo echo    API Docs: http://localhost:8000/docs >> start-amc-trader.bat
echo echo. >> start-amc-trader.bat
echo start http://localhost:3000 >> start-amc-trader.bat
echo echo Press any key to exit... >> start-amc-trader.bat
echo pause ^>nul >> start-amc-trader.bat

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo SUCCESS: AMC-TRADER has been successfully installed
echo.
echo Next steps:
echo 1. Edit %INSTALL_DIR%\.env with your API keys
echo 2. Run: %INSTALL_DIR%\start-amc-trader.bat
echo.
echo API Keys needed:
echo • Alpaca Trading API (for trading)
echo • Polygon API (for market data)  
echo • Claude API (optional, for AI analysis)
echo.
echo Happy Trading!
echo.
goto END

:ERROR
echo.
echo ========================================
echo Installation Failed!
echo ========================================
echo An error occurred during installation.
echo Please check the error messages above and try again.
echo.

:END
pause