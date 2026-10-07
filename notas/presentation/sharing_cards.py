"""Deterministic branded PNG cards rendered exclusively from share snapshots."""

from __future__ import annotations

import hashlib
import io
import json
import unicodedata
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

from notas.presentation.share_card_icons import draw_share_entity_icon

CARD_SIZE = (1200, 630)
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/SFNS.ttf",
    "C:/Windows/Fonts/arial.ttf",
)
FONT_BOLD_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
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
def _font(size: int, *, bold: bool = False):
    font_path = _font_path()
    if font_path:
        font = ImageFont.truetype(font_path, size=size)
        if bold:
            try:
                font.set_variation_by_name("Bold")
            except (AttributeError, OSError):
                bold_path = next((candidate for candidate in FONT_BOLD_CANDIDATES if Path(candidate).is_file()), None)
                if bold_path:
                    font = ImageFont.truetype(bold_path, size=size)
        return font
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


def _program_daily_calories(snapshot: Mapping) -> list[float]:
    points: list[tuple[int, int, float]] = []
    days = snapshot.get("days") if isinstance(snapshot, Mapping) else None
    for day in days if isinstance(days, list) else []:
        if not isinstance(day, Mapping):
            continue
        week = int(_number(day.get("week_number")))
        plan = day.get("plan")
        nutrition = plan.get("nutrition") if isinstance(plan, Mapping) else None
        calories = _number(nutrition.get("calories")) if isinstance(nutrition, Mapping) else 0
        day_number = int(_number(day.get("day_number")))
        if week > 0 and day_number > 0 and calories > 0:
            points.append((week, day_number, calories))
    points.sort(key=lambda point: (point[0], point[1]))
    return [calories for _, _, calories in points[:14]]


def render_share_card_png(snapshot: Mapping) -> bytes:
    """Render a fixed-size social card without model, request or source-object access."""
    subject = snapshot.get("subject") if isinstance(snapshot, Mapping) else None
    nutrition = snapshot.get("nutrition") if isinstance(snapshot, Mapping) else None
    summary = snapshot.get("summary") if isinstance(snapshot, Mapping) else None
    subject = subject if isinstance(subject, Mapping) else {}
    nutrition = nutrition if isinstance(nutrition, Mapping) else {}
    summary = summary if isinstance(summary, Mapping) else {}

    title = _display_text(_text(subject.get("title"), fallback="Contenido compartido"))
    subject_type = _text(subject.get("type"), fallback="daily_plan")
    type_label = {
        "daily_plan": "PLAN DIARIO",
        "food": "ALIMENTO",
        "meal": "COMIDA",
        "program": "PROGRAMA",
    }.get(subject_type, "COMPARTIDO")
    calories = _number(nutrition.get("calories"))
    meal_count = int(_number(summary.get("meal_count")))
    food_count = int(_number(summary.get("food_count")))

    entity_colors = {
        "daily_plan": "#7C4DDB",
        "food": "#FF8800",
        "meal": "#CF34B0",
        "program": "#1B6491",
    }
    entity_color = entity_colors.get(subject_type, "#515151")

    # The social image is the card itself. Avoid nesting an inset card inside the
    # share canvas so previews can use every available pixel.
    image = Image.new("RGB", CARD_SIZE, "#121212")
    draw = ImageDraw.Draw(image)
    # A flush, full-width accent is platform-safe: hosts that round or crop the
    # social preview apply their own curve without exposing a second inner arc.
    draw.rectangle((0, 0, CARD_SIZE[0], 2), fill=entity_color)

    # Title section: semantic entity identity, title and structural summary.
    draw.rounded_rectangle((52, 38, 106, 92), radius=13, fill=entity_color)
    draw_share_entity_icon(draw, subject_type, (59, 45, 99, 85))
    draw.text((130, 47), type_label, font=_font(31, bold=True), fill="#B5B5B5")
    title_font = _font(60, bold=True)
    title_lines = _fit_lines(draw, title, title_font, max_width=1096, max_lines=2)
    for index, line in enumerate(title_lines):
        draw.text((52, 102 + index * 68), line, font=title_font, fill="#F5F5F5")

    title_bottom = 102 + len(title_lines) * 68
    if subject_type == "food":
        structural = (("100 g", "#241E10", "#FF8800"),)
    elif subject_type == "meal":
        structural = ((f"{food_count} alimentos", "#FF8800", None),)
    elif subject_type == "program":
        structural = (
            (f"{int(_number(summary.get('duration_weeks')))} semanas", "#1B6491", None),
            (f"{int(_number(summary.get('filled_days')))} días planificados", "#7C4DDB", None),
        )
    else:
        structural = (
            (f"{meal_count} comidas", "#CF34B0", None),
            (f"{food_count} alimentos", "#FF8800", None),
        )
    chip_font = _font(34, bold=True)
    chip_left = 52
    chip_top = title_bottom + 22
    for value, background, border in structural:
        chip_width = draw.textlength(value, font=chip_font) + 40
        draw.rounded_rectangle(
            (chip_left, chip_top, chip_left + chip_width, chip_top + 56),
            radius=28 if subject_type == "food" else 13,
            fill=background,
            outline=border,
            width=2 if border else 1,
        )
        draw.text((chip_left + 20, chip_top + 8), value, font=chip_font, fill="#FFFFFF")
        chip_left += chip_width + 14
    content_bottom = chip_top + 56

    if subject_type != "program":
        # Dash KPI: the same card recipe used by entity details.
        kpi_top = max(270, chip_top + 80)
        # Calories and macros form one horizontally centered unit. The calories
        # panel intentionally stays square to mirror Tot calories in the app.
        total_box = (52, kpi_top, 288, kpi_top + 236)
        total_center_x = (total_box[0] + total_box[2]) / 2
        draw.rounded_rectangle(total_box, radius=42, fill="#26211D", outline="#8D6951", width=6)
        draw.text((total_center_x, kpi_top + 34), "Calorías", anchor="ma", font=_font(28, bold=True), fill="#B5B5B5")
        calorie_text = f"{calories:.0f}"
        draw.text((total_center_x, kpi_top + 118), calorie_text, anchor="mm", font=_font(76, bold=True), fill="#F5F5F5")
        draw.text((total_center_x, kpi_top + 180), "kcal", anchor="ma", font=_font(30, bold=True), fill="#8F8F8F")

        protein = _number(nutrition.get("protein_grams"))
        carbs = _number(nutrition.get("carbs_grams"))
        fat = _number(nutrition.get("fat_grams"))
        macro_calories = protein * 4 + carbs * 4 + fat * 9
        macros = (
            ("Proteína", protein, 4, "#00D0F5"),
            ("Carbos", carbs, 4, "#01E888"),
            ("Grasas", fat, 9, "#BBFF00"),
        )
        row_left = 336
        for index, (label, grams, factor, color) in enumerate(macros):
            row_top = kpi_top + 14 + index * 76
            allocation = round(grams * factor * 100 / macro_calories) if macro_calories else 0
            draw.text((row_left, row_top + 14), label, font=_font(30, bold=True), fill="#F5F5F5")
            grams_text = f"{grams:.0f} g"
            draw.text((526, row_top + 14), grams_text, font=_font(30, bold=True), fill="#F5F5F5")
            draw.rounded_rectangle((640, row_top + 7, 1148, row_top + 61), radius=12, fill="#313131")
            fill_width = max(0, min(508, 508 * allocation / 100))
            if fill_width:
                draw.rounded_rectangle((640, row_top + 7, 640 + fill_width, row_top + 61), radius=12, fill=color)
            draw.text((1128, row_top + 34), f"{allocation}%", anchor="rm", font=_font(28, bold=True), fill="#F5F5F5")
        content_bottom = total_box[3]
    else:
        daily_calories = _program_daily_calories(snapshot)
        if daily_calories:
            duration_weeks = max(1, int(_number(summary.get("duration_weeks"))))
            header_top = chip_top + 82
            header_bottom = header_top + 48
            chart_top = header_bottom + 8
            chart_bottom = chart_top + 188
            chart_left = 52
            chart_right = 1148
            identity_right = 424
            radius = 28
            draw.rounded_rectangle((chart_left, header_top, identity_right - 8, header_bottom), radius=24, fill="#121212", outline="#343434", width=3)
            draw.text((74, header_top + 9), f"Semanas 1-{duration_weeks}", font=_font(27, bold=True), fill="#B5B5B5")
            week_count = min(duration_weeks, 8)
            chip_gap = 7
            chip_area_left = identity_right
            chip_width = (chart_right - chip_area_left - chip_gap * (week_count - 1)) / week_count
            for index in range(week_count):
                week_left = chip_area_left + index * (chip_width + chip_gap)
                draw.rounded_rectangle((week_left, header_top, week_left + chip_width, header_bottom), radius=24, fill="#121212", outline="#343434", width=3)
                draw.text((week_left + chip_width / 2, header_top + 24), f"S{index + 1}", anchor="mm", font=_font(25, bold=True), fill="#B5B5B5")

            draw.rounded_rectangle((chart_left, chart_top, chart_right, chart_bottom), radius=radius, fill="#000000", outline="#343434", width=3)
            draw.rounded_rectangle((chart_left, chart_top, identity_right, chart_bottom), radius=radius, fill="#262626")
            draw.rectangle((identity_right - radius, chart_top, identity_right, chart_bottom), fill="#262626")
            draw.text((78, chart_top + 24), "Calorías", font=_font(40, bold=True), fill="#F5F5F5")
            minimum = min(daily_calories)
            maximum = max(daily_calories)
            min_label = f"{minimum:.0f}" if minimum < 1000 else f"{minimum:,.0f}".replace(",", ".")
            max_label = f"{maximum:.0f}" if maximum < 1000 else f"{maximum:,.0f}".replace(",", ".")
            range_text = f"{min_label} - {max_label} kcal"
            range_width = draw.textlength(range_text, font=_font(32, bold=True)) + 38
            draw.rounded_rectangle(
                (78, chart_top + 94, 78 + range_width, chart_top + 154),
                radius=18,
                fill="#26211D",
                outline="#8D6951",
                width=3,
            )
            draw.text((97, chart_top + 105), range_text, font=_font(32, bold=True), fill="#F5F5F5")

            plot_left = identity_right
            plot_right = chart_right
            plot_top = chart_top + 27
            plot_bottom = chart_bottom - 27
            slot_width = (plot_right - plot_left - 48) / max(len(daily_calories) - 1, 1)
            value_range = max(maximum - minimum, 1)
            points = []
            for index, value in enumerate(daily_calories):
                x = plot_left + 24 + index * slot_width
                normalized = (value - minimum) / value_range
                y = plot_bottom - normalized * (plot_bottom - plot_top)
                points.append((x, y))

            area_mask = Image.new("L", CARD_SIZE, 0)
            area_mask_draw = ImageDraw.Draw(area_mask)
            area_mask_draw.polygon(
                [*points, (points[-1][0], plot_bottom), (points[0][0], plot_bottom)],
                fill=255,
            )
            fade_mask = Image.new("L", CARD_SIZE, 0)
            fade_draw = ImageDraw.Draw(fade_mask)
            fade_height = max(plot_bottom - plot_top, 1)
            for y in range(int(plot_top), int(plot_bottom) + 1):
                opacity = round(112 * (plot_bottom - y) / fade_height)
                fade_draw.line((plot_left, y, plot_right, y), fill=opacity)
            area_alpha = ImageChops.multiply(area_mask, fade_mask)
            area_overlay = Image.new("RGBA", CARD_SIZE, (141, 105, 81, 0))
            area_overlay.putalpha(area_alpha)
            image.paste(area_overlay, (0, 0), area_overlay)
            draw = ImageDraw.Draw(image)

            for divider_index in range(7, len(points), 7):
                divider_x = (points[divider_index - 1][0] + points[divider_index][0]) / 2
                draw.line((divider_x, chart_top + 18, divider_x, chart_bottom - 18), fill="#343434", width=3)
            draw.line(points, fill="#8D6951", width=2, joint="curve")
            for x, y in points:
                draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill="#8D6951")
            draw.rounded_rectangle((chart_left, chart_top, chart_right, chart_bottom), radius=radius, outline="#343434", width=3)
            content_bottom = chart_bottom
    # Programs intentionally stop after the title section: there is no Dash KPI.

    # MyScoope logo footer.
    logo_y = content_bottom + (CARD_SIZE[1] - content_bottom) / 2 - 16
    logo_text = "MyScoope"
    logo_font = _font(31)
    logo_width = draw.textlength(logo_text, font=logo_font)
    logo_left = (CARD_SIZE[0] - logo_width - 28) / 2
    draw.text((logo_left, logo_y), logo_text, font=logo_font, fill="#F5F5F5")  # textMain
    bars_left = logo_left + logo_width + 10
    for index, color in enumerate(("#00D0F5", "#01E888", "#BBFF00")):
        draw.rounded_rectangle((bars_left, logo_y + 5 + index * 9, bars_left + 20, logo_y + 11 + index * 9), radius=2, fill=color)

    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
