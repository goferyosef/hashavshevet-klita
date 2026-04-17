@echo off
echo ===========================
echo  Building קליטה לחשבשבת
echo ===========================

REM Generate icon if missing
if not exist assets\icon.ico (
    echo Generating icon...
    python assets\create_icon.py
)

REM Build exe
pyinstaller ^
    --onefile ^
    --windowed ^
    --icon=assets\icon.ico ^
    --name="קליטה_לחשבשבת" ^
    --add-data="data;data" ^
    --add-data="assets;assets" ^
    main.py

REM Create desktop shortcut
echo Creating desktop shortcut...
python create_shortcut.py

echo.
echo Done! Executable is in dist\
pause
