"""Small local vector copies of the entity icons used by social share cards."""

from PIL import ImageDraw


def draw_share_entity_icon(draw: ImageDraw.ImageDraw, entity: str, box: tuple[int, int, int, int]) -> None:
    """Draw a white 24px-style entity glyph without a UI icon dependency."""
    left, top, right, bottom = box
    width = right - left
    scale = width / 24

    def point(x: float, y: float) -> tuple[float, float]:
        return left + x * scale, top + y * scale

    stroke = max(2, round(2.2 * scale))
    white = "#FFFFFF"

    if entity == "food":
        draw.polygon([point(7, 9), point(15, 7), point(17, 10), point(10, 19), point(5, 20)], outline=white, width=stroke)
        draw.line([point(8, 14), point(11, 17)], fill=white, width=stroke)
        draw.line([point(15, 8), point(18, 4), point(19, 8)], fill=white, width=stroke)
        draw.line([point(16, 8), point(22, 7), point(19, 11)], fill=white, width=stroke)
    elif entity == "meal":
        draw.line([point(6, 3), point(6, 21)], fill=white, width=stroke)
        draw.line([point(3, 3), point(3, 9), point(9, 9), point(9, 3)], fill=white, width=stroke)
        draw.line([point(16, 21), point(16, 9)], fill=white, width=stroke)
        draw.arc((point(13, 3), point(21, 13)), 90, 270, fill=white, width=stroke)
    elif entity == "daily_plan":
        draw.rounded_rectangle((point(5, 4), point(19, 22)), radius=2 * scale, outline=white, width=stroke)
        draw.rounded_rectangle((point(9, 2), point(15, 6)), radius=1 * scale, outline=white, width=stroke)
        for y in (11, 16):
            draw.ellipse((point(8, y), point(9, y + 1)), fill=white)
            draw.line([point(12, y + 0.5), point(16, y + 0.5)], fill=white, width=stroke)
    else:
        draw.rounded_rectangle((point(3, 4), point(21, 21)), radius=2 * scale, outline=white, width=stroke)
        draw.line([point(3, 9), point(21, 9)], fill=white, width=stroke)
        draw.line([point(8, 2), point(8, 6)], fill=white, width=stroke)
        draw.line([point(16, 2), point(16, 6)], fill=white, width=stroke)
        draw.line([point(8, 14), point(16, 14)], fill=white, width=stroke)
        draw.line([point(7, 18), point(13, 18)], fill=white, width=stroke)
