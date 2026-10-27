@echo off
setlocal
cd /d "%~dp0"
set "BLOSSOM_PY=%LOCALAPPDATA%\BlossomPlanning\venv\Scripts\python.exe"
if not exist "%BLOSSOM_PY%" (
  py -3.12 -m venv "%LOCALAPPDATA%\BlossomPlanning\venv"
  if errorlevel 1 goto fail
)
"%BLOSSOM_PY%" -c "import streamlit, openpyxl" >nul 2>&1
if errorlevel 1 (
  "%BLOSSOM_PY%" -m pip install -r requirements.txt
  if errorlevel 1 goto fail
)
"%BLOSSOM_PY%" -m streamlit run app.py --server.headless false --server.address 127.0.0.1 --server.port 8501
if errorlevel 1 goto fail
exit /b 0
:fail
 echo Nao foi possivel abrir o Blossom. Verifique o Python 3.12 e a conexao para instalar as dependencias.
 pause
 exit /b 1
