$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$trainPython = Join-Path $projectRoot ".venv-sldgraphx-detector-train\Scripts\python.exe"
$detectorPython = Join-Path $projectRoot ".venv-sldgraphx-detector\Scripts\python.exe"
if (-not (Test-Path $trainPython)) { py -3.10 -m venv (Join-Path $projectRoot ".venv-sldgraphx-detector-train") }
if (-not (Test-Path $detectorPython)) { py -3.10 -m venv (Join-Path $projectRoot ".venv-sldgraphx-detector") }
foreach ($python in @($trainPython, $detectorPython)) {
  & $python -m pip install "numpy==1.26.4" "opencv-python-headless==4.10.0.84" "scikit-learn==1.5.2" "pydantic==2.13.4"
  & $python -m pip check
}
& (Join-Path $projectRoot ".venv-sldgraphx\Scripts\python.exe") (Join-Path $PSScriptRoot "create_symbol_dataset.py")
& $trainPython (Join-Path $PSScriptRoot "train_symbol_detector.py")
& (Join-Path $projectRoot ".venv-sldgraphx\Scripts\python.exe") (Join-Path $PSScriptRoot "symbol_detector_smoke.py")
