$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
if (-not (Test-Path .venv-sldgraphx)) {
  & "C:\Users\SARUP\AppData\Local\Programs\Python\Python310\python.exe" -m venv .venv-sldgraphx
}
& .\.venv-sldgraphx\Scripts\python.exe -m pip install -r requirements-dev.txt
Push-Location apps\web
npm install
Pop-Location
Write-Host "Bootstrap complete. Run .\scripts\dev.ps1"
