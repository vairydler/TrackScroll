@echo off
rem =============================================================================
rem setup_folders.bat
rem
rem 一括ダウンロードしたファイルを正しいフォルダ構成に再配置するスクリプト。
rem
rem 【使い方】
rem   1. すべての .py / .md ファイルとこの .bat を同じフォルダに置く
rem   2. このファイルをダブルクリック（または bat を実行）
rem   3. 自動的にサブフォルダが作成され、各ファイルが配置される
rem
rem 【生成されるフォルダ構成】
rem   (このファイルのあるフォルダ)/
rem     setup_folders.bat
rem     docs/
rem       gesture_spec_v2_6.md
rem       refactoring_plan.md
rem     src/
rem       main.py
rem       __init__.py          ← 自動生成
rem       app/
rem         __init__.py        ← 自動生成
rem         app_core.py
rem         app_messages.py
rem         console_app.py
rem         gesture_service.py
rem       config/
rem         __init__.py        ← 自動生成
rem         gesture_config.py
rem       core/
rem         __init__.py        ← 自動生成
rem         gesture_action.py
rem         gesture_builder.py
rem         gesture_core.py
rem         gesture_event.py
rem       debug/
rem         __init__.py        ← 自動生成
rem         input_driver_debug.py
rem         output_driver_debug.py
rem       drivers/
rem         __init__.py        ← 自動生成
rem         input_driver.py
rem         output_driver.py
rem         vk_codes.py
rem
rem 【起動方法】
rem   python src\main.py --console
rem
rem 【デバッグスクリプトの実行方法】
rem   python -m src.debug.input_driver_debug
rem   python -m src.debug.output_driver_debug
rem =============================================================================

setlocal
set BASE=%~dp0

echo [setup_folders] フォルダを作成しています...

rem フォルダ作成
if not exist "%BASE%docs"           mkdir "%BASE%docs"
if not exist "%BASE%src"            mkdir "%BASE%src"
if not exist "%BASE%src\app"        mkdir "%BASE%src\app"
if not exist "%BASE%src\config"     mkdir "%BASE%src\config"
if not exist "%BASE%src\core"       mkdir "%BASE%src\core"
if not exist "%BASE%src\drivers"    mkdir "%BASE%src\drivers"
if not exist "%BASE%src\debug"      mkdir "%BASE%src\debug"

echo [setup_folders] __init__.py を生成しています...

rem __init__.py を生成（存在しない場合のみ）
if not exist "%BASE%src\__init__.py"            type nul > "%BASE%src\__init__.py"
if not exist "%BASE%src\app\__init__.py"        type nul > "%BASE%src\app\__init__.py"
if not exist "%BASE%src\config\__init__.py"     type nul > "%BASE%src\config\__init__.py"
if not exist "%BASE%src\core\__init__.py"       type nul > "%BASE%src\core\__init__.py"
if not exist "%BASE%src\drivers\__init__.py"    type nul > "%BASE%src\drivers\__init__.py"
if not exist "%BASE%src\debug\__init__.py"      type nul > "%BASE%src\debug\__init__.py"

echo [setup_folders] ファイルを移動しています...

rem --- docs/ ---
call :move_file "gesture_spec_v2_6.md"  "docs"
call :move_file "refactoring_plan.md"   "docs"

rem --- src/ (ルート) ---
call :move_file "main.py"               "src"

rem --- src/app/ ---
call :move_file "app_core.py"           "src\app"
call :move_file "app_messages.py"       "src\app"
call :move_file "console_app.py"        "src\app"
call :move_file "gesture_service.py"    "src\app"

rem --- src/config/ ---
call :move_file "gesture_config.py"     "src\config"

rem --- src/core/ ---
call :move_file "gesture_action.py"     "src\core"
call :move_file "gesture_builder.py"    "src\core"
call :move_file "gesture_core.py"       "src\core"
call :move_file "gesture_event.py"      "src\core"

rem --- src/drivers/ ---
call :move_file "input_driver.py"       "src\drivers"
call :move_file "output_driver.py"      "src\drivers"
call :move_file "vk_codes.py"           "src\drivers"

rem --- src/debug/ ---
call :move_file "input_driver_debug.py"     "src\debug"
call :move_file "output_driver_debug.py"    "src\debug"

echo.
echo [setup_folders] 完了しました。
echo.
echo 起動方法:
echo   python src\main.py --console
echo.
pause
endlocal
exit /b 0

rem =============================================================================
rem サブルーチン: ファイルを指定フォルダへ移動
rem   %1 = ファイル名
rem   %2 = 移動先フォルダ（BASE からの相対パス）
rem =============================================================================
:move_file
set SRC=%BASE%%~1
set DST=%BASE%%~2\%~1
if exist "%SRC%" (
    move /Y "%SRC%" "%DST%" >nul
    echo   moved: %~1 -^> %~2\
) else (
    echo   [SKIP] %~1 が見つかりません（既に移動済みか存在しない）
)
exit /b 0
