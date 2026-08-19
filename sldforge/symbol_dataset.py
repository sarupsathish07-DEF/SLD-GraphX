"""Project-owned, style-varied synthetic symbol scenes and neutral detector annotations."""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from engine.sldgraph.symbols import SymbolClass

CLASS_ORDER = [
    SymbolClass.POWER_TRANSFORMER,
    SymbolClass.CIRCUIT_BREAKER,
    SymbolClass.DISCONNECTOR,
    SymbolClass.CURRENT_TRANSFORMER,
    SymbolClass.POTENTIAL_TRANSFORMER,
    SymbolClass.FEEDER_TERMINAL,
    SymbolClass.LOAD,
    SymbolClass.ENERGY_SOURCE,
    SymbolClass.BUS_COUPLER,
    SymbolClass.BUSBAR,
]
STYLE_FAMILIES = ("style_a", "style_b", "style_c", "style_d")


@dataclass(frozen=True)
class SymbolAnnotation:
    id: str
    class_name: str
    bbox: tuple[float, float, float, float]
    label: str
    style_family: str


def _font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _label(symbol_class: SymbolClass, index: int) -> str:
    prefixes = {
        SymbolClass.POWER_TRANSFORMER: "TR",
        SymbolClass.CIRCUIT_BREAKER: "CB",
        SymbolClass.DISCONNECTOR: "DS",
        SymbolClass.CURRENT_TRANSFORMER: "CT",
        SymbolClass.POTENTIAL_TRANSFORMER: "PT",
        SymbolClass.FEEDER_TERMINAL: "FDR",
        SymbolClass.LOAD: "LOAD",
        SymbolClass.ENERGY_SOURCE: "GRID",
        SymbolClass.BUS_COUPLER: "BC",
        SymbolClass.BUSBAR: "BUS",
    }
    return f"{prefixes[symbol_class]}-{index:02d}"


def _draw_symbol(
    draw: ImageDraw.ImageDraw,
    symbol_class: SymbolClass,
    box: tuple[int, int, int, int],
    style: str,
    line_width: int,
) -> None:
    x1, y1, x2, y2 = box
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    color = "#27312f"
    if symbol_class is SymbolClass.BUSBAR:
        draw.rectangle((x1, cy - max(3, line_width), x2, cy + max(3, line_width)), fill=color)
    elif symbol_class is SymbolClass.POWER_TRANSFORMER:
        radius = max(10, min(x2 - x1, y2 - y1) // 4)
        if style == "style_b":
            draw.arc((x1 + 8, y1 + 10, cx + 5, y2 - 10), 270, 90, fill=color, width=line_width)
            draw.arc((cx - 5, y1 + 10, x2 - 8, y2 - 10), 90, 270, fill=color, width=line_width)
        else:
            draw.ellipse(
                (cx - radius - 8, cy - radius, cx - 8, cy + radius), outline=color, width=line_width
            )
            draw.ellipse(
                (cx + 8, cy - radius, cx + radius + 8, cy + radius), outline=color, width=line_width
            )
    elif symbol_class is SymbolClass.CIRCUIT_BREAKER:
        if style == "style_c":
            draw.line((x1 + 8, cy, cx - 8, cy), fill=color, width=line_width)
            draw.line((cx + 8, cy, x2 - 8, cy), fill=color, width=line_width)
            draw.rectangle((cx - 8, cy - 8, cx + 8, cy + 8), outline=color, width=line_width)
        else:
            draw.rectangle(box, outline=color, width=line_width)
            draw.line((x1 + 10, y2 - 10, x2 - 10, y1 + 10), fill=color, width=line_width)
    elif symbol_class is SymbolClass.DISCONNECTOR:
        draw.line((x1 + 6, cy, cx - 5, cy), fill=color, width=line_width)
        draw.line(
            (cx - 5, cy, x2 - 8, y1 + 9 if style in {"style_a", "style_c"} else y2 - 9),
            fill=color,
            width=line_width,
        )
        draw.ellipse((x1 + 2, cy - 3, x1 + 8, cy + 3), fill=color)
        draw.ellipse((x2 - 8, cy - 3, x2 - 2, cy + 3), fill=color)
    elif symbol_class in {SymbolClass.CURRENT_TRANSFORMER, SymbolClass.POTENTIAL_TRANSFORMER}:
        radius = max(12, min(x2 - x1, y2 - y1) // 3)
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius), outline=color, width=line_width
        )
        if symbol_class is SymbolClass.CURRENT_TRANSFORMER:
            draw.line((cx - radius - 10, cy, cx + radius + 10, cy), fill=color, width=line_width)
        else:
            draw.line((cx, cy - radius - 10, cx, cy + radius + 10), fill=color, width=line_width)
    elif symbol_class is SymbolClass.FEEDER_TERMINAL:
        if style == "style_d":
            draw.polygon([(cx, y1 + 4), (x2 - 5, cy), (cx, y2 - 4), (x1 + 5, cy)], outline=color)
        else:
            draw.line((cx, y1 + 5, cx, y2 - 12), fill=color, width=line_width)
            draw.polygon([(x1 + 8, y2 - 14), (x2 - 8, y2 - 14), (cx, y2 - 3)], fill=color)
    elif symbol_class is SymbolClass.LOAD:
        if style == "style_b":
            draw.arc((x1 + 8, y1 + 6, x2 - 8, y2 + 10), 180, 360, fill=color, width=line_width)
            draw.line((cx, y1 + 4, cx, cy), fill=color, width=line_width)
        else:
            draw.polygon([(cx, y1 + 5), (x2 - 6, y2 - 6), (x1 + 6, y2 - 6)], outline=color)
    elif symbol_class is SymbolClass.ENERGY_SOURCE:
        draw.ellipse((x1 + 6, y1 + 6, x2 - 6, y2 - 6), outline="#285d87", width=line_width)
        if style in {"style_c", "style_d"}:
            draw.line((cx, y1 + 11, cx, y2 - 11), fill="#285d87", width=line_width)
        else:
            draw.line((x1 + 11, cy, x2 - 11, cy), fill="#285d87", width=line_width)
    elif symbol_class is SymbolClass.BUS_COUPLER:
        draw.rectangle(box, outline=color, width=line_width)
        draw.line((x1 + 8, y1 + 8, x2 - 8, y2 - 8), fill=color, width=line_width)
        draw.line((x1 + 8, y2 - 8, x2 - 8, y1 + 8), fill=color, width=max(1, line_width - 1))


def render_symbol_scene(
    seed: int,
    style_family: str,
    target: Path | None = None,
    width: int = 1200,
    height: int = 820,
) -> tuple[Image.Image, list[SymbolAnnotation]]:
    """Render one neutral synthetic sheet with all P0 symbols and canonical annotation boxes."""
    if style_family not in STYLE_FAMILIES:
        raise ValueError(f"Unknown style family: {style_family}")
    rng = random.Random(seed)
    image = Image.new("RGB", (width, height), rng.choice(["#f8f7f2", "#fbfbf8", "#f2f4f1"]))
    draw = ImageDraw.Draw(image)
    draw.rectangle((18, 18, width - 18, height - 18), outline="#c8c9c2", width=2)
    draw.text((44, 42), "SLDFORGE / SYMBOL INTELLIGENCE", fill="#26302d", font=_font(20))
    annotations: list[SymbolAnnotation] = []
    columns, rows = 5, 2
    cell_w, cell_h = (width - 110) // columns, (height - 170) // rows
    for index, symbol_class in enumerate(CLASS_ORDER):
        column, row = index % columns, index // columns
        cell_x, cell_y = 58 + column * cell_w, 120 + row * cell_h
        scale = rng.uniform(0.72, 0.92)
        box_w = int(cell_w * scale * (0.82 if symbol_class is SymbolClass.BUSBAR else 0.42))
        box_h = int(cell_h * scale * (0.18 if symbol_class is SymbolClass.BUSBAR else 0.36))
        x1 = cell_x + (cell_w - box_w) // 2 + rng.randint(-10, 10)
        y1 = cell_y + (cell_h - box_h) // 2 - 18 + rng.randint(-8, 8)
        x2, y2 = x1 + box_w, y1 + box_h
        line_width = rng.choice([2, 3, 4])
        _draw_symbol(draw, symbol_class, (x1, y1, x2, y2), style_family, line_width)
        label = _label(symbol_class, index + 1)
        draw.text(
            (x1, min(height - 34, y2 + 20)),
            label,
            fill="#4b504b",
            font=_font(rng.choice([14, 15, 16])),
        )
        annotations.append(
            SymbolAnnotation(
                id=f"{style_family}-{seed}-{index:02}",
                class_name=symbol_class.value,
                bbox=(x1 / width, y1 / height, x2 / width, y2 / height),
                label=label,
                style_family=style_family,
            )
        )
    draw.text(
        (width - 300, height - 48),
        "Project-owned synthetic symbols",
        fill="#6b7069",
        font=_font(13),
    )
    if target:
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, "PNG", optimize=True)
    return image, annotations


def annotation_payload(
    image_name: str, width: int, height: int, annotations: list[SymbolAnnotation]
) -> dict:
    return {
        "image": image_name,
        "width": width,
        "height": height,
        "objects": [asdict(item) for item in annotations],
    }


def write_annotation(
    target: Path, image_name: str, image: Image.Image, annotations: list[SymbolAnnotation]
) -> None:
    target.write_text(
        json.dumps(
            annotation_payload(image_name, image.width, image.height, annotations), indent=2
        ),
        encoding="utf-8",
    )
