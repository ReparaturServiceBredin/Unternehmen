@echo off
chcp 65001 >nul
title Reparatur Service Bredin - Buchhaltung (dieses Fenster offen lassen)
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Bitte zuerst installieren.bat ausfuehren.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m rsb
pause
