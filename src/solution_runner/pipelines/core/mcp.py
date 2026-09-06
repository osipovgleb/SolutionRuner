"""Stable domain-neutral import boundary for TeacherHelper MCP access.

The implementation still lives in the historical geometry package during the
incremental migration. Domain launchers import this module so moving the
implementation later does not change every runner family.
"""

from solution_runner.pipelines.grid_polygon.mcp_runtime import (
    DEFAULT_MCP_URL,
    JsonRpcMcpGateway,
    McpCallError,
)

__all__ = ["DEFAULT_MCP_URL", "JsonRpcMcpGateway", "McpCallError"]
