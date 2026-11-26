@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "VENV_PY=..\Anime Game Automation Tools\.venv\Scripts\python.exe"
if exist "%VENV_PY%" (
    "%VENV_PY%" main.py %*
) else (
    python main.py %*
)
