@echo off
chcp 65001 > nul
echo ========================================================
echo   Compilador del Simulador Térmico Bioclimático Perú
echo ========================================================
echo.
echo Seleccione el modo de compilación:
echo  [1] Compilar Versión Portable (Un solo archivo .EXE autónomo - Fácil de compartir)
echo  [2] Compilar Versión Carpeta (Apertura ultra-rápida)
echo  [3] Compilar AMBAS versiones y generar Manual PDF
echo.
set /p opt="Ingrese opción [1, 2 o 3]: "

if "%opt%"=="1" goto ONEFILE
if "%opt%"=="2" goto ONEDIR
if "%opt%"=="3" goto BOTH
goto ONEFILE

:ONEFILE
echo.
echo Compilando ejecutable portable (Un solo archivo)...
python -m PyInstaller --noconfirm --onefile --windowed --name "SimuladorTermicoPeru_Portable" --add-data "core;core" --add-data "geometry;geometry" --add-data "ui;ui" --add-data "modelos_sketchup;modelos_sketchup" --hidden-import "reportlab" --hidden-import "reportlab.platypus" --hidden-import "reportlab.lib" --hidden-import "reportlab.pdfgen" main.py
python generate_user_manual_pdf.py
copy /Y Manual_de_Usuario_Simulador_Termico_Peru.pdf dist\
goto END

:ONEDIR
echo.
echo Compilando versión carpeta...
python -m PyInstaller --noconfirm --onedir --windowed --name "SimuladorTermicoPeru" --add-data "core;core" --add-data "geometry;geometry" --add-data "ui;ui" --add-data "modelos_sketchup;modelos_sketchup" --hidden-import "reportlab" --hidden-import "reportlab.platypus" --hidden-import "reportlab.lib" --hidden-import "reportlab.pdfgen" main.py
python generate_user_manual_pdf.py
copy /Y Manual_de_Usuario_Simulador_Termico_Peru.pdf dist\SimuladorTermicoPeru\
goto END

:BOTH
echo.
echo Compilando ambas versiones...
python -m PyInstaller --noconfirm --onedir --windowed --name "SimuladorTermicoPeru" --add-data "core;core" --add-data "geometry;geometry" --add-data "ui;ui" --add-data "modelos_sketchup;modelos_sketchup" --hidden-import "reportlab" --hidden-import "reportlab.platypus" --hidden-import "reportlab.lib" --hidden-import "reportlab.pdfgen" main.py
python -m PyInstaller --noconfirm --onefile --windowed --name "SimuladorTermicoPeru_Portable" --add-data "core;core" --add-data "geometry;geometry" --add-data "ui;ui" --add-data "modelos_sketchup;modelos_sketchup" --hidden-import "reportlab" --hidden-import "reportlab.platypus" --hidden-import "reportlab.lib" --hidden-import "reportlab.pdfgen" main.py
python generate_user_manual_pdf.py
copy /Y Manual_de_Usuario_Simulador_Termico_Peru.pdf dist\
copy /Y Manual_de_Usuario_Simulador_Termico_Peru.pdf dist\SimuladorTermicoPeru\
goto END

:END
echo.
echo ========================================================
echo   ¡Compilación completada!
echo   Archivos generados en la carpeta: dist\
echo ========================================================
pause
