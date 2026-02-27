@echo off
REM =============================================================================
REM  Race Timing System — Windows desktop build script
REM =============================================================================
REM  Prerequisites:
REM    Python 3.11+ installed and on PATH
REM    All packages in requirements.txt installed in the active venv
REM
REM  Usage:
REM    Double-click build_desktop.bat  OR  run from a Command Prompt
REM
REM  Output:
REM    dist\RaceTimingSystem\   — distributable folder
REM =============================================================================

setlocal enabledelayedexpansion

echo ============================================================
echo  Race Timing System — Desktop Build (Windows)
echo ============================================================

REM ── 1. Check Python ──────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: python not found on PATH.
    echo Install Python 3.11+ from https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do echo Python: %%v

REM ── 2. Ensure virtual environment ────────────────────────────
if not exist ".venv\" (
    echo Creating virtual environment ...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

REM ── 3. Install / upgrade dependencies ────────────────────────
echo Installing dependencies ...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
python -m pip install --quiet pyinstaller

REM ── 4. Clean previous build ──────────────────────────────────
echo Cleaning previous build artefacts ...
if exist build\  rmdir /s /q build
if exist dist\   rmdir /s /q dist

REM ── 5. Run PyInstaller ───────────────────────────────────────
echo Running PyInstaller ...
pyinstaller race_timing.spec --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller failed.
    pause
    exit /b 1
)

REM ── 6. Copy runtime assets ───────────────────────────────────
set DIST_DIR=dist\RaceTimingSystem
copy .env.example "%DIST_DIR%\.env.example" >nul
if not exist "%DIST_DIR%\data\" mkdir "%DIST_DIR%\data"

echo.
echo ============================================================
echo  Build complete!
echo  Output: %DIST_DIR%
echo.
echo  To run on this machine:
echo    %DIST_DIR%\RaceTimingSystem.exe
echo.
echo  To distribute:
echo    Zip the %DIST_DIR% folder and copy to the target machine.
echo ============================================================
pause

@REM Made with Bob
