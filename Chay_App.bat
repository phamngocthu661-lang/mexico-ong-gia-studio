@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
chcp 65001 >nul
title Mexico Ong Gia Studio - Workstation

:: Tu dong go bo nhan chan file tai tu Internet (Smart App Control / Mark-of-the-Web)
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '%~dp0' -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue" >nul 2>&1

set "PYTHON_EXE="
if exist "%~dp0python_path.txt" (
    set /p SAVED_PY=<"%~dp0python_path.txt"
    if exist "!SAVED_PY!" set "PYTHON_EXE=!SAVED_PY!"
)
if not defined PYTHON_EXE (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
)
if not defined PYTHON_EXE (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
if not defined PYTHON_EXE (
    if exist "C:\Program Files\Python311\python.exe" set "PYTHON_EXE=C:\Program Files\Python311\python.exe"
)

if defined PYTHON_EXE (
    for %%D in ("%PYTHON_EXE%") do set "PY_DIR=%%~dpD"
    set "PATH=%PY_DIR%;%PY_DIR%Scripts;%~dp0bin;%PATH%"
    "%PYTHON_EXE%" "%~dp0main.py"
) else (
    start "" "%~dp0Mexico_Ong_Gia.exe"
)
