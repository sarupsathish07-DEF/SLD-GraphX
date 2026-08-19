$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
& .\.venv-sldgraphx\Scripts\python.exe -m pytest
& .\.venv-sldgraphx\Scripts\python.exe -m ruff check engine services sldforge scripts
Push-Location apps\web
npm run test
npm run build
Pop-Location
