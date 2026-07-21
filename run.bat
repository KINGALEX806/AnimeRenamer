@echo off
cd /d "%~dp0"
powershell -WindowStyle Hidden -Command "& '%~dp0.venv\Scripts\pythonw.exe' '%~dp0main.pyw'"