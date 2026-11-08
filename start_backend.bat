@echo off
title FraudShield AI Backend Guard Service
cd /d "c:\Users\saiab\OneDrive\Desktop\GNN-Based Fraud Detection\Financial-Fraud-Detection"
echo =================================================================
echo       FRAUDSHIELD AI BACKEND - AUTO-RESTART GUARDIAN
echo =================================================================
echo Port: 8000 | Host: 0.0.0.0 (Accessible via Wi-Fi & USB)
echo If the server ever crashes, it will automatically restart!
echo To stop: Close this window or run stop_backend.bat
echo =================================================================
echo.

:loop
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
echo.
echo [Service Notice] Server stopped or exited. Auto-restarting in 3 seconds...
timeout /t 3 >nul
goto loop

