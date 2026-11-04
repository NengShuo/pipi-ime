@echo off
chcp 65001 >nul
title Pipi IME - Uninstall
cd /d "%~dp0"

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   Requesting administrator rights...
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1"
