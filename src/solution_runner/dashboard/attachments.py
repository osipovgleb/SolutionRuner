"""Local image attachments for dashboard comments and native Codex delivery."""

import base64
import binascii
from pathlib import Path
from uuid import uuid4


MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGES = 4


def save_images(root: Path, images: object) -> list[dict[str, str]]:
    if not isinstance(images, list) or len(images) > MAX_IMAGES:
        raise ValueError("Можно прикрепить до 4 изображений, каждое до 5 МБ.")
    prepared = []
    for item in images:
        if not isinstance(item, dict):
            raise ValueError("Некорректное изображение.")
        encoded = item.get("data", "")
        if not isinstance(encoded, str) or len(encoded) > (MAX_IMAGE_BYTES * 4 // 3 + 8):
            raise ValueError("Изображение превышает 5 МБ.")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("Не удалось прочитать изображение.") from exc
        extension = (
            "png" if data.startswith(b"\x89PNG\r\n\x1a\n") else
            "jpg" if data.startswith(b"\xff\xd8\xff") else
            "gif" if data.startswith((b"GIF87a", b"GIF89a")) else
            "webp" if data[:4] == b"RIFF" and data[8:12] == b"WEBP" else None
        )
        if not extension or len(data) > MAX_IMAGE_BYTES:
            raise ValueError("Поддерживаются PNG, JPEG, GIF и WebP до 5 МБ.")
        prepared.append((data, extension, str(item.get("name") or "Изображение")[:200]))
    root.mkdir(parents=True, exist_ok=True)
    saved = []
    for data, extension, name in prepared:
        filename = f"{uuid4().hex}.{extension}"
        (root / filename).write_bytes(data)
        saved.append({"name": name, "url": f"/api/comment-images/{filename}"})
    return saved
