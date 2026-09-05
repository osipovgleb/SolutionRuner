"""Provide JSON-RPC transport contracts and response decoding for polygon MCP calls."""

from __future__ import annotations

import json
from typing import Any, Protocol


MCP_PROTOCOL_VERSION = "2025-06-18"


class McpCallError(RuntimeError):
    """Report one failed MCP operation without exposing credentials."""


class HttpTransport(Protocol):
    """Describe the small HTTP client surface used by JSON-RPC calls."""

    def post(self, url: str, *, json: dict[str, object]) -> Any:
        """Post one JSON-RPC envelope."""

    def close(self) -> None:
        """Close pooled transport resources."""


def default_transport(*, api_key: str, timeout_seconds: float) -> HttpTransport:
    """Create the production authenticated HTTP pool lazily."""

    import httpx

    return httpx.Client(
        timeout=httpx.Timeout(timeout_seconds),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
        },
    )


def content_text(result: dict[str, Any]) -> str:
    """Join text blocks from one MCP CallToolResult."""

    return "\n".join(
        str(block.get("text") or "")
        for block in result.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    ).strip()


def unpack_result(result: dict[str, Any]) -> dict[str, Any]:
    """Extract one structured TeacherHelper payload."""

    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    for block in result.get("content", []):
        if not isinstance(block, dict) or block.get("type") != "text":
            continue
        try:
            decoded = json.loads(str(block.get("text") or ""))
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, dict):
            return decoded
    raise McpCallError("MCP tool returned no structured JSON payload")
