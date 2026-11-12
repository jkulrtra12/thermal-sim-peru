@echo off
cd /d "%~dp0"

:: 1. Si existe Python en PATH, ejecutar codigo fuente
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python main.py
    if %ERRORLEVEL% EQU 0 goto :fin
)

:: 2. Si existe py launcher
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py main.py
    if %ERRORLEVEL% EQU 0 goto :fin
)

:: 3. Ejecutar la aplicacion compilada nativa .exe
if exist "dist\SimuladorTermicoPeru\SimuladorTermicoPeru.exe" (
    echo Iniciando Simulador Termico (Ejecutable Nativo)...
    start "" "dist\SimuladorTermicoPeru\SimuladorTermicoPeru.exe"
    goto :fin
)

echo [ERROR] No se pudo encontrar Python ni el ejecutable compilado.
pause

:fin
