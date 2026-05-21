@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

REM このスクリプトが Cursor ターミナル内から呼ばれた場合、
REM 新しい cmd ウィンドウで再実行する（I/O リダイレクトによるデッドロック回避）
if "%~1"=="--inner" goto :inner
start "File Sorter Build" cmd /k "cd /d "%~dp0" && "%~f0" --inner"
exit /b 0

:inner
echo =============================================
echo  File Sorter v1.0  ビルドスクリプト
echo =============================================
echo.

REM ---------------------------------------------------------------
REM [1/3] Python を自動検出
REM ---------------------------------------------------------------
echo [1/3] Python を検出中...

set "PYTHON="

REM (1) py ランチャー（Windows 標準推奨）を優先
where py >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%P in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do (
        set "PYTHON=%%P"
    )
)

REM (2) py で見つからなければ PATH 上の python を探す
if not defined PYTHON (
    where python >nul 2>nul
    if not errorlevel 1 (
        for /f "delims=" %%P in ('python -c "import sys;print(sys.executable)" 2^>nul') do (
            set "PYTHON=%%P"
        )
    )
)

REM (3) よくあるインストール場所をフォールバック検索
if not defined PYTHON (
    for %%V in (313 312 311 310 39) do (
        if not defined PYTHON (
            if exist "%LocalAppData%\Programs\Python\Python%%V\python.exe" (
                set "PYTHON=%LocalAppData%\Programs\Python\Python%%V\python.exe"
            )
        )
    )
)

if not defined PYTHON (
    echo [ERROR] Python が見つかりませんでした。
    echo         https://www.python.org/ からインストールしてください。
    pause
    exit /b 1
)

echo     使用する Python: "!PYTHON!"

REM ---------------------------------------------------------------
REM [2/3] PyInstaller を確認（無ければ自動インストール）
REM ---------------------------------------------------------------
echo.
echo [2/3] PyInstaller を確認中...
"!PYTHON!" -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo     PyInstaller が未インストールのため、インストールします...
    "!PYTHON!" -m pip install --upgrade pip
    "!PYTHON!" -m pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] PyInstaller のインストールに失敗しました。
        pause
        exit /b 1
    )
)
echo     OK

REM ---------------------------------------------------------------
REM [3/3] EXE ビルド
REM ---------------------------------------------------------------
cd /d "%~dp0"

echo.
echo [3/3] exe をビルド中（数分かかる場合があります）...
"!PYTHON!" -m PyInstaller --onefile --windowed --name "FileSorter" --distpath "dist" --workpath "build" --specpath "." main.py

if errorlevel 1 (
    echo.
    echo [ERROR] ビルドに失敗しました。上のエラーを確認してください。
    pause
    exit /b 1
)

echo.
echo =============================================
echo  完了！
echo  dist\FileSorter.exe が生成されました。
echo =============================================
echo.
pause
endlocal
