@echo off
cd /d "%~dp0"
python launch_web_app.py
if errorlevel 1 py launch_web_app.py
pause
