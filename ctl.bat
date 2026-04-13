@echo off
setlocal

set ROOT=%~dp0
set BACKEND_PORT=8001
set FRONTEND_PORT=5177

if "%1"=="" goto help
if "%1"=="start" goto start
if "%1"=="stop" goto stop
if "%1"=="restart" goto restart
if "%1"=="status" goto status
if "%1"=="init" goto init
if "%1"=="logs" goto logs
goto help

:start
echo [START] Ontology Platform
echo.

:: Check if already running
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%BACKEND_PORT% " ^| findstr "LISTENING"') do (
    echo Backend already running on port %BACKEND_PORT% (PID: %%a)
    goto start_frontend
)

echo Starting backend (port %BACKEND_PORT%)...
start "Ontology-Backend" /min cmd /c "cd /d %ROOT%backend && uvicorn app.main:app --reload --port %BACKEND_PORT% --log-level info > %ROOT%backend.log 2>&1"
timeout /t 3 /nobreak >nul

:start_frontend
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%FRONTEND_PORT% " ^| findstr "LISTENING"') do (
    echo Frontend already running on port %FRONTEND_PORT% (PID: %%a)
    goto start_done
)

echo Starting frontend (port %FRONTEND_PORT%)...
start "Ontology-Frontend" /min cmd /c "cd /d %ROOT%frontend && npm run dev > %ROOT%frontend.log 2>&1"
timeout /t 3 /nobreak >nul

:start_done
echo.
echo ========================================
echo   Frontend: http://localhost:%FRONTEND_PORT%
echo   Backend:  http://localhost:%BACKEND_PORT%
echo   API Docs: http://localhost:%BACKEND_PORT%/docs
echo ========================================
goto end

:stop
echo [STOP] Ontology Platform
echo.

:: Kill backend
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%BACKEND_PORT% " ^| findstr "LISTENING"') do (
    echo Stopping backend (PID: %%a)...
    taskkill /F /PID %%a >nul 2>&1
)

:: Kill frontend
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%FRONTEND_PORT% " ^| findstr "LISTENING"') do (
    echo Stopping frontend (PID: %%a)...
    taskkill /F /PID %%a >nul 2>&1
)

timeout /t 2 /nobreak >nul
echo Services stopped.
goto end

:restart
echo [RESTART] Ontology Platform
echo.
call %0 stop
timeout /t 2 /nobreak >nul
call %0 start
goto end

:status
echo [STATUS] Ontology Platform
echo.

set BACKEND_UP=NO
set FRONTEND_UP=NO

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%BACKEND_PORT% " ^| findstr "LISTENING"') do (
    set BACKEND_UP=YES (PID: %%a^)
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%FRONTEND_PORT% " ^| findstr "LISTENING"') do (
    set FRONTEND_UP=YES (PID: %%a^)
)

echo   Backend  (:%BACKEND_PORT%): %BACKEND_UP%
echo   Frontend (:%FRONTEND_PORT%): %FRONTEND_UP%
goto end

:init
echo [INIT] Database
echo.
cd /d %ROOT%backend
echo Running seed.py...
python seed.py
echo Running import_schema.py...
python import_schema.py
echo Done.
goto end

:logs
if "%2"=="backend" (
    type %ROOT%backend.log
) else if "%2"=="frontend" (
    type %ROOT%frontend.log
) else (
    echo Usage: ctl.bat logs [backend^|frontend]
)
goto end

:help
echo.
echo   Ontology Platform Control
echo   ========================
echo.
echo   Usage: ctl.bat [command]
echo.
echo   Commands:
echo     start    - Start backend + frontend
echo     stop     - Stop all services
echo     restart  - Stop then start
echo     status   - Show running status
echo     init     - Init database (seed + import)
echo     logs     - Show logs (ctl.bat logs backend)
echo.

:end
endlocal
