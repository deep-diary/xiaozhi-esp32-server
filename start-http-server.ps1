# PowerShell Script: Start HTTP Server in Background

# Get the absolute path of the script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "Switching to directory: main/xiaozhi-server/test"
$TestDir = Join-Path $ScriptDir "main\xiaozhi-server\test"

if (-not (Test-Path $TestDir)) {
    Write-Host "Error: Directory does not exist: $TestDir" -ForegroundColor Red
    exit 1
}

Set-Location $TestDir

# Check if port 8006 is already in use
$PortInUse = Get-NetTCPConnection -LocalPort 8006 -ErrorAction SilentlyContinue
if ($PortInUse) {
    Write-Host "Warning: Port 8006 is already in use" -ForegroundColor Yellow
    Write-Host "Finding and terminating process using port 8006..."
    $Process = Get-NetTCPConnection -LocalPort 8006 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    if ($Process) {
        Stop-Process -Id $Process -Force -ErrorAction SilentlyContinue
        Write-Host "Terminated process $Process"
        Start-Sleep -Seconds 1
    }
}

# Start HTTP server in background
Write-Host "Starting HTTP server on port: 8006" -ForegroundColor Green
Write-Host "Access URL: http://localhost:8006" -ForegroundColor Green
Write-Host ""

# Start job in background
$Job = Start-Job -ScriptBlock {
    Set-Location $using:TestDir
    python -m http.server 8006
}

Write-Host "HTTP server started in background (Job ID: $($Job.Id))" -ForegroundColor Green
Write-Host "View logs: Receive-Job -Id $($Job.Id)" -ForegroundColor Cyan
Write-Host "Stop service: Stop-Job -Id $($Job.Id); Remove-Job -Id $($Job.Id)" -ForegroundColor Cyan
Write-Host ""

# 显示作业状态
Start-Sleep -Seconds 2
$Job | Format-Table Id, State, HasMoreData
