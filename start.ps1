$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $PSCommandPath
Set-Location $scriptDir

if (-not (Test-Path ".\main.py")) {
    throw "Cannot find main.py in $scriptDir"
}

function Get-PythonCommand {
    foreach ($name in @("python", "python3", "py")) {
        try {
            $cmd = Get-Command $name -ErrorAction Stop
            if ($cmd.CommandType -eq "Application" -or $cmd.CommandType -eq "ExternalScript") {
                return $cmd.Source
            }
            return $cmd.Name
        } catch {
        }
    }

    throw "Python is not available in PATH. Please install Python or add it to PATH."
}

$venvPython = Join-Path $scriptDir ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = Get-PythonCommand
}

Write-Host "Starting RSS Translation..." -ForegroundColor Cyan
Write-Host "Working directory: $scriptDir" -ForegroundColor DarkGray
Write-Host "Python: $python" -ForegroundColor DarkGray

& $python main.py
