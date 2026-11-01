@echo off
rem news-digest daily run (STEP1 fetch_rss -> STEP2 generate_summary -> STEP3 distribute)
rem NOTE: keep this file ASCII-only. cmd.exe misparses UTF-8 multibyte lines in .bat files
rem (byte offsets drift, and fragments of comments run as commands; this also broke the
rem .env loading loop). Japanese messages come from the Python scripts instead.
chcp 65001 >nul
setlocal enabledelayedexpansion

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
rem Unbuffered output keeps stdout/stderr lines in the log in the order they happened.
set PYTHONUNBUFFERED=1

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

if not exist "data" mkdir "data"
if not exist "logs" mkdir "logs"

rem Choose the Python launcher. Prefer "py" because "python" may point to the
rem empty Microsoft Store shortcut (WindowsApps\python.exe).
where py >nul 2>&1
if errorlevel 1 (
    set "PY=python"
) else (
    set "PY=py -3"
)

rem Load environment variables (SLACK_WEBHOOK_URL etc.) from .env. Skip comment lines (#) and blank lines.
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        set "line=%%A"
        if not "!line:~0,1!"=="#" if not "!line!"=="" (
            set "%%A=%%B"
        )
    )
)

rem Locale-independent date string (YYYY-MM-DD) via Python
for /f %%D in ('%PY% -c "from datetime import date; print(date.today().isoformat())"') do set "TODAY=%%D"
set "LOGFILE=logs\%TODAY%.log"

echo [%TODAY%] news-digest run_daily.bat start >> "%LOGFILE%"

echo [%TODAY%] STEP1: fetch_rss.py >> "%LOGFILE%"
%PY% src\fetch_rss.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo [%TODAY%] STEP1 fetch_rss.py failed. Skipping the remaining steps. >> "%LOGFILE%"
    endlocal
    exit /b 1
)

echo [%TODAY%] STEP2: generate_summary.py >> "%LOGFILE%"
%PY% src\generate_summary.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo [%TODAY%] STEP2 generate_summary.py failed. Skipping the remaining steps. >> "%LOGFILE%"
    echo [%TODAY%] data\articles.json is kept, so you can rerun from STEP2. >> "%LOGFILE%"
    endlocal
    exit /b 1
)

echo [%TODAY%] STEP3: distribute.py >> "%LOGFILE%"
%PY% src\distribute.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo [%TODAY%] STEP3 distribute.py failed. >> "%LOGFILE%"
    endlocal
    exit /b 1
)

echo [%TODAY%] news-digest run_daily.bat finished successfully >> "%LOGFILE%"
endlocal
exit /b 0
