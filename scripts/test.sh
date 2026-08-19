#!/usr/bin/env bash
set -euo pipefail
.venv-sldgraphx/bin/python -m pytest
.venv-sldgraphx/bin/python -m ruff check engine services sldforge scripts
(cd apps/web && npm run test && npm run build)
