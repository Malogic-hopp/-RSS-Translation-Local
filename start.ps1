$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $PSCommandPath
Set-Location $scriptDir

if (-not (Test-Path ".\main.py")) {
    throw "Cannot find main.py in $scriptDir"
}

$venvPython = Join-Path $scriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw @"
找不到项目虚拟环境 `.venv`。
请先在项目根目录创建并安装依赖：
  python -m venv .venv
  .\.venv\Scripts\pip install -r requirements.txt
"@
}

Write-Host "Starting RSS Translation..." -ForegroundColor Cyan
Write-Host "Working directory: $scriptDir" -ForegroundColor DarkGray
Write-Host "Python: $venvPython" -ForegroundColor DarkGray

& $venvPython main.py
