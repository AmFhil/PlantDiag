@echo off
title PlantDiag Web App - Dual Model Edition (v1.7 and v2.0)
color 0A

echo =============================================================
echo   Starting PlantDiag Web Diagnostic Server...
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

echo [1/2] Launching browser to http://localhost:8000 ...
start http://localhost:8000

echo [2/2] Starting Python TFLite server...
"%PYTHON_EXE%" PlantDiag_Web_App\server.py

pause
