# Starts the RubbleEcho simulation backend and the mission-control UI.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Create the backend virtual environment first. See README.md."
    exit 1
}

$backend = Start-Process -FilePath $python -ArgumentList "-m","uvicorn","main:app","--reload","--port","8080" -WorkingDirectory (Join-Path $root "backend") -PassThru
$frontend = Start-Process -FilePath "npm" -ArgumentList "run","dev" -WorkingDirectory (Join-Path $root "frontend") -PassThru

Write-Host "Backend PID $($backend.Id)  http://127.0.0.1:8080"
Write-Host "Frontend PID $($frontend.Id)  http://127.0.0.1:5173"
Write-Host "Stop those processes to shut the demo down."
