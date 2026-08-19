"""Create the separate topology-repair development and validation corpus."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sldforge.topology_dataset import generate_topology_repair_development_corpus


def main() -> None:
    result = generate_topology_repair_development_corpus(
        Path("data/synthetic/topology-repair-dev/images"),
        Path("data/benchmark/topology-repair-dev/manifest.json"),
    )
    print(json.dumps({"drawings": len(result["entries"]), "development": 6, "validation": 6}, indent=2))


if __name__ == "__main__":
    main()
