$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
$api = Start-Process -FilePath "$projectRoot\.venv-sldgraphx\Scripts\python.exe" -ArgumentList "-m uvicorn services.api.app.main:app --host 127.0.0.1 --port 8000" -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
$web = Start-Process -FilePath "npm.cmd" -ArgumentList "run dev -- --host 127.0.0.1" -WorkingDirectory "$projectRoot\apps\web" -WindowStyle Hidden -PassThru
Write-Host "API: http://127.0.0.1:8000/api/health (PID $($api.Id))"
Write-Host "Web: http://127.0.0.1:5173 (PID $($web.Id))"
Write-Host "Stop with: Stop-Process -Id $($api.Id),$($web.Id)"
