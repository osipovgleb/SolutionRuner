"""Verify narrow MCP transport, result unpacking, and retry boundaries."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from solution_runner.pipelines.grid_polygon.asset_preparation import ExistingSvgAsset
from solution_runner.pipelines.grid_polygon.mcp_runtime import (
    JsonRpcMcpGateway,
    McpCallError,
)


class Response:
    """Provide the minimal HTTP response behavior used by the gateway."""

    def __init__(self, payload: dict[str, object], status_code: int = 200) -> None:
        """Store one response envelope and status."""

        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """Raise one transient status error for non-success responses."""

        if self.status_code >= 400:
            raise OSError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, object]:
        """Return the recorded JSON-RPC envelope."""

        return self.payload


class Transport:
    """Record calls and replay predetermined responses."""

    def __init__(self, responses: list[Response]) -> None:
        """Queue deterministic fake HTTP responses."""

        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def post(self, url: str, *, json: dict[str, object]) -> Response:
        """Record one request and return the next response."""

        self.calls.append(json)
        return self.responses.pop(0)

    def close(self) -> None:
        """Match the production transport lifecycle."""


def _success(payload: dict[str, object]) -> Response:
    """Wrap one structured TeacherHelper tool result."""

    return Response(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"structuredContent": payload, "content": []},
        }
    )


def test_gateway_exposes_narrow_problem_operations() -> None:
    """Keep raw MCP tool names inside one transport boundary."""

    transport = Transport(
        [
            _success({"problem_id": "p1", "content": {}}),
            _success({"asset_id": "asset-1", "content_type": "image/svg+xml"}),
            _success({"results": [{"problem_id": "p1"}]}),
            _success({"problem_id": "p1", "stage_details": {}}),
        ]
    )
    gateway = JsonRpcMcpGateway(
        url="https://example.invalid/mcp",
        api_key="secret",
        transport=transport,
        sleep=lambda _: None,
    )

    assert gateway.get_problem_context("p1")["problem_id"] == "p1"
    assert gateway.get_asset_metadata("asset-1")["content_type"] == "image/svg+xml"
    assert gateway.apply_problem_transformations("p1", [{"operation": "add"}])["results"]
    assert gateway.get_problem_pipeline_state("p1")["problem_id"] == "p1"
    assert [call["params"]["name"] for call in transport.calls] == [
        "get_problem_transformation_context",
        "get_asset",
        "apply_problem_transformations_batch",
        "get_problem_pipeline_state",
    ]
    assert transport.calls[2]["params"]["arguments"] == {
        "problem_id": "p1",
        "transformations": [{"operation": "add"}],
    }


def test_gateway_resolves_visible_group_inside_explicit_catalog() -> None:
    """Catch a runner falling back to a hard-coded internal source-group UUID."""

    transport = Transport(
        [_success({"target": {"id": "group-uuid", "source_id": "27238"}})]
    )
    gateway = JsonRpcMcpGateway(
        url="https://example.invalid/mcp",
        api_key="secret",
        transport=transport,
        sleep=lambda _: None,
    )

    result = gateway.find_source_catalog_path("catalog-uuid", "27238", "group")

    assert result["target"]["id"] == "group-uuid"
    assert transport.calls[0]["params"] == {
        "name": "find_source_catalog_path",
        "arguments": {
            "catalog_snapshot_id": "catalog-uuid",
            "query": "27238",
            "target_type": "group",
        },
    }


def test_read_retries_transient_failure_but_write_does_not_blindly_retry() -> None:
    """Avoid duplicating an ambiguous write while retaining bounded read retry."""

    read_transport = Transport([Response({}, 502), _success({"problem_id": "p1"})])
    read_gateway = JsonRpcMcpGateway(
        url="https://example.invalid/mcp",
        api_key="secret",
        transport=read_transport,
        sleep=lambda _: None,
    )
    assert read_gateway.get_problem_context("p1")["problem_id"] == "p1"
    assert len(read_transport.calls) == 2

    write_transport = Transport([Response({}, 502), _success({"results": []})])
    write_gateway = JsonRpcMcpGateway(
        url="https://example.invalid/mcp",
        api_key="secret",
        transport=write_transport,
        sleep=lambda _: None,
    )
    with pytest.raises(McpCallError, match="ambiguous"):
        write_gateway.apply_problem_transformations("p1", [{"operation": "add"}])
    assert len(write_transport.calls) == 1


def test_existing_svg_alt_reconciles_ambiguous_write_by_readback() -> None:
    """Accept only matching readback and retain an ambiguous write as failure cause."""

    target = SimpleNamespace(problem_id="p1", asset_key="image_1")
    asset = ExistingSvgAsset(
        asset_id="asset-1",
        content_type="image/svg+xml",
        alt_text="old",
        svg_bytes=b"<svg/>",
    )
    matching_gateway = JsonRpcMcpGateway(
        url="https://example.invalid/mcp",
        api_key="secret",
        transport=Transport(
            [
                Response({}, 502),
                _success(
                    {
                        "current_asset_id": "asset-1",
                        "current_asset": {"asset_id": "asset-1", "alt": "[(1,2)]"},
                    }
                ),
            ]
        ),
        sleep=lambda _: None,
    )

    updated = matching_gateway.replace_existing_svg_alt(
        target,
        asset,
        "[(1,2)]",
    )

    assert updated.alt_text == "[(1,2)]"

    mismatching_gateway = JsonRpcMcpGateway(
        url="https://example.invalid/mcp",
        api_key="secret",
        transport=Transport(
            [
                Response({}, 502),
                _success(
                    {
                        "current_asset_id": "asset-1",
                        "current_asset": {"asset_id": "asset-1", "alt": "old"},
                    }
                ),
            ]
        ),
        sleep=lambda _: None,
    )

    with pytest.raises(McpCallError, match="readback differs") as raised:
        mismatching_gateway.replace_existing_svg_alt(target, asset, "[(1,2)]")

    assert isinstance(raised.value.__cause__, McpCallError)
    assert "ambiguous write response" in str(raised.value.__cause__)


def test_solution_asset_replacement_targets_only_the_requested_asset() -> None:
    """Replace one generated solution asset without a section transformation batch."""

    transport = Transport(
        [
            _success(
                {
                    "current_asset_id": "asset-old",
                    "current_asset": {"asset_id": "asset-old", "alt": "old"},
                }
            ),
            _success({"problem_id": "p1"}),
            _success(
                {
                    "current_asset_id": "asset-new",
                    "current_asset": {"asset_id": "asset-new", "alt": "rectangle"},
                }
            ),
        ]
    )
    gateway = JsonRpcMcpGateway(
        url="https://example.invalid/mcp",
        api_key="secret",
        transport=transport,
        sleep=lambda _: None,
    )

    result = gateway.replace_problem_asset_target(
        problem_id="p1",
        transformation_target_id="asset:generated_solution_diagram",
        replacement_asset_id="asset-new",
        alt_text="rectangle",
    )

    assert result == {"asset_id": "asset-new", "alt": "rectangle"}
    assert [call["params"]["name"] for call in transport.calls] == [
        "get_problem_asset_target_context",
        "replace_problem_asset",
        "get_problem_asset_target_context",
    ]
    assert transport.calls[1]["params"]["arguments"] == {
        "problem_id": "p1",
        "transformation_target_id": "asset:generated_solution_diagram",
        "replacement_asset_id": "asset-new",
        "scope": "target",
        "alt_text": "rectangle",
    }


def test_ring_source_download_uses_original_asset_from_prior_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Re-run ring conversion from the original raster, not the replacement SVG."""

    original_asset_id = "5552a197-1c22-42e8-b530-6342799511ac"
    current_asset_id = "b08dd6ac-97cd-476b-a713-81c45b2b2184"
    transport = Transport(
        [
            _success(
                {
                    "current_asset_id": current_asset_id,
                    "current_asset": {
                        "asset_id": current_asset_id,
                        "alt": "Кольцо: R₁²=18, R₂²=10",
                    },
                    "transformation": {
                        "operation": "replace",
                        "value": {
                            "html": (
                                '<img data-asset-id="'
                                + original_asset_id
                                + '" data-asset-key="image_1" '
                                + 'src="/assets/'
                                + original_asset_id
                                + '"/>'
                            )
                        },
                    },
                }
            ),
            _success({"asset_id": original_asset_id, "content_type": "image/png"}),
            _success(
                {
                    "asset_id": original_asset_id,
                    "content_type": "image/png",
                    "url": f"/assets/{original_asset_id}/file",
                }
            ),
        ]
    )
    gateway = JsonRpcMcpGateway(
        url="https://example.invalid/mcp",
        api_key="secret",
        transport=transport,
        sleep=lambda _: None,
    )

    class FileResponse:
        """Return one deterministic original raster download."""

        content = b"\x89PNG\r\n\x1a\noriginal"

        def raise_for_status(self) -> None:
            """Accept the fake file response."""

    monkeypatch.setattr("httpx.get", lambda *_args, **_kwargs: FileResponse())

    downloaded = gateway.download_original_condition_asset(
        SimpleNamespace(problem_id="problem-263425", asset_key="image_1")
    )

    assert downloaded.asset_id == original_asset_id
    assert downloaded.content_type == "image/png"
    assert downloaded.data.endswith(b"original")
    assert [call["params"]["name"] for call in transport.calls] == [
        "get_problem_asset_target_context",
        "get_asset",
        "get_asset_file",
    ]
