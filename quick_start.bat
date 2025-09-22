@echo off
echo ========================================
echo  YouTube AI Summarizer - Quick Start
echo ========================================
echo.

echo Starting Backend Server...
start "YouTube Summarizer Backend" cmd /k "cd /d %~dp0 && venv\Scripts\activate && cd backend && python start_server.py"

echo Waiting 5 seconds for backend to initialize...
timeout /t 5 /nobreak > nul

echo Starting Frontend Server...
start "YouTube Summarizer Frontend" cmd /k "cd /d %~dp0 && cd frontend && npm run dev"

echo.
echo ========================================
echo  Servers are starting...
echo  Backend: http://localhost:8000
echo  Frontend: http://localhost:5173
echo ========================================
echo.
echo 1. Open http://localhost:5173 in your browser
echo 2. Add your Gemini API key in settings
echo 3. Test with a YouTube URL
echo.
echo Press any key to exit...
pause > nul
