"""Describe source format and visible polygon color."""

from pathlib import Path
from urllib.parse import urlparse

import numpy as np


def _source_format(src, source_info):
    source_info_text = str(source_info)
    if source_info_text.lower().startswith("image/"):
        raw_format = source_info_text.split("/", 1)[1].split(";", 1)[0]
    else:
        raw_format = Path(source_info_text).suffix.lstrip(".")
        if not raw_format:
            raw_format = Path(urlparse(src).path).suffix.lstrip(".")
    raw_format_lower = raw_format.lower()
    if "bmp" in raw_format_lower:
        image_format = "BMP"
    elif raw_format_lower in {"jpg", "jpeg", "pjpeg"}:
        image_format = "JPEG"
    elif raw_format_lower:
        image_format = raw_format_lower.upper()
    else:
        image_format = "UNKNOWN"

    return image_format


def _visual_type(rgba, base_mask):
    shape_pixels = rgba[:, :, :3][base_mask > 0].astype(np.float32)
    if shape_pixels.size == 0:
        visual_type = "unknown"
    else:
        median_r, median_g, median_b = np.median(shape_pixels, axis=0)
        if max(median_r, median_g, median_b) - min(median_r, median_g, median_b) <= 12:
            visual_type = "grayscale"
        elif median_b >= median_r + 20 and median_b >= median_g + 10:
            visual_type = "blue"
        else:
            visual_type = "color"

    return visual_type
