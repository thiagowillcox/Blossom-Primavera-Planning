@echo off
cd /d "%~dp0"
if exist "%LOCALAPPDATA%\BlossomPlanning\venv\Scripts\python.exe" (
  "%LOCALAPPDATA%\BlossomPlanning\venv\Scripts\python.exe" -m blossom.oracle --enviar-rascunho
) else if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m blossom.oracle --enviar-rascunho
) else (
  echo Abra primeiro Abrir_Blossom.bat para instalar as dependencias do programa.
)
pause
