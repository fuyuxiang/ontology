@echo off
echo ========================================
echo   Ontology Platform - Startup
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] Installing backend dependencies...
cd /d "%~dp0backend"
pip install -r requirements.txt --quiet 2>nul
echo Dependencies ready.
echo.

echo [2/3] Starting backend (port 8001)...
start "Ontology-Backend" cmd /k "cd /d %~dp0backend && uvicorn app.main:app --reload --port 8001 --log-level info"
timeout /t 3 /nobreak >nul

echo [3/3] Starting frontend (port 5177)...
start "Ontology-Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo   Ready!
echo   Frontend: http://localhost:5177
echo   Backend:  http://localhost:8001
echo   API Docs: http://localhost:8001/docs
echo ========================================
echo.
echo Press any key to open browser...
pause >nul
start http://localhost:5177
