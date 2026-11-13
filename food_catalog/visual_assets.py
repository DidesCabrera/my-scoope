"""Small, versioned catalog images served without a mobile release."""

import hashlib
from io import BytesIO

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

MAX_SOURCE_BYTES = 5 * 1024 * 1024
MAX_OUTPUT_BYTES = 512 * 1024
ICON_SIDE = 256
MOBILE_ICON_SIDE = 192


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
