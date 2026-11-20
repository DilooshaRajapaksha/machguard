@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0backend\install_usb.ps1"
if errorlevel 1 pause
