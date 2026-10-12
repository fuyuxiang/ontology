# Ontology Platform managed process control: start | stop | restart | status | init
param([string]$Command = "help")
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$ErrorActionPreference = "Stop"
# Read configuration before computing ports and the frontend proxy.
if (Test-Path "$ROOT\.env") {
    foreach ($line in Get-Content "$ROOT\.env") {
        if ($line -match '^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
            $key = $Matches[1]; $value = $Matches[2].Trim()
            if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) { $value = $value.Substring(1, $value.Length - 2) }
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}
$BACKEND_PORT = if ($env:BACKEND_PORT) { [int]$env:BACKEND_PORT } elseif ($env:PORT) { [int]$env:PORT } else { 8001 }
$FRONTEND_PORT = if ($env:FRONTEND_PORT) { [int]$env:FRONTEND_PORT } else { 5177 }
$CODE_SERVER_PORT = if ($env:CODE_SERVER_PORT) { [int]$env:CODE_SERVER_PORT } else { 8443 }
$CodeHost = if ($env:CODE_SERVER_BIND_HOST) { $env:CODE_SERVER_BIND_HOST } else { "127.0.0.1" }
$Workspace = if ($env:WORKSPACE_ROOT) { $env:WORKSPACE_ROOT } else { "$ROOT\workspace" }
$CodeData = if ($env:CODE_SERVER_USER_DATA_DIR) { $env:CODE_SERVER_USER_DATA_DIR } else { "$ROOT\.code-server-data" }
$CodeExtensions = if ($env:CODE_SERVER_EXTENSIONS_DIR) { $env:CODE_SERVER_EXTENSIONS_DIR } else { "$ROOT\.code-server-extensions" }
$BackendPython = @("$ROOT\backend\.venv\Scripts\python.exe", "$ROOT\backend\venv\Scripts\python.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (!$BackendPython) { $BackendPython = (Get-Command python -ErrorAction Stop).Source }
$env:PORT = "$BACKEND_PORT"; $env:WORKSPACE_ROOT = $Workspace; $env:CODE_SERVER_PORT = "$CODE_SERVER_PORT"
if (!$env:VITE_PROXY_TARGET) { $env:VITE_PROXY_TARGET = "http://127.0.0.1:$BACKEND_PORT" }

function Get-PortPID($port) {
    $connection = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($connection) { return $connection.OwningProcess }
    return $null
}
function Process-Identity($procId) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
    if (!$process) { return $null }
    return @{ Pid = [int]$process.ProcessId; Started = $process.CreationDate.ToUniversalTime().ToString("o"); Command = $process.CommandLine }
}
function Managed-Record($name) {
    $file = "$ROOT\.$name.pid"
    if (!(Test-Path $file)) { return $null }
    try {
        $record = Get-Content $file -Raw | ConvertFrom-Json
        $actual = Process-Identity $record.Pid
        if ($record.Root -ne $ROOT -or !$actual -or $actual.Started -ne $record.Started -or $actual.Command -ne $record.Command -or !$actual.Command.Contains($ROOT)) { return $null }
        return $record
    } catch { return $null }
}
function Record-Process($name, $process) {
    $identity = Process-Identity $process.Id
    if (!$identity) { throw "$name exited before its PID could be recorded." }
    $identity.Root = $ROOT; $identity.Service = $name
    $identity | ConvertTo-Json | Set-Content "$ROOT\.$name.pid" -Encoding UTF8
}
function Wait-Ready($name, $url, $health) {
    for ($attempt = 0; $attempt -lt 100; $attempt++) {
        if (!(Managed-Record $name)) { throw "$name process exited or changed identity. Check $name.log." }
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200 -and (!$health -or ($response.Content | ConvertFrom-Json).status -eq "ok")) { return }
        } catch { }
        Start-Sleep -Seconds 1
    }
    throw "Readiness timed out: $url"
}
function Stop-One($name) {
    $record = Managed-Record $name
    if (!$record) { Write-Host "  ${name}: no owned process; unrelated listeners preserved."; return }
    $all = Get-CimInstance Win32_Process
    $owned = @([int]$record.Pid)
    do {
        $more = @($all | Where-Object { $_.ParentProcessId -in $owned -and $_.ProcessId -notin $owned } | Select-Object -ExpandProperty ProcessId)
        $owned += $more
    } while ($more.Count -gt 0)
    $identities = @($owned | ForEach-Object { Process-Identity $_ })
    [array]::Reverse($identities)
    foreach ($identity in $identities) {
        if (!$identity) { continue }
        $current = Process-Identity $identity.Pid
        if ($current -and $current.Started -eq $identity.Started -and $current.Command -eq $identity.Command) { Stop-Process -Id $identity.Pid -Force -ErrorAction SilentlyContinue }
    }
    Remove-Item "$ROOT\.$name.pid" -ErrorAction SilentlyContinue
    Write-Host "  $name managed process tree stopped."
}
function Start-Services {
    $created = @()
    try {
        foreach ($port in @($BACKEND_PORT, $FRONTEND_PORT, $CODE_SERVER_PORT)) {
            if (Get-PortPID $port) { throw "Port $port is already occupied. Stop this checkout's managed services or choose another port." }
        }
        if (!(Test-Path "$ROOT\frontend\node_modules\vite\bin\vite.js")) { throw "Install frontend dependencies first." }
        $node = (Get-Command node -ErrorAction Stop).Source
        $code = (Get-Command code-server -ErrorAction Stop).Source
        if ($env:SKIP_DEPENDENCY_INSTALL -ne "1") {
            & $BackendPython -m pip install -r "$ROOT\backend\requirements.txt" --quiet
            if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
        }
        $env:PORT = "$BACKEND_PORT"
        $arguments = @('-m', 'uvicorn', 'app.main:app', '--app-dir', "`"$ROOT\backend`"", '--host', '127.0.0.1', '--port', "$BACKEND_PORT", '--log-level', 'info')
        if ($env:BACKEND_RELOAD -eq "1") { $arguments += '--reload' }
        $process = Start-Process -FilePath $BackendPython -ArgumentList $arguments -WorkingDirectory "$ROOT\backend" -RedirectStandardOutput "$ROOT\backend.log" -RedirectStandardError "$ROOT\backend-error.log" -PassThru
        Record-Process 'backend' $process; $created += 'backend'; Wait-Ready 'backend' "http://127.0.0.1:$BACKEND_PORT/api/health" $true
        $process = Start-Process -FilePath $node -ArgumentList @("`"$ROOT\frontend\node_modules\vite\bin\vite.js`"", '--host', '127.0.0.1', '--port', "$FRONTEND_PORT", '--strictPort') -WorkingDirectory "$ROOT\frontend" -RedirectStandardOutput "$ROOT\frontend.log" -RedirectStandardError "$ROOT\frontend-error.log" -PassThru
        Record-Process 'frontend' $process; $created += 'frontend'; Wait-Ready 'frontend' "http://127.0.0.1:$FRONTEND_PORT" $false
        New-Item -ItemType Directory -Force -Path $Workspace, $CodeData, $CodeExtensions | Out-Null
        if (!$env:CODE_SERVER_PASSWORD) {
            $passwordFile = "$ROOT\.code-server-password"
            if (!(Test-Path $passwordFile)) {
                $bytes = New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
                [Convert]::ToBase64String($bytes) | Set-Content $passwordFile -Encoding ASCII
            }
            & icacls $passwordFile /inheritance:r /grant:r "${env:USERNAME}:(F)" | Out-Null
            $env:CODE_SERVER_PASSWORD = (Get-Content $passwordFile -Raw).Trim()
        }
        $env:PASSWORD = $env:CODE_SERVER_PASSWORD
        # code-server reads PORT before its --bind-addr value.
        $env:PORT = "$CODE_SERVER_PORT"
        $arguments = @('--config', "`"$ROOT\code-server\config.yaml`"", '--bind-addr', "${CodeHost}:$CODE_SERVER_PORT", '--auth', 'password', '--user-data-dir', "`"$CodeData`"", '--extensions-dir', "`"$CodeExtensions`"", "`"$Workspace`"")
        if ($code.EndsWith('.cmd') -or $code.EndsWith('.bat')) {
            $process = Start-Process -FilePath $env:ComSpec -ArgumentList @('/d', '/s', '/c', "`"`"$code`" $($arguments -join ' ')`"") -WorkingDirectory $ROOT -RedirectStandardOutput "$ROOT\code-server.log" -RedirectStandardError "$ROOT\code-server-error.log" -PassThru
        } else {
            $process = Start-Process -FilePath $code -ArgumentList $arguments -WorkingDirectory $ROOT -RedirectStandardOutput "$ROOT\code-server.log" -RedirectStandardError "$ROOT\code-server-error.log" -PassThru
        }
        Record-Process 'code-server' $process; $created += 'code-server'; Wait-Ready 'code-server' "http://127.0.0.1:$CODE_SERVER_PORT/healthz" $false
        Write-Host "Ready: frontend :$FRONTEND_PORT / backend :$BACKEND_PORT / code-server :$CODE_SERVER_PORT. Editor password is in the local file or configured environment."
    } catch {
        foreach ($name in $created) { Stop-One $name }
        throw
    }
}
function Stop-Services { foreach ($name in @('code-server', 'frontend', 'backend')) { Stop-One $name } }
function Show-Status {
    foreach ($name in @('backend', 'frontend', 'code-server')) {
        $record = Managed-Record $name
        if ($record) { Write-Host "${name}: RUNNING managed PID $($record.Pid)" } else { Write-Host "${name}: STOPPED or foreign process" }
    }
}
function Init-Database {
    Push-Location "$ROOT\backend"
    try {
        & $BackendPython init_db.py
        if ($LASTEXITCODE -ne 0) { throw "Database initialization failed." }
    } finally { Pop-Location }
}
try {
    switch ($Command) {
        'start' { Start-Services }
        'stop' { Stop-Services }
        'restart' { Stop-Services; Start-Services }
        'status' { Show-Status }
        'init' { Init-Database }
        default { Write-Host '.\ctl.ps1 start | stop | restart | status | init' }
    }
} catch { Write-Error $_; exit 1 }
