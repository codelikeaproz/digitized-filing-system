$python = "C:\Users\ciscl\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$script = Join-Path $PSScriptRoot "scanner_bridge_stdlib.py"

Write-Host "Starting DFS Scanner Bridge..." -ForegroundColor Green
Write-Host "Do not close this window while scanning." -ForegroundColor Yellow
Write-Host ""

& $python $script
