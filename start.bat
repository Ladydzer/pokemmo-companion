@echo off
echo ========================================
echo  PokeMMO Companion v0.1.0
echo ========================================
echo.

REM Find Python (try python first, then py)
set PYTHON=python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    set PYTHON=py
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo Python non trouve ! Installe Python 3.11+ depuis python.org
        echo N'oublie pas de cocher "Add to PATH" pendant l'installation !
        pause
        exit /b 1
    )
)

REM Install deps if needed
if not exist "venv" (
    echo Premier lancement - creation environnement virtuel...
    %PYTHON% -m venv venv
    echo Installation des dependances...
    venv\Scripts\pip install -r requirements.txt
    echo.
    echo Installation terminee !
    echo.
)

REM Run
echo Lancement de PokeMMO Companion...
echo F9 = toggle overlay, F10 = mode etendu, F11 = debug OCR
echo.
venv\Scripts\python run.py
pause
