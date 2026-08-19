"""Generate a small ignored, reproducible SLDForge development corpus."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sldforge.generator import generate_development_corpus

for path in generate_development_corpus(Path("data/synthetic/dev")):
    print(path)
