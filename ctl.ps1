# Ontology Platform Control Script
# Usage: .\ctl.ps1 start | stop | restart | status | init

param([string]$Command = "help")

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKEND_PORT = 8001
$FRONTEND_PORT = 5177

function Get-PortPID($port) {
    $line = netstat -ano | Select-String ":$port\s" | Select-String "LISTENING" | Select-Object -First 1
    if ($line) {
        return ($line -split '\s+')[-1]
    }
    return $null
}

function Start-Services {
    Write-Host "[START] Ontology Platform" -ForegroundColor Cyan
    Write-Host ""

    $bpid = Get-PortPID $BACKEND_PORT
    if ($bpid) {
        Write-Host "  Backend already running on port $BACKEND_PORT (PID: $bpid)" -ForegroundColor Yellow
    } else {
        Write-Host "  Starting backend (port $BACKEND_PORT)..."
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd /d $ROOT\backend && venv\Scripts\python.exe -m uvicorn app.main:app --reload --port $BACKEND_PORT --log-level info" -WindowStyle Minimized
        Start-Sleep -Seconds 3
        Write-Host "  Backend started." -ForegroundColor Green
    }

    $fpid = Get-PortPID $FRONTEND_PORT
    if ($fpid) {
        Write-Host "  Frontend already running on port $FRONTEND_PORT (PID: $fpid)" -ForegroundColor Yellow
    } else {
        Write-Host "  Starting frontend (port $FRONTEND_PORT)..."
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd /d $ROOT\frontend && npm run dev" -WindowStyle Minimized
        Start-Sleep -Seconds 3
        Write-Host "  Frontend started." -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "  ========================================" -ForegroundColor Cyan
    Write-Host "  Frontend: http://localhost:$FRONTEND_PORT"
    Write-Host "  Backend:  http://localhost:$BACKEND_PORT"
    Write-Host "  API Docs: http://localhost:$BACKEND_PORT/docs"
    Write-Host "  ========================================" -ForegroundColor Cyan
}

function Stop-Services {
    Write-Host "[STOP] Ontology Platform" -ForegroundColor Cyan
    Write-Host ""

    $bpid = Get-PortPID $BACKEND_PORT
    if ($bpid) {
        Write-Host "  Stopping backend (PID: $bpid)..."
        Stop-Process -Id $bpid -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host "  Backend not running." -ForegroundColor Gray
    }

    $fpid = Get-PortPID $FRONTEND_PORT
    if ($fpid) {
        Write-Host "  Stopping frontend (PID: $fpid)..."
        Stop-Process -Id $fpid -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host "  Frontend not running." -ForegroundColor Gray
    }

    Start-Sleep -Seconds 2
    Write-Host "  Services stopped." -ForegroundColor Green
}

function Show-Status {
    Write-Host "[STATUS] Ontology Platform" -ForegroundColor Cyan
    Write-Host ""

    $bpid = Get-PortPID $BACKEND_PORT
    if ($bpid) {
        Write-Host "  Backend  (:$BACKEND_PORT): RUNNING (PID: $bpid)" -ForegroundColor Green
    } else {
        Write-Host "  Backend  (:$BACKEND_PORT): STOPPED" -ForegroundColor Red
    }

    $fpid = Get-PortPID $FRONTEND_PORT
    if ($fpid) {
        Write-Host "  Frontend (:$FRONTEND_PORT): RUNNING (PID: $fpid)" -ForegroundColor Green
    } else {
        Write-Host "  Frontend (:$FRONTEND_PORT): STOPPED" -ForegroundColor Red
    }
}

function Init-Database {
    Write-Host "[INIT] Database" -ForegroundColor Cyan
    Write-Host ""
    Push-Location "$ROOT\backend"
    Write-Host "  Running seed.py..."
    python seed.py
    Write-Host "  Running import_schema.py..."
    python import_schema.py
    Pop-Location
    Write-Host "  Done." -ForegroundColor Green
}

switch ($Command) {
    "start"   { Start-Services }
    "stop"    { Stop-Services }
    "restart" { Stop-Services; Start-Sleep -Seconds 2; Start-Services }
    "status"  { Show-Status }
    "init"    { Init-Database }
    default {
        Write-Host ""
        Write-Host "  Ontology Platform Control" -ForegroundColor Cyan
        Write-Host "  ========================"
        Write-Host ""
        Write-Host "  Usage: .\ctl.ps1 [command]"
        Write-Host ""
        Write-Host "  Commands:"
        Write-Host "    start    - Start backend + frontend"
        Write-Host "    stop     - Stop all services"
        Write-Host "    restart  - Stop then start"
        Write-Host "    status   - Show running status"
        Write-Host "    init     - Init database (seed + import)"
        Write-Host ""
    }
}
