# 安全重启 backend 服务
# 用法:
#   .\scripts\restart.ps1              # 默认端口 8000，热重载启动
#   .\scripts\restart.ps1 -StopOnly      # 仅停止，不启动
#   .\scripts\restart.ps1 -RebuildVenv   # 重建虚拟环境后启动
#   .\scripts\restart.ps1 -NoReload      # 禁用热重载

param(
    [int]$Port = 8000,
    [switch]$StopOnly,
    [switch]$RebuildVenv,
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"
$BackendDir = Split-Path $PSScriptRoot -Parent
$VenvDir = Join-Path $BackendDir ".venv"

function Write-Step([string]$Message) {
    Write-Host "[restart] $Message"
}

function Get-BackendProcessIds {
    $pids = [System.Collections.Generic.HashSet[int]]::new()

    $portPids = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { $_.OwningProcess } |
        Where-Object { $_ -gt 0 }

    foreach ($procId in $portPids) {
        [void]$pids.Add($procId)
    }

    $backendMarker = $BackendDir.ToLower()
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -in @("python.exe", "uvicorn.exe") -and
            $_.CommandLine -and
            $_.CommandLine.ToLower().Contains($backendMarker)
        } |
        ForEach-Object { [void]$pids.Add($_.ProcessId) }

    return @($pids)
}

function Stop-BackendProcesses {
    $pids = Get-BackendProcessIds
    if ($pids.Count -eq 0) {
        Write-Step "No backend process found on port $Port"
        return
    }

    Write-Step "Stopping processes: $($pids -join ', ')"
    $prevErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    foreach ($procId in $pids) {
        & taskkill /F /T /PID $procId 2>&1 | Out-Null
    }
    $ErrorActionPreference = $prevErrorAction

    $maxWaitSeconds = 15
    for ($i = 1; $i -le $maxWaitSeconds; $i++) {
        $remaining = Get-BackendProcessIds
        if ($remaining.Count -eq 0) {
            Write-Step "Processes stopped, port $Port is free"
            return
        }
        Start-Sleep -Seconds 1
    }

    throw "Failed to free port $Port within ${maxWaitSeconds}s. Remaining PIDs: $($remaining -join ', ')"
}

Push-Location $BackendDir
try {
    Write-Step "Working directory: $BackendDir"
    Stop-BackendProcesses

    if ($StopOnly) {
        Write-Step "Stop-only mode completed"
        exit 0
    }

    if ($RebuildVenv) {
        Write-Step "Rebuilding virtual environment..."
        if (Test-Path $VenvDir) {
            Remove-Item -Recurse -Force $VenvDir
        }
        & uv sync
        if ($LASTEXITCODE -ne 0) {
            throw "uv sync failed with exit code $LASTEXITCODE"
        }
        Write-Step "Virtual environment rebuilt"
    }

    Write-Step "Starting backend on port $Port..."

    if ($NoReload) {
        & uv run uvicorn main:app --host 0.0.0.0 --port $Port
    } else {
        & uv run main.py
    }
} finally {
    Pop-Location
}