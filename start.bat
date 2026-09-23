@echo off
title AgroSense-RAG & LeafSense Launcher
echo ============================================================
echo   Starting AgroSense-RAG & LeafSense Plant Disease System
echo ============================================================
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0start-local.ps1"
