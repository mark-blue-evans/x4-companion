@echo off
REM Double-click launcher for X4 Companion.
REM Activates the venv and starts the app from this directory.
cd /d "%~dp0"
start "" "%~dp0.venv\Scripts\pythonw.exe" -m x4_companion
