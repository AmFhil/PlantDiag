@echo off
title PlantDiag Web App - Version 2.1 (v1.7-based)
color 0A

echo =============================================================
echo   Starting PlantDiag Web App v2.1...
echo   Built by Fhinovax(TM)
echo =============================================================
echo.

set PYTHON_EXE=tools\naija_train_env\Scripts\python.exe

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python environment not found at: %PYTHON_EXE%
    echo Please make sure the tools\naija_train_env folder exists.
    pause
    exit /b 1
)

echo [1/2] Launching browser to http://localhost:8000/home.html ...
start http://localhost:8000/home.html

echo [2/2] Starting Python TFLite server...
"%PYTHON_EXE%" webapp_v2.1\server.py

pause
