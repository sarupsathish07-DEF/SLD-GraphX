from pathlib import Path

import pytest

from engine.sldgraph.ocr import UnavailableOcrAdapter


def test_unavailable_adapter_never_fabricates_ocr() -> None:
    with pytest.raises(RuntimeError, match="OCR has not run"):
        UnavailableOcrAdapter().recognize(Path("missing.png"))
