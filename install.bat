@echo off
title PokeMMO Companion - Installateur
color 0B
echo.
echo  ============================================
echo   PokeMMO Companion - Installation automatique
echo  ============================================
echo.

REM === Check Python ===
echo [1/5] Verification de Python...
set PYTHON=python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    set PYTHON=py
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo  PYTHON NON TROUVE !
        echo  Telecharge Python 3.12 depuis : https://www.python.org/downloads/
        echo  IMPORTANT : Coche "Add python.exe to PATH" pendant l'installation !
        echo.
        echo  Appuie sur une touche pour ouvrir la page de telechargement...
        pause >nul
        start https://www.python.org/downloads/
        echo.
        echo  Apres installation, FERME ce terminal et relance install.bat
        pause
        exit /b 1
    )
)
echo  Python OK !

REM === Check Git ===
echo [2/5] Verification de Git...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  GIT NON TROUVE !
    echo  Telecharge Git depuis : https://git-scm.com/download/win
    echo.
    echo  Appuie sur une touche pour ouvrir la page...
    pause >nul
    start https://git-scm.com/download/win
    echo.
    echo  Apres installation, FERME ce terminal et relance install.bat
    pause
    exit /b 1
)
echo  Git OK !

REM === Check Tesseract ===
echo [3/5] Verification de Tesseract OCR...
set TESS_OK=0
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" set TESS_OK=1
if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" set TESS_OK=1
tesseract --version >nul 2>&1
if %errorlevel% equ 0 set TESS_OK=1

if %TESS_OK% equ 0 (
    echo.
    echo  TESSERACT OCR NON TROUVE !
    echo  C'est necessaire pour lire le texte du jeu (overlay).
    echo  L'app desktop fonctionne sans, mais l'overlay OCR sera desactive.
    echo.
    echo  Pour installer : https://github.com/UB-Mannheim/tesseract/wiki
    echo  (Installe dans C:\Program Files\Tesseract-OCR\)
    echo.
    echo  On continue l'installation quand meme...
    echo.
) else (
    echo  Tesseract OK !
)

REM === Create virtual environment ===
echo [4/5] Creation de l'environnement Python...
if not exist "venv" (
    %PYTHON% -m venv venv
    if %errorlevel% neq 0 (
        echo  Erreur creation venv !
        pause
        exit /b 1
    )
)
echo  Environnement OK !

REM === Install dependencies ===
echo [5/5] Installation des dependances (ca peut prendre 1-2 min)...
venv\Scripts\pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo  Erreur installation dependances !
    echo  Essaie : venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)
echo  Dependances OK !

echo.
echo  ============================================
echo   INSTALLATION TERMINEE !
echo  ============================================
echo.
echo  Pour lancer l'app desktop (recommande) :
echo    venv\Scripts\python companion.py
echo.
echo  Pour lancer l'overlay (par-dessus le jeu) :
echo    venv\Scripts\python run.py
echo    (lance le terminal en Administrateur pour les raccourcis clavier)
echo.
echo  Raccourcis overlay : F9=afficher/masquer, F10=mode etendu, F11=debug
echo.
echo  ============================================
echo.

REM === Ask to launch ===
set /p LAUNCH="Lancer l'app desktop maintenant ? (O/N) : "
if /i "%LAUNCH%"=="O" (
    echo Lancement de PokeMMO Companion...
    venv\Scripts\python companion.py
) else (
    echo OK, tu peux lancer plus tard avec : venv\Scripts\python companion.py
)

pause
