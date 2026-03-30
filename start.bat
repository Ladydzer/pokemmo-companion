@echo off
echo ========================================
echo  PokeMMO Companion v0.1.0
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python non trouve ! Installe Python 3.11+ depuis python.org
    pause
    exit /b 1
)

REM Install deps if needed
if not exist "venv" (
    echo Premier lancement - installation des dependances...
    python -m venv venv
    venv\Scripts\pip install -r requirements.txt
    echo.
    echo Installation terminee !
    echo.
)

REM Run
echo Lancement de PokeMMO Companion...
echo F9 = toggle overlay, F10 = mode etendu
echo.
venv\Scripts\python run.py
pause
