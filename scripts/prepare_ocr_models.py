"""Download PaddleOCR models once and copy them into the project-local model store."""

from __future__ import annotations

import shutil
from pathlib import Path

from paddleocr import PaddleOCR

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path.home() / ".paddleocr" / "whl"
TARGET = ROOT / "models" / "ocr" / "paddle"
MODELS = {
    SOURCE / "det" / "en" / "en_PP-OCRv3_det_infer": TARGET / "det" / "en_PP-OCRv3_det_infer",
    SOURCE / "rec" / "en" / "en_PP-OCRv4_rec_infer": TARGET / "rec" / "en_PP-OCRv4_rec_infer",
    SOURCE / "cls" / "ch_ppocr_mobile_v2.0_cls_infer": TARGET
    / "cls"
    / "ch_ppocr_mobile_v2.0_cls_infer",
}


def main() -> None:
    # The only network-enabled preparation action. Runtime workers use explicit local paths.
    PaddleOCR(use_angle_cls=True, lang="en", use_gpu=False, show_log=False)
    for source, target in MODELS.items():
        if not source.is_dir():
            raise RuntimeError(f"PaddleOCR preparation did not produce {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target, dirs_exist_ok=True)
        print(target)


if __name__ == "__main__":
    main()
