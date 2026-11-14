"""Small, versioned catalog images served without a mobile release."""

import hashlib
from functools import lru_cache
from io import BytesIO

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

MAX_SOURCE_BYTES = 5 * 1024 * 1024
MAX_OUTPUT_BYTES = 512 * 1024
ICON_SIDE = 256
MOBILE_ICON_SIDE = 192
WIDE_ICON_SIZE = (192, 127)  # 62:41 title frame, rounded to whole source pixels.


def _encode_icon(image: Image.Image, side: int) -> bytes:
    resized = image.copy()
    resized.thumbnail((side, side), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(resized, ((side - resized.width) // 2, (side - resized.height) // 2))
    output = BytesIO()
    canvas.save(output, format="PNG", optimize=True)
    data = output.getvalue()
    if len(data) > MAX_OUTPUT_BYTES:
        raise ValidationError("El icono procesado supera 512 KB; usa una imagen más simple.")
    return data


def prepare_food_visual(upload) -> tuple[bytes, bytes, str]:
    if upload.size > MAX_SOURCE_BYTES:
        raise ValidationError("La imagen debe pesar como máximo 5 MB.")
    if upload.content_type != "image/png":
        raise ValidationError("Solo se aceptan imágenes PNG.")
    try:
        image = Image.open(upload)
        if image.format != "PNG" or image.width > 2048 or image.height > 2048:
            raise ValidationError("El PNG debe medir como máximo 2048 × 2048 px.")
        image.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError("El archivo no es un PNG válido.") from exc

    image = image.convert("RGBA")
    original_data = _encode_icon(image, ICON_SIDE)
    mobile_data = _encode_icon(image, MOBILE_ICON_SIDE)
    return original_data, mobile_data, hashlib.sha256(mobile_data).hexdigest()


@lru_cache(maxsize=256)
def render_wide_food_visual(square_mobile_data: bytes) -> bytes:
    """Derive a wide display variant; never replace the approved square asset."""
    image = Image.open(BytesIO(square_mobile_data)).convert("RGBA")
    alpha = image.getchannel("A")
    visible = alpha.point(lambda value: 255 if value >= 20 else 0).getbbox()
    if visible:
        image = image.crop(visible)
    image.thumbnail(WIDE_ICON_SIZE, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", WIDE_ICON_SIZE, (0, 0, 0, 0))
    canvas.alpha_composite(image, ((WIDE_ICON_SIZE[0] - image.width) // 2, (WIDE_ICON_SIZE[1] - image.height) // 2))
    output = BytesIO()
    canvas.save(output, format="PNG", optimize=True)
    return output.getvalue()
