#!/usr/bin/env bash
set -euo pipefail
.venv-sldgraphx/bin/python -m uvicorn services.api.app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!
(cd apps/web && npm run dev -- --host 127.0.0.1) &
WEB_PID=$!
trap 'kill $API_PID $WEB_PID' EXIT
wait
