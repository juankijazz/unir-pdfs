@echo off
REM Compila unir_pdfs.exe (requiere Python 3 instalado en Windows)
python -m pip install -r requirements.txt || goto :err
python -m PyInstaller --onefile --windowed --name unir_pdfs unir_pdfs.py || goto :err
echo.
echo Listo: dist\unir_pdfs.exe
pause
exit /b 0
:err
echo Error en la compilacion.
pause
exit /b 1
