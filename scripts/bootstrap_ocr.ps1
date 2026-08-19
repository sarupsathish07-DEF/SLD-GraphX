$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$ocrPython = Join-Path $projectRoot ".venv-sldgraphx-ocr-clean\Scripts\python.exe"
if (-not (Test-Path $ocrPython)) { py -3.10 -m venv (Join-Path $projectRoot ".venv-sldgraphx-ocr-clean") }
& $ocrPython -m pip install --upgrade pip
& $ocrPython -m pip install "paddlepaddle==2.6.2" "paddleocr==2.7.3" "numpy==1.26.4" "protobuf==3.20.2" "opencv-python==4.6.0.66" "opencv-contrib-python==4.6.0.66"
& $ocrPython -c "import paddle, paddleocr; print('Paddle', paddle.__version__, 'PaddleOCR', paddleocr.__version__)"
& $ocrPython (Join-Path $PSScriptRoot "prepare_ocr_models.py")
& (Join-Path $projectRoot ".venv-sldgraphx\Scripts\python.exe") (Join-Path $PSScriptRoot "ocr_smoke.py")
