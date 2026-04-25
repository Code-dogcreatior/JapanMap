@echo off
setlocal

REM ============================================
REM Start map.py + mapdown + optional frontend
REM ============================================

set "BASE_DIR=%~dp0"
set "PY_EXE=D:\Anaconda\python.exe"

REM Optional: set path to extra frontend (must contain package.json)
REM Example: set "EXTRA_FRONTEND_DIR=E:\fumigo\your-frontend"
set "EXTRA_FRONTEND_DIR="
set "EXTRA_FRONTEND_CMD=npm run dev"

echo [1/3] Start Python backend map.py ...
if exist "%PY_EXE%" (
    start "map.py (Flask:5000)" cmd /k "cd /d ""%BASE_DIR%"" && ""%PY_EXE%"" map.py"
) else (
    echo [WARN] PY_EXE not found: %PY_EXE%
    echo [WARN] Fallback to system python.
    start "map.py (Flask:5000)" cmd /k "cd /d ""%BASE_DIR%"" && python map.py"
)

echo [2/3] Start mapdown frontend ...
start "mapdown (Vite)" cmd /k "cd /d ""%BASE_DIR%mapdown"" && npm run dev"

echo [3/3] Start optional frontend if configured ...
if not "%EXTRA_FRONTEND_DIR%"=="" (
    if exist "%EXTRA_FRONTEND_DIR%\package.json" (
        start "extra-frontend" cmd /k "cd /d ""%EXTRA_FRONTEND_DIR%"" && %EXTRA_FRONTEND_CMD%"
    ) else (
        echo [WARN] package.json not found in EXTRA_FRONTEND_DIR. Skipped.
    )
) else (
    echo [INFO] EXTRA_FRONTEND_DIR is empty. Optional frontend skipped.
)

echo.
echo Launch commands sent. Check new windows for logs.
endlocal
