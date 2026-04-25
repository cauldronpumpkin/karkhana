@echo off
echo Starting Idea Refinery...
start /b python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
timeout /t 3 /nobreak >nul
start http://localhost:8000
echo Idea Refinery is running at http://localhost:8000
echo Press Ctrl+C to stop
pause
