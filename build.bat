@echo off
setlocal
cd /d "%~dp0"
title Build NEXUS Study AI Windows EXE
if not exist ".venv\Scripts\python.exe" (
 echo Run run.bat first to create the virtual environment.
 pause
 exit /b 1
)
echo Running automated tests...
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install pyinstaller
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name NEXUS_Study_AI app.py
if errorlevel 1 goto failed
echo.
echo SUCCESS: dist\NEXUS_Study_AI.exe
pause
exit /b 0
:failed
echo BUILD FAILED. Take a screenshot of the error.
pause
exit /b 1
