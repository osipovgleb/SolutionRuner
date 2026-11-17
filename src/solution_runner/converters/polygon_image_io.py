"""Load polygon source images and derive stable identifiers."""

import io
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np
import requests
from PIL import Image


def is_url(s: str) -> bool:
    p = urlparse(s)
    return p.scheme in {"http", "https"}


def load_image(src: str) -> tuple[np.ndarray, str]:
    if is_url(src):
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(src, headers=headers, timeout=60)
        resp.raise_for_status()
        content_type = (resp.headers.get("content-type") or "").lower()
        if "svg" in content_type:
            raise ValueError("source is not raster (svg)")
        data = resp.content
        img = Image.open(io.BytesIO(data)).convert("RGBA")
        return np.array(img), content_type

    path = Path(src)
    img = Image.open(path).convert("RGBA")
    return np.array(img), str(path)


def extract_id(src: str) -> str:
    try:
        query = parse_qs(urlparse(src).query)
    except (ValueError, TypeError, AttributeError):
        query = {}
    return query["id"][0] if query.get("id") else Path(src).stem
