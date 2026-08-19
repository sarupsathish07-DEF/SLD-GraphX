#!/usr/bin/env bash
set -euo pipefail
python3.10 -m venv .venv-sldgraphx
.venv-sldgraphx/bin/python -m pip install -r requirements-dev.txt
(cd apps/web && npm install)
echo "Bootstrap complete. Run ./scripts/dev.sh"
