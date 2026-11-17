"""Transfer and validate raster or SVG asset bytes."""

from __future__ import annotations

import io
from typing import Any

import httpx
from PIL import Image

if __package__:
    from .mcp_polygon_client import _safe_exception
    from .mcp_polygon_models import CandidateRejected, PipelineError
    from .mcp_polygon_util import _sha256_bytes
else:
    from mcp_polygon_client import _safe_exception
    from mcp_polygon_models import CandidateRejected, PipelineError
    from mcp_polygon_util import _sha256_bytes


def _transfer_get(contract: dict[str, Any], *, timeout_seconds: float) -> bytes:
    """Execute one capability-bound GET with only the returned headers."""

    if str(contract.get("method")) != "GET":
        raise PipelineError("download contract method is not GET")
    url = str(contract.get("download_url") or "")
    headers = contract.get("headers")
    if not url or not isinstance(headers, dict):
        raise PipelineError("download contract is incomplete")
    with httpx.Client(
        timeout=httpx.Timeout(timeout_seconds), follow_redirects=False
    ) as client:
        response = client.get(url, headers={str(k): str(v) for k, v in headers.items()})
        response.raise_for_status()
        return response.content


def _transfer_put(
    contract: dict[str, Any], data: bytes, *, timeout_seconds: float
) -> dict[str, Any]:
    """Execute one capability-bound raw PUT with only the returned headers."""

    if str(contract.get("method")) != "PUT":
        raise PipelineError("upload contract method is not PUT")
    url = str(contract.get("upload_url") or "")
    headers = contract.get("headers")
    if not url or not isinstance(headers, dict) or not headers:
        raise PipelineError("upload contract is incomplete")
    with httpx.Client(
        timeout=httpx.Timeout(timeout_seconds), follow_redirects=False
    ) as client:
        response = client.put(
            url,
            headers={str(k): str(v) for k, v in headers.items()},
            content=data,
        )
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        raise PipelineError("source asset upload returned no JSON object")
    return payload


def _validate_png(data: bytes, contract: dict[str, Any]) -> tuple[str, tuple[int, int]]:
    """Validate one supported raster, including historical MIME mismatches."""

    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        expected_format = "PNG"
    elif data.startswith(b"\xff\xd8\xff"):
        expected_format = "JPEG"
    elif data.startswith(b"BM"):
        expected_format = "BMP"
    else:
        raise CandidateRejected(
            "downloaded bytes are not a supported PNG/JPEG/BMP raster"
        )
    digest = _sha256_bytes(data)
    expected_digest = str(contract.get("sha256") or "").lower()
    if expected_digest and digest != expected_digest:
        raise CandidateRejected("downloaded raster sha256 differs from MCP metadata")
    expected_size = contract.get("size_bytes")
    if expected_size is not None and int(expected_size) != len(data):
        raise CandidateRejected("downloaded raster size differs from MCP metadata")
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format != expected_format:
                raise CandidateRejected(
                    f"Pillow decoded {image.format}, not {expected_format}"
                )
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
    except CandidateRejected:
        raise
    except Exception as exc:  # decoder failures are input rejections.
        raise CandidateRejected(f"invalid raster: {_safe_exception(exc)}") from exc
    if width <= 0 or height <= 0:
        raise CandidateRejected("raster has invalid dimensions")
    return digest, (width, height)
