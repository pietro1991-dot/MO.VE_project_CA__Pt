@echo off
title Pulizie Bot - MO.VE
echo ========================================
echo    PULIZIE BOT - MO.VE
echo ========================================
echo.

cd /d "%~dp0Pulizie_BOT_MOVE"

echo Verifico e installo dipendenze...
pip install -r requirements.txt --quiet
if %ERRORLEVEL% NEQ 0 (
    echo [ERRORE] Installazione dipendenze fallita.
    pause
    exit /b 1
)
echo Dipendenze OK.
echo.

echo Avvio bot in corso...
echo.

python bot.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRORE] Il bot si e' arrestato con errore.
    pause
)
