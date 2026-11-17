"""Communicate with the TeacherHelper MCP endpoint."""

from __future__ import annotations

import json
import threading
import time
from typing import Any

import httpx

if __package__:
    from .mcp_polygon_config import (
        MCP_PROTOCOL_VERSION,
        REQUIRED_MCP_TOOLS,
        REQUIRED_ROLLBACK_MCP_TOOLS,
    )
    from .mcp_polygon_events import EventLogger
    from .mcp_polygon_models import McpCallError, PipelineError
else:
    from mcp_polygon_config import (
        MCP_PROTOCOL_VERSION,
        REQUIRED_MCP_TOOLS,
        REQUIRED_ROLLBACK_MCP_TOOLS,
    )
    from mcp_polygon_events import EventLogger
    from mcp_polygon_models import McpCallError, PipelineError


class McpClient:
    """Call the stateless TeacherHelper Streamable HTTP JSON-RPC endpoint."""

    def __init__(
        self,
        *,
        url: str,
        api_key: str,
        timeout_seconds: float,
        logger: EventLogger,
    ) -> None:
        """Create an authenticated MCP client without logging its bearer token."""

        self.url = url
        self.logger = logger
        self._next_id = 0
        self._id_lock = threading.Lock()
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout_seconds),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
            },
        )

    def close(self) -> None:
        """Close the shared authenticated HTTP connection pool."""

        self._client.close()

    def call(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        attempts: int = 3,
    ) -> dict[str, Any]:
        """Call one MCP tool, retrying only with the same idempotent arguments."""

        arguments = arguments or {}
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            with self._id_lock:
                self._next_id += 1
                request_id = self._next_id
            payload = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
            try:
                response = self._client.post(self.url, json=payload)
                response.raise_for_status()
                envelope = response.json()
                if not isinstance(envelope, dict):
                    raise McpCallError("MCP response is not a JSON object")
                if envelope.get("error"):
                    raise McpCallError(_compact_error(envelope["error"]))
                result = envelope.get("result")
                if not isinstance(result, dict):
                    raise McpCallError("MCP response has no result object")
                if result.get("isError"):
                    raise McpCallError(_mcp_content_text(result) or "MCP tool failed")
                return _unpack_mcp_result(result)
            except (httpx.HTTPError, ValueError, McpCallError) as exc:
                last_error = exc
                if attempt >= attempts:
                    break
                delay = float(attempt)
                self.logger.emit(
                    "mcp_retry",
                    level="warning",
                    tool=name,
                    attempt=attempt,
                    delay_seconds=delay,
                    reason=_safe_exception(exc),
                )
                time.sleep(delay)
        raise McpCallError(
            f"{name} failed after {attempts} attempt(s): {_safe_exception(last_error)}"
        ) from last_error


def _compact_error(value: Any) -> str:
    """Return a bounded JSON error string."""

    return json.dumps(value, ensure_ascii=False, default=str)[:1000]


def _safe_exception(exc: BaseException | None) -> str:
    """Return a bounded one-line exception message suitable for logs."""

    if exc is None:
        return "unknown_error"
    return " ".join(str(exc).split())[:1000]


def _mcp_content_text(result: dict[str, Any]) -> str:
    """Join text blocks from one MCP CallToolResult."""

    return "\n".join(
        str(block.get("text") or "")
        for block in result.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    ).strip()


def _unpack_mcp_result(result: dict[str, Any]) -> dict[str, Any]:
    """Extract the structured payload returned by a TeacherHelper MCP tool."""

    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    for block in result.get("content", []):
        if not isinstance(block, dict) or block.get("type") != "text":
            continue
        text = str(block.get("text") or "").strip()
        if not text:
            continue
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, dict):
            return decoded
    raise McpCallError("MCP tool returned no structured JSON payload")


def _validate_startup(client: McpClient, *, mode: str, logger: EventLogger) -> str:
    """Verify identity, scopes, role, and all required MCP tools."""

    writes = mode in {"apply", "rollback"}
    info = client.call("mcp_server_info", attempts=3)
    scopes = {
        str(scope) for scope in info.get("effective_scopes", info.get("scopes", []))
    }
    required_scopes = {"source_content:read", "source_groups:read"}
    if writes:
        required_scopes.add("source_content:write")
    missing_scopes = sorted(required_scopes - scopes)
    if missing_scopes:
        raise PipelineError(f"MCP credential lacks scopes: {missing_scopes}")

    capabilities = client.call("get_mcp_capabilities", attempts=3)
    usable = {
        str(item.get("name"))
        for item in capabilities.get("usable_tools", [])
        if isinstance(item, dict) and item.get("usable") is True
    }
    required_tools = (
        REQUIRED_ROLLBACK_MCP_TOOLS if mode == "rollback" else REQUIRED_MCP_TOOLS
    )
    missing_tools = sorted(required_tools - usable)
    if missing_tools:
        raise PipelineError(f"MCP tools are unavailable: {missing_tools}")
    if writes and str(capabilities.get("role") or "") != "admin":
        raise PipelineError(f"{mode} mode requires an admin MCP identity")
    user_id = str(info.get("user_id") or "")
    if not user_id:
        raise PipelineError("mcp_server_info returned no user_id")
    logger.emit(
        "mcp_ready",
        user_id=user_id,
        role=capabilities.get("role"),
        scopes=sorted(scopes),
        mode=mode,
    )
    return user_id
