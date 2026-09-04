@echo off
title Razorpay Agentic Checkout Server
cd /d "%~dp0"
echo.
echo  ===================================================
echo   Razorpay Agentic Checkout - Starting Server...
echo   Dashboard: http://127.0.0.1:8000
echo  ===================================================
echo.
start "" http://127.0.0.1:8000
Scripts\python.exe main.py --serve --port 8000
pause
