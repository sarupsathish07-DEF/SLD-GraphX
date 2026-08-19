"""Generate reproducible, ignored SLDForge topology-v1 raster evidence and hidden graph truth."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sldforge.topology_dataset import generate_topology_corpus


def main() -> None:
    result = generate_topology_corpus(
        Path("data/synthetic/topology-v1/images"),
        Path("data/benchmark/topology-v1/manifest.json"),
    )
    print(json.dumps({"drawings": len(result["entries"]), "test": sum(item["split"] == "test" for item in result["entries"]), "style_holdout": sum(item["split"] == "style_holdout" for item in result["entries"])}, indent=2))


if __name__ == "__main__":
    main()
