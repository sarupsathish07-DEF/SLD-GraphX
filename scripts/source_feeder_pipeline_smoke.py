"""Named M5 entrypoint for the real upload-to-source/feeder pipeline smoke."""

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("topology_pipeline_smoke.py")), run_name="__main__")
