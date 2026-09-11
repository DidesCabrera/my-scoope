"""Deterministic branded PNG cards rendered exclusively from share snapshots."""

from __future__ import annotations

import hashlib
import io
import json
import unicodedata
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CARD_SIZE = (1200, 630)
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/SFNS.ttf",
    "C:/Windows/Fonts/arial.ttf",
)


def snapshot_card_etag(snapshot: Mapping) -> str:
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _text(value, *, fallback: str = "", limit: int = 120) -> str:
    clean = " ".join(str(value or fallback).split())
    return clean[:limit]


def _number(value) -> float:
    try:
        return max(0.0, float(value or 0))
    except (TypeError, ValueError):
        return 0.0


@lru_cache(maxsize=1)
def _font_path() -> str | None:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    return None


@lru_cache(maxsize=12)
def _font(size: int):
    font_path = _font_path()
    if font_path:
        return ImageFont.truetype(font_path, size=size)
    return ImageFont.load_default(size=size)


def _display_text(value: str) -> str:
    if _font_path():
        return value
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")


def _fit_lines(draw, text: str, font, *, max_width: int, max_lines: int = 2) -> list[str]:
    words = _display_text(text).split() or ["Plan compartido"]
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or draw.textlength(candidate, font=font) <= max_width:
            current = candidate
            continue
        lines.append(current)
        current = word
        if len(lines) == max_lines - 1:
            break
    if len(lines) < max_lines and current:
        lines.append(current)
    consumed = " ".join(lines)
    if len(consumed) < len(text) and lines:
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > max_width:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    return lines


def render_share_card_png(snapshot: Mapping) -> bytes:
    """Render a fixed-size social card without model, request or source-object access."""
    subject = snapshot.get("subject") if isinstance(snapshot, Mapping) else None
    nutrition = snapshot.get("nutrition") if isinstance(snapshot, Mapping) else None
    summary = snapshot.get("summary") if isinstance(snapshot, Mapping) else None
    subject = subject if isinstance(subject, Mapping) else {}
    nutrition = nutrition if isinstance(nutrition, Mapping) else {}
    summary = summary if isinstance(summary, Mapping) else {}

    title = _display_text(_text(subject.get("title"), fallback="Plan compartido"))
    calories = _number(nutrition.get("calories"))
    meal_count = int(_number(summary.get("meal_count")))
    food_count = int(_number(summary.get("food_count")))

    image = Image.new("RGB", CARD_SIZE, "#071720")
    draw = ImageDraw.Draw(image)
    for y in range(CARD_SIZE[1]):
        ratio = y / CARD_SIZE[1]
        draw.line((0, y, CARD_SIZE[0], y), fill=(7, int(23 + 13 * ratio), int(32 + 15 * ratio)))

    draw.ellipse((930, -220, 1370, 220), fill="#153a36")
    draw.ellipse((1030, 390, 1260, 620), fill="#13302f")
    draw.rounded_rectangle((70, 54, 1130, 576), radius=38, fill="#0d222c", outline="#29404a", width=2)
    draw.rounded_rectangle((92, 78, 262, 126), radius=24, fill="#c9f36a")
    draw.text((119, 88), "PLAN DIARIO", font=_font(22), fill="#10211c")
    draw.text((862, 85), "MY SCOOPE", font=_font(30), fill="#f3f7f5")

    title_font = _font(58)
    for index, line in enumerate(_fit_lines(draw, title, title_font, max_width=850)):
        draw.text((94, 165 + index * 68), line, font=title_font, fill="#ffffff")

    draw.text((94, 326), f"{calories:.0f}", font=_font(76), fill="#c9f36a")
    draw.text((270, 361), "kcal", font=_font(32), fill="#b5c2c7")

    macros = (
        ("PROTEÍNA", nutrition.get("protein_grams")),
        ("CARBOS", nutrition.get("carbs_grams")),
        ("GRASAS", nutrition.get("fat_grams")),
    )
    x = 492
    for label, value in macros:
        draw.rounded_rectangle((x, 335, x + 190, 435), radius=20, fill="#142f39")
        draw.text((x + 20, 352), _display_text(label), font=_font(18), fill="#91a4ab")
        draw.text((x + 20, 384), f"{_number(value):.1f} g", font=_font(29), fill="#ffffff")
        x += 210

    draw.line((94, 476, 1106, 476), fill="#29404a", width=2)
    draw.text(
        (94, 505),
        f"{meal_count} comidas  ·  {food_count} alimentos",
        font=_font(27),
        fill="#c8d3d6",
    )

    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
