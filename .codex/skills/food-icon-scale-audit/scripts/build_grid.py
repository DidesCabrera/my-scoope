#!/usr/bin/env python3
"""Render the published food-image scale audit without mutating the catalog."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import subprocess
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont


PATH_PATTERN = re.compile(r"/api/v1/foods/visual-assets/[0-9a-f-]{36}/([0-9a-f]{64})\.png")
CELL_W = 106
CELL_H = 124
HEADER_H = 90
GAP = 18
BG = (12, 12, 13, 255)
CELL_BG = (29, 29, 31, 255)
TEXT = (245, 245, 246, 255)
MUTED = (166, 166, 170, 255)
FONT_CANDIDATES = (
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
)


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def get_bytes(url: str) -> bytes:
    return subprocess.run(
        ["curl", "-fsSL", "--max-time", "25", url],
        check=True,
        capture_output=True,
    ).stdout


def sort_key(name: str) -> str:
    normalized = unicodedata.normalize("NFD", name)
    return "".join(char for char in normalized if not unicodedata.combining(char)).casefold()


def label_lines(draw: ImageDraw.ImageDraw, name: str, label_font: ImageFont.ImageFont) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in name.split():
        candidate = f"{line} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=label_font)[2] <= CELL_W - 10:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    if not lines:
        return [""]
    if len(lines) > 2:
        lines = [lines[0], " ".join(lines[1:])]
    if draw.textbbox((0, 0), lines[-1], font=label_font)[2] > CELL_W - 10:
        tail = lines[-1]
        while tail and draw.textbbox((0, 0), tail + "…", font=label_font)[2] > CELL_W - 10:
            tail = tail[:-1]
        lines[-1] = tail.rstrip() + "…"
    return lines


def fitted_icon(source: Image.Image, frame: tuple[int, int], trim: bool) -> Image.Image:
    if trim:
        alpha = source.getchannel("A")
        bounds = alpha.point(lambda value: 255 if value >= 20 else 0).getbbox()
        if bounds:
            source = source.crop(bounds)
    scale = min(frame[0] / source.width, frame[1] / source.height)
    size = max(1, round(source.width * scale)), max(1, round(source.height * scale))
    return source.resize(size, Image.Resampling.LANCZOS)


def render_grid(
    items: list[tuple[str, Image.Image]],
    columns: int,
    frame: tuple[int, int],
    trim: bool,
    title: str,
    detail: str,
    output: Path,
) -> None:
    rows = math.ceil(len(items) / columns)
    canvas = Image.new("RGBA", (GAP * 2 + columns * CELL_W, HEADER_H + rows * CELL_H + GAP), BG)
    draw = ImageDraw.Draw(canvas)
    title_font, meta_font, label_font = font(24), font(14), font(11)
    draw.text((GAP, 17), title, font=title_font, fill=TEXT)
    draw.text((GAP, 52), f"{len(items)} imágenes · {columns} por fila · {detail}", font=meta_font, fill=MUTED)
    for index, (name, source) in enumerate(items):
        row, col = divmod(index, columns)
        x, y = GAP + col * CELL_W, HEADER_H + row * CELL_H
        draw.rounded_rectangle((x + 2, y + 2, x + CELL_W - 4, y + CELL_H - 4), radius=12, fill=CELL_BG)
        icon = fitted_icon(source, frame, trim)
        center_x = x + CELL_W // 2
        canvas.alpha_composite(icon, (center_x - icon.width // 2, y + 10 + (54 - icon.height) // 2))
        for line_index, line in enumerate(label_lines(draw, name, label_font)):
            text_width = draw.textbbox((0, 0), line, font=label_font)[2]
            draw.text((center_x - text_width // 2, y + 74 + line_index * 14), line, font=label_font, fill=TEXT)
    canvas.convert("RGB").save(output, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://my-scoope.onrender.com")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--columns", type=int, default=15)
    parser.add_argument("--square-size", type=int, default=41)
    parser.add_argument("--wide-width", type=int, default=62)
    parser.add_argument("--wide-height", type=int, default=41)
    args = parser.parse_args()
    if args.columns < 1 or min(args.square_size, args.wide_width, args.wide_height) < 1:
        parser.error("columns and frame dimensions must be positive")
    if args.square_size > 54 or args.wide_height > 54 or args.wide_width > CELL_W - 12:
        parser.error("frame dimensions exceed the audit cell; enlarge the cell before using these sizes")
    base = args.base_url.rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path:
        parser.error("base-url must be an HTTPS origin without a path")
    manifest_url = f"{base}/api/v1/foods/visual-assets/manifest"
    manifest = json.loads(get_bytes(manifest_url))
    images, food_ids = manifest["images"], manifest["food_ids"]
    if not images:
        raise RuntimeError("Manifest contains no published named images")
    if len(images) != len(food_ids):
        raise RuntimeError(f"Named images ({len(images)}) differ from food IDs ({len(food_ids)}); resolve identity mapping before claiming full coverage")

    def load_item(item: tuple[str, str]) -> tuple[str, Image.Image]:
        name, path = item
        match = PATH_PATTERN.fullmatch(path)
        if not match:
            raise RuntimeError(f"Unexpected image path for {name}: {path}")
        data = get_bytes(base + path)
        if hashlib.sha256(data).hexdigest() != match.group(1):
            raise RuntimeError(f"Image digest mismatch: {name}")
        image = Image.open(io.BytesIO(data)).convert("RGBA")
        if image.size != (192, 192):
            raise RuntimeError(f"Unexpected image size for {name}: {image.size}")
        return name, image

    with ThreadPoolExecutor(max_workers=8) as pool:
        items = list(pool.map(load_item, images.items()))
    items.sort(key=lambda item: sort_key(item[0]))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    render_grid(items, args.columns, (args.square_size, args.square_size), False,
                f"Vista actual · {args.square_size} × {args.square_size} px",
                "PNG publicado completo", args.output_dir / "food-icons-current-grid.png")
    render_grid(items, args.columns, (args.wide_width, args.wide_height), True,
                f"Vista rectangular · {args.wide_width} × {args.wide_height} px",
                "margen transparente recortado · simulación",
                args.output_dir / "food-icons-rectangular-preview.png")
    record = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manifest_url": manifest_url,
        "published_named_images": len(items),
        "food_ids": len(food_ids),
        "columns": args.columns,
        "current_frame_px": [args.square_size, args.square_size],
        "proposed_frame_px": [args.wide_width, args.wide_height],
        "images": [{"name": name, "path": images[name]} for name, _ in items],
    }
    (args.output_dir / "food-icons-audit.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(items)} published images; wrote two {args.columns}-column grids to {args.output_dir}")


if __name__ == "__main__":
    main()
