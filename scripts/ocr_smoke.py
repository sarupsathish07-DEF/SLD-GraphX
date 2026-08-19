"""Create a known label image and invoke the isolated local OCR worker."""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.api.app.services.ocr_worker import recognize

image_path = Path("var/cache/ocr-smoke-labels.png")
image_path.parent.mkdir(parents=True, exist_ok=True)
image = Image.new("RGB", (1000, 440), "white")
draw = ImageDraw.Draw(image)
font = ImageFont.truetype("arial.ttf", 48)
for index, text in enumerate(["FDR-11KV-03", "CB-07", "TR-01", "11 kV", "630 A", "25 MVA"]):
    draw.text((60, 35 + index * 65), text, font=font, fill="black")
image.save(image_path)
response = recognize(image_path, 1, timeout_seconds=180)
print(json.dumps(response.model_dump(mode="json"), indent=2))
