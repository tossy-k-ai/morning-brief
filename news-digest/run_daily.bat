@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

if not exist "data" mkdir "data"
if not exist "logs" mkdir "logs"

rem .envから環境変数を読み込む（SLACK_WEBHOOK_URL等）。コメント行(#)と空行は無視する。
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        set "line=%%A"
        if not "!line:~0,1!"=="#" if not "!line!"=="" (
            set "%%A=%%B"
        )
    )
)

rem ロケールに依存しない日付文字列 (YYYY-MM-DD) をPythonで取得する
for /f %%D in ('python -c "from datetime import date; print(date.today().isoformat())"') do set "TODAY=%%D"
set "LOGFILE=logs\%TODAY%.log"

echo [%TODAY%] news-digest run_daily.bat 開始 >> "%LOGFILE%"

echo [%TODAY%] STEP1: fetch_rss.py >> "%LOGFILE%"
python src\fetch_rss.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo [%TODAY%] STEP1 (fetch_rss.py) が失敗しました。以降のSTEPを中止します。 >> "%LOGFILE%"
    endlocal
    exit /b 1
)

echo [%TODAY%] STEP2: generate_summary.py >> "%LOGFILE%"
python src\generate_summary.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo [%TODAY%] STEP2 (generate_summary.py) が失敗しました。以降のSTEPを中止します。 >> "%LOGFILE%"
    echo [%TODAY%] articles.json は残っているので、STEP2からの再実行が可能です。 >> "%LOGFILE%"
    endlocal
    exit /b 1
)

echo [%TODAY%] STEP3: distribute.py >> "%LOGFILE%"
python src\distribute.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo [%TODAY%] STEP3 (distribute.py) が失敗しました。 >> "%LOGFILE%"
    endlocal
    exit /b 1
)

echo [%TODAY%] news-digest run_daily.bat 正常終了 >> "%LOGFILE%"
endlocal
exit /b 0
