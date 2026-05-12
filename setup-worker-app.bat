@echo off
REM ============================================================================
REM Karkhana Worker App — Windows Quick Start
REM ============================================================================
REM Double-click this file (or run from a command prompt) to set up and launch
REM the Tauri desktop worker application.
REM
REM What it does:
REM   1. Checks for Node.js, Rust, and Git
REM   2. Installs npm dependencies (if needed)
REM   3. Offers to launch the app in dev mode or build a release installer
REM ============================================================================
setlocal enabledelayedexpansion

cd /d "%~dp0worker-app"

echo.
echo === Karkhana Worker App Setup ===
echo.

REM ---- Check prerequisites ----

where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js not found. Install from https://nodejs.org/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node -v') do echo [OK] Node.js %%i

where rustc >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Rust not found. Install from https://rustup.rs/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('rustc --version') do echo [OK] %%i

where cargo >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Cargo not found. Install from https://rustup.rs/
    pause
    exit /b 1
)

REM ---- Check for Visual Studio Build Tools ----
set VSWHERE="%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if exist %VSWHERE% (
    for /f "tokens=*" %%i in ('%VSWHERE% -property installationPath') do set VS_PATH=%%i
    if defined VS_PATH (
        echo [OK] Visual Studio found
    ) else (
        echo [WARN] Visual Studio not detected. Install from:
        echo        https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022
        echo        Select "Desktop development with C++" workload.
    )
) else (
    echo [WARN] Could not check for Visual Studio.
    echo        If builds fail, install: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022
    echo        Select "Desktop development with C++" workload.
)

REM ---- Install npm dependencies ----
echo.
echo === Installing npm dependencies ===
if not exist "node_modules" (
    call npm install
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] npm install failed
        pause
        exit /b 1
    )
) else (
    echo [OK] node_modules exists (delete it and re-run to force reinstall)
)

REM ---- Choose mode ----
echo.
echo ===========================================================================
echo.
echo  Choose an option:
echo   1) Launch app in development mode (hot-reload)
echo   2) Build release installer (.msi)
echo   3) Run Rust tests only
echo   4) Exit
echo.
set /p MODE="Enter 1, 2, 3, or 4: "

if "%MODE%"=="1" (
    echo.
    echo === Launching Tauri dev mode ===
    echo    The app window will open automatically.
    echo    Press Ctrl+C in this terminal to stop.
    echo.
    call npx tauri dev
) else if "%MODE%"=="2" (
    echo.
    echo === Building release installer ===
    echo    This will take several minutes on the first run.
    echo.
    call npx tauri build
    echo.
    if exist "src-tauri\target\release\bundle\msi\*.msi" (
        echo [OK] Installer built! Look in:
        echo     src-tauri\target\release\bundle\msi\
    ) else (
        echo [DONE] Build complete. Check src-tauri\target\release\bundle\ for the installer.
    )
) else if "%MODE%"=="3" (
    echo.
    echo === Running Rust tests ===
    cd src-tauri
    call cargo test
    cd ..
) else (
    echo.
    echo Exiting.
)

echo.
pause
