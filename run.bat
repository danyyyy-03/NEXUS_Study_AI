@echo off
setlocal
cd /d "%~dp0"
title NEXUS Study AI - Setup and Launch
py -3.12 --version >nul 2>&1
if errorlevel 1 (
 echo ERROR: Python 3.12 was not found.
 echo Install Python 3.12 from https://www.python.org/downloads/
 pause
 exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
 echo Creating a local Python environment...
 py -3.12 -m venv ".venv"
 if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -c "import pypdf, docx" >nul 2>&1
if errorlevel 1 (
 echo Installing pypdf and python-docx for document reading...
 ".venv\Scripts\python.exe" -m pip install -r requirements.txt
 if errorlevel 1 goto failed
)
echo Launching NEXUS Study AI...
".venv\Scripts\python.exe" app.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo Something went wrong. Take a screenshot of this window.
pause
exit /b 1
