"""Generated PWA startup images for iOS/iPadOS.

The startup image URLs keep the exact device-specific dimensions expected by
Safari, but the PNG bytes are generated at request time instead of being stored
as large base64 strings in source control or ChatGPT exports.
"""

import struct
import zlib
from functools import lru_cache

PWA_STARTUP_IMAGE_SPECS = [
    {
        "key": 'iphone-se-1st-portrait',
        "width": 640,
        "height": 1136,
        "css_width": 320,
        "css_height": 568,
        "pixel_ratio": 2,
        "orientation": 'portrait',
        "label": 'iPhone SE 1ª gen / 5s - vertical',
    },
    {
        "key": 'iphone-se-1st-landscape',
        "width": 1136,
        "height": 640,
        "css_width": 320,
        "css_height": 568,
        "pixel_ratio": 2,
        "orientation": 'landscape',
        "label": 'iPhone SE 1ª gen / 5s - horizontal',
    },
    {
        "key": 'iphone-678-se-portrait',
        "width": 750,
        "height": 1334,
        "css_width": 375,
        "css_height": 667,
        "pixel_ratio": 2,
        "orientation": 'portrait',
        "label": 'iPhone 6/7/8/SE 2-3 - vertical',
    },
    {
        "key": 'iphone-678-se-landscape',
        "width": 1334,
        "height": 750,
        "css_width": 375,
        "css_height": 667,
        "pixel_ratio": 2,
        "orientation": 'landscape',
        "label": 'iPhone 6/7/8/SE 2-3 - horizontal',
    },
    {
        "key": 'iphone-678-plus-portrait',
        "width": 1242,
        "height": 2208,
        "css_width": 414,
        "css_height": 736,
        "pixel_ratio": 3,
        "orientation": 'portrait',
        "label": 'iPhone Plus 6/7/8 - vertical',
    },
    {
        "key": 'iphone-678-plus-landscape',
        "width": 2208,
        "height": 1242,
        "css_width": 414,
        "css_height": 736,
        "pixel_ratio": 3,
        "orientation": 'landscape',
        "label": 'iPhone Plus 6/7/8 - horizontal',
    },
    {
        "key": 'iphone-x-xs-11pro-portrait',
        "width": 1125,
        "height": 2436,
        "css_width": 375,
        "css_height": 812,
        "pixel_ratio": 3,
        "orientation": 'portrait',
        "label": 'iPhone X/XS/11 Pro - vertical',
    },
    {
        "key": 'iphone-x-xs-11pro-landscape',
        "width": 2436,
        "height": 1125,
        "css_width": 375,
        "css_height": 812,
        "pixel_ratio": 3,
        "orientation": 'landscape',
        "label": 'iPhone X/XS/11 Pro - horizontal',
    },
    {
        "key": 'iphone-xr-11-portrait',
        "width": 828,
        "height": 1792,
        "css_width": 414,
        "css_height": 896,
        "pixel_ratio": 2,
        "orientation": 'portrait',
        "label": 'iPhone XR/11 - vertical',
    },
    {
        "key": 'iphone-xr-11-landscape',
        "width": 1792,
        "height": 828,
        "css_width": 414,
        "css_height": 896,
        "pixel_ratio": 2,
        "orientation": 'landscape',
        "label": 'iPhone XR/11 - horizontal',
    },
    {
        "key": 'iphone-xsmax-11promax-portrait',
        "width": 1242,
        "height": 2688,
        "css_width": 414,
        "css_height": 896,
        "pixel_ratio": 3,
        "orientation": 'portrait',
        "label": 'iPhone XS Max/11 Pro Max - vertical',
    },
    {
        "key": 'iphone-xsmax-11promax-landscape',
        "width": 2688,
        "height": 1242,
        "css_width": 414,
        "css_height": 896,
        "pixel_ratio": 3,
        "orientation": 'landscape',
        "label": 'iPhone XS Max/11 Pro Max - horizontal',
    },
    {
        "key": 'iphone-12-13-mini-portrait',
        "width": 1080,
        "height": 2340,
        "css_width": 360,
        "css_height": 780,
        "pixel_ratio": 3,
        "orientation": 'portrait',
        "label": 'iPhone 12/13 mini - vertical',
    },
    {
        "key": 'iphone-12-13-mini-landscape',
        "width": 2340,
        "height": 1080,
        "css_width": 360,
        "css_height": 780,
        "pixel_ratio": 3,
        "orientation": 'landscape',
        "label": 'iPhone 12/13 mini - horizontal',
    },
    {
        "key": 'iphone-12-13-14-15-portrait',
        "width": 1170,
        "height": 2532,
        "css_width": 390,
        "css_height": 844,
        "pixel_ratio": 3,
        "orientation": 'portrait',
        "label": 'iPhone 12/13/14/15 - vertical',
    },
    {
        "key": 'iphone-12-13-14-15-landscape',
        "width": 2532,
        "height": 1170,
        "css_width": 390,
        "css_height": 844,
        "pixel_ratio": 3,
        "orientation": 'landscape',
        "label": 'iPhone 12/13/14/15 - horizontal',
    },
    {
        "key": 'iphone-12-13-14-plus-promax-portrait',
        "width": 1284,
        "height": 2778,
        "css_width": 428,
        "css_height": 926,
        "pixel_ratio": 3,
        "orientation": 'portrait',
        "label": 'iPhone 12/13/14 Plus/Pro Max - vertical',
    },
    {
        "key": 'iphone-12-13-14-plus-promax-landscape',
        "width": 2778,
        "height": 1284,
        "css_width": 428,
        "css_height": 926,
        "pixel_ratio": 3,
        "orientation": 'landscape',
        "label": 'iPhone 12/13/14 Plus/Pro Max - horizontal',
    },
    {
        "key": 'iphone-14-15-pro-portrait',
        "width": 1179,
        "height": 2556,
        "css_width": 393,
        "css_height": 852,
        "pixel_ratio": 3,
        "orientation": 'portrait',
        "label": 'iPhone 14/15 Pro - vertical',
    },
    {
        "key": 'iphone-14-15-pro-landscape',
        "width": 2556,
        "height": 1179,
        "css_width": 393,
        "css_height": 852,
        "pixel_ratio": 3,
        "orientation": 'landscape',
        "label": 'iPhone 14/15 Pro - horizontal',
    },
    {
        "key": 'iphone-14-15-promax-portrait',
        "width": 1290,
        "height": 2796,
        "css_width": 430,
        "css_height": 932,
        "pixel_ratio": 3,
        "orientation": 'portrait',
        "label": 'iPhone 14/15 Pro Max - vertical',
    },
    {
        "key": 'iphone-14-15-promax-landscape',
        "width": 2796,
        "height": 1290,
        "css_width": 430,
        "css_height": 932,
        "pixel_ratio": 3,
        "orientation": 'landscape',
        "label": 'iPhone 14/15 Pro Max - horizontal',
    },
    {
        "key": 'ipad-9-7-portrait',
        "width": 1536,
        "height": 2048,
        "css_width": 768,
        "css_height": 1024,
        "pixel_ratio": 2,
        "orientation": 'portrait',
        "label": 'iPad 9.7" - vertical',
    },
    {
        "key": 'ipad-9-7-landscape',
        "width": 2048,
        "height": 1536,
        "css_width": 768,
        "css_height": 1024,
        "pixel_ratio": 2,
        "orientation": 'landscape',
        "label": 'iPad 9.7" - horizontal',
    },
    {
        "key": 'ipad-10-2-portrait',
        "width": 1620,
        "height": 2160,
        "css_width": 810,
        "css_height": 1080,
        "pixel_ratio": 2,
        "orientation": 'portrait',
        "label": 'iPad 10.2" - vertical',
    },
    {
        "key": 'ipad-10-2-landscape',
        "width": 2160,
        "height": 1620,
        "css_width": 810,
        "css_height": 1080,
        "pixel_ratio": 2,
        "orientation": 'landscape',
        "label": 'iPad 10.2" - horizontal',
    },
    {
        "key": 'ipad-10-5-air-portrait',
        "width": 1668,
        "height": 2224,
        "css_width": 834,
        "css_height": 1112,
        "pixel_ratio": 2,
        "orientation": 'portrait',
        "label": 'iPad 10.5" / Air - vertical',
    },
    {
        "key": 'ipad-10-5-air-landscape',
        "width": 2224,
        "height": 1668,
        "css_width": 834,
        "css_height": 1112,
        "pixel_ratio": 2,
        "orientation": 'landscape',
        "label": 'iPad 10.5" / Air - horizontal',
    },
    {
        "key": 'ipad-11-pro-portrait',
        "width": 1668,
        "height": 2388,
        "css_width": 834,
        "css_height": 1194,
        "pixel_ratio": 2,
        "orientation": 'portrait',
        "label": 'iPad Pro 11" - vertical',
    },
    {
        "key": 'ipad-11-pro-landscape',
        "width": 2388,
        "height": 1668,
        "css_width": 834,
        "css_height": 1194,
        "pixel_ratio": 2,
        "orientation": 'landscape',
        "label": 'iPad Pro 11" - horizontal',
    },
    {
        "key": 'ipad-12-9-pro-portrait',
        "width": 2048,
        "height": 2732,
        "css_width": 1024,
        "css_height": 1366,
        "pixel_ratio": 2,
        "orientation": 'portrait',
        "label": 'iPad Pro 12.9" - vertical',
    },
    {
        "key": 'ipad-12-9-pro-landscape',
        "width": 2732,
        "height": 2048,
        "css_width": 1024,
        "css_height": 1366,
        "pixel_ratio": 2,
        "orientation": 'landscape',
        "label": 'iPad Pro 12.9" - horizontal',
    },
]

PWA_STARTUP_CANVAS_RGB = (18, 18, 18)
PWA_STARTUP_IMAGE_SPECS_BY_KEY = {
    spec["key"]: spec
    for spec in PWA_STARTUP_IMAGE_SPECS
}


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """Build a PNG chunk with its CRC checksum."""
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


@lru_cache(maxsize=4)
def _solid_png_bytes(width: int, height: int, rgb: tuple[int, int, int] = PWA_STARTUP_CANVAS_RGB) -> bytes:
    """Generate a solid-color PNG using only Python's standard library.

    Startup images are intentionally generated instead of stored as base64 or
    binary files. This keeps the app routes stable while avoiding a very large
    Python source file in code exports.
    """
    if width <= 0 or height <= 0:
        raise ValueError("PWA startup image dimensions must be positive")

    red, green, blue = rgb
    row = bytes((red, green, blue)) * width
    raw = b"".join(b"\x00" + row for _ in range(height))

    png_signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)

    return b"".join(
        (
            png_signature,
            _png_chunk(b"IHDR", ihdr),
            _png_chunk(b"IDAT", zlib.compress(raw, level=9)),
            _png_chunk(b"IEND", b""),
        )
    )


def pwa_startup_image_bytes(image_key: str) -> bytes | None:
    """Return generated PNG bytes for a supported startup image key."""
    spec = PWA_STARTUP_IMAGE_SPECS_BY_KEY.get(image_key)
    if not spec:
        return None
    return _solid_png_bytes(spec["width"], spec["height"])

