@echo off
echo =================================================================
echo       STOPPING FRAUDSHIELD AI BACKEND SERVICE
echo =================================================================
echo Terminating any process bound to port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
    taskkill /f /pid %%a 2>nul
)
echo Cleaned up port 8000 and stopped background services.
echo =================================================================
pause

