@echo off
cd /d "%~dp0"
py -3.12 -m blossom.oracle.diagnose
pause
