"""Centralize narrow TeacherHelper MCP operations and retry semantics."""

from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any, Callable, Protocol, Sequence
from urllib.parse import urljoin
from uuid import UUID

from .mcp_transport import (
    HttpTransport,
    McpCallError,
    content_text,
    default_transport,
    unpack_result,
)


DEFAULT_MCP_URL = "https://lessons-helper.ru/mcp"
SOURCE_SITE_ID = "7bed2492-5b8b-4c88-9be8-7d47916cd7c6"


class McpGateway(Protocol):
    """Expose typed problem operations to pipeline runtimes."""

    def get_problem_context(self, problem_id: str) -> dict[str, Any]:
        """Return normalized problem transformation context."""

    def get_problem_batch(self, problem_ids: Sequence[str]) -> dict[str, Any]:
        """Return normalized content for up to 30 known problem UUIDs."""

    def get_asset_metadata(self, asset_id: str) -> dict[str, Any]:
        """Return authoritative metadata for one current asset UUID."""

    def get_source_catalog_children(
        self,
        parent_id: str,
        parent_type: str,
    ) -> dict[str, Any]:
        """Return ordered source catalog children."""

    def find_source_catalog_path(
        self,
        catalog_snapshot_id: str,
        source_id: str,
        target_type: str,
    ) -> dict[str, Any]:
        """Resolve one visible source id inside an explicit catalog."""

    def get_source_catalog_section_images(
        self,
        target_id: str,
        target_type: str,
    ) -> dict[str, Any]:
        """Return compact current condition and solution image evidence."""

    def get_source_catalog_missing_solution_summary(
        self,
        target_id: str,
        target_type: str,
    ) -> dict[str, Any]:
        """Return current source identities whose solution is empty."""

    def prepare_source_asset_upload(
        self,
        *,
        source_site_id: str,
        canonical_asset_key: str,
        content_type: str,
        byte_size: int,
        sha256: str,
    ) -> dict[str, Any]:
        """Create one exact upload target."""

    def get_source_asset(self, source_asset_id: str) -> dict[str, Any]:
        """Return authoritative source-asset metadata."""

    def upload_solution_asset(
        self,
        *,
        source_problem_id: str,
        svg_bytes: bytes,
        sha256: str,
    ) -> dict[str, str]:
        """Upload one verified solution SVG and return its stable identity."""

    def download_condition_asset(self, target: Any) -> Any:
        """Download one current condition asset without trusting its MIME type."""

    def download_original_condition_asset(self, target: Any) -> Any:
        """Download the source asset that preceded the current replacement."""

    def upload_condition_svg(
        self,
        *,
        source_problem_id: str,
        svg_bytes: bytes,
        sha256: str,
    ) -> dict[str, str]:
        """Upload one verified condition SVG and return its stable identity."""

    def replace_condition_asset(
        self,
        target: Any,
        *,
        replacement_asset_id: str,
        alt_text: str,
    ) -> dict[str, str]:
        """Replace image_1 and require authoritative asset-target readback."""

    def replace_problem_asset_target(
        self,
        *,
        problem_id: str,
        transformation_target_id: str,
        replacement_asset_id: str,
        alt_text: str,
    ) -> dict[str, str]:
        """Replace one exact problem asset target with authoritative readback."""

    def apply_problem_transformations(
        self,
        problem_id: str,
        transformations: Sequence[dict[str, Any]],
    ) -> dict[str, Any]:
        """Apply one problem's transformations without blind retry."""

    def attach_source_asset_to_problems(
        self,
        *,
        source_asset_id: str,
        section_id: str,
        alt_text: str,
        problem_ids: list[str],
    ) -> dict[str, Any]:
        """Attach one reusable SourceAsset to explicit solution sections."""

    def get_problem_asset_target_context(
        self,
        problem_id: str,
        transformation_target_id: str,
    ) -> dict[str, Any]:
        """Return authoritative asset target readback."""

    def get_problem_pipeline_state(self, problem_id: str) -> dict[str, Any]:
        """Return pipeline stage values and concurrency tokens."""

    def reject_problem_content_pipeline(self, problem_id: str, reason: str) -> dict[str, Any]:
        """Explicitly reject one problem across the full content pipeline."""

    def set_problem_pipeline_stage_state_batch(
        self,
        stage: str,
        updates: Sequence[dict[str, Any]],
        reason: str,
    ) -> dict[str, Any]:
        """Apply token-bound pipeline state updates without blind retry."""


class JsonRpcMcpGateway:
    """Call stateless TeacherHelper Streamable HTTP MCP through typed methods."""

    def __init__(
        self,
        *,
        url: str,
        api_key: str,
        timeout_seconds: float = 60.0,
        transport: HttpTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Create one sequential gateway with injectable transport and sleep."""

        self._url = url
        self._transport = transport or default_transport(
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )
        self._sleep = sleep
        self._next_id = 0

    def close(self) -> None:
        """Close the shared HTTP pool."""

        self._transport.close()

    def _call(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        read_only: bool,
    ) -> dict[str, Any]:
        """Call one tool with retry only when the operation is read-only."""

        attempts = 3 if read_only else 1
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            self._next_id += 1
            envelope = {
                "jsonrpc": "2.0",
                "id": self._next_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            }
            try:
                response = self._transport.post(self._url, json=envelope)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise McpCallError("MCP response is not a JSON object")
                if payload.get("error"):
                    raise McpCallError(
                        json.dumps(payload["error"], ensure_ascii=False)[:1000]
                    )
                result = payload.get("result")
                if not isinstance(result, dict):
                    raise McpCallError("MCP response has no result object")
                if result.get("isError"):
                    raise McpCallError(content_text(result) or "MCP tool failed")
                return unpack_result(result)
            except Exception as exc:  # noqa: BLE001 - transport implementations vary.
                last_error = exc
                if "Normalized content is unavailable" in str(exc):
                    break
                if attempt < attempts:
                    self._sleep(float(attempt))
        message = " ".join(str(last_error or "unknown error").split())[:1000]
        if not read_only:
            raise McpCallError(
                f"{name} returned an ambiguous write response; reconcile by readback: {message}"
            ) from last_error
        raise McpCallError(
            f"{name} failed after {attempts} attempts: {message}"
        ) from last_error

    def get_problem_context(self, problem_id: str) -> dict[str, Any]:
        """Return normalized problem transformation context."""

        return self._call(
            "get_problem_transformation_context",
            {"problem_id": problem_id},
            read_only=True,
        )

    def get_problem_batch(self, problem_ids: Sequence[str]) -> dict[str, Any]:
        """Return normalized content for one bounded problem batch."""

        if not 1 <= len(problem_ids) <= 30:
            raise ValueError("problem batch must contain 1 to 30 ids")
        return self._call(
            "get_problem_batch",
            {"problem_ids": list(problem_ids)},
            read_only=True,
        )

    def get_asset_metadata(self, asset_id: str) -> dict[str, Any]:
        """Return authoritative metadata for one current asset UUID."""

        return self._call(
            "get_asset",
            {"asset_id": asset_id},
            read_only=True,
        )

    def get_source_catalog_children(
        self,
        parent_id: str,
        parent_type: str,
    ) -> dict[str, Any]:
        """Return ordered children for one exact source parent."""

        return self._call(
            "get_source_catalog_children",
            {"parent_id": parent_id, "parent_type": parent_type},
            read_only=True,
        )

    def find_source_catalog_path(
        self,
        catalog_snapshot_id: str,
        source_id: str,
        target_type: str,
    ) -> dict[str, Any]:
        """Resolve one source id without retaining a group-specific UUID."""

        return self._call(
            "find_source_catalog_path",
            {
                "catalog_snapshot_id": catalog_snapshot_id,
                "query": source_id,
                "target_type": target_type,
            },
            read_only=True,
        )

    def get_source_catalog_section_images(
        self,
        target_id: str,
        target_type: str,
    ) -> dict[str, Any]:
        """Return compact current condition and solution image evidence."""

        return self._call(
            "get_source_catalog_section_images",
            {"target_id": target_id, "target_type": target_type},
            read_only=True,
        )

    def get_source_catalog_missing_solution_summary(
        self,
        target_id: str,
        target_type: str,
    ) -> dict[str, Any]:
        """Return current source identities whose solution is empty."""

        return self._call(
            "get_source_catalog_missing_solution_summary",
            {"target_id": target_id, "target_type": target_type},
            read_only=True,
        )

    def download_existing_svg(self, target: Any) -> Any:
        """Download one current ordinary SVG asset for a prepared target."""

        from .asset_preparation import ExistingSvgAsset

        downloaded = self.download_condition_asset(target)
        if downloaded.content_type != "image/svg+xml":
            raise McpCallError("current asset has no SVG download capability")
        return ExistingSvgAsset(
            asset_id=downloaded.asset_id,
            content_type=downloaded.content_type,
            alt_text=downloaded.alt_text,
            svg_bytes=downloaded.data,
        )

    def download_condition_asset(self, target: Any) -> Any:
        """Download one current ordinary condition asset exactly once."""

        from .ring_asset_preparation import ConditionAsset

        content = self.get_problem_context(target.problem_id).get("normalized_content")
        assets = content.get("assets", []) if isinstance(content, dict) else []
        matches = [
            asset
            for asset in assets
            if isinstance(asset, dict)
            and asset.get("asset_key") == target.asset_key
            and asset.get("kind") == "ordinary_image"
        ]
        if len(matches) != 1:
            raise McpCallError("existing SVG target has no unique current asset")
        asset = matches[0]
        asset_id = str(asset.get("asset_id") or "")
        return self._download_condition_asset_bytes(
            asset_id,
            alt_text=str(asset.get("alt") or ""),
        )

    def download_original_condition_asset(self, target: Any) -> Any:
        """Download a prior replacement's original raster, falling back to current."""

        target_id = f"asset:{target.asset_key}"
        context = self.get_problem_asset_target_context(target.problem_id, target_id)
        current = context.get("current_asset")
        if not isinstance(current, dict):
            raise McpCallError("condition target has no current asset")
        current_asset_id = str(
            context.get("current_asset_id") or current.get("asset_id") or ""
        )
        if not current_asset_id:
            raise McpCallError("condition target has no current asset identity")
        original_asset_id = self._original_replaced_asset_id(context)
        return self._download_condition_asset_bytes(
            original_asset_id or current_asset_id,
            alt_text=str(current.get("alt") or ""),
        )

    @staticmethod
    def _original_replaced_asset_id(context: dict[str, Any]) -> str | None:
        """Extract one safe original asset UUID from server-owned replacement HTML."""

        transformation = context.get("transformation")
        value = transformation.get("value") if isinstance(transformation, dict) else None
        html = str(value.get("html") or "") if isinstance(value, dict) else ""
        match = re.search(
            r"data-asset-id\s*=\s*['\"]([0-9a-fA-F-]{36})['\"]",
            html,
        )
        if match is None:
            match = re.search(r"/assets/([0-9a-fA-F-]{36})(?:[/'\"?]|$)", html)
        if match is None:
            return None
        candidate = match.group(1)
        try:
            return str(UUID(candidate))
        except ValueError:
            return None

    def _download_condition_asset_bytes(
        self,
        asset_id: str,
        *,
        alt_text: str,
    ) -> Any:
        """Download one exact asset identity returned by the MCP read boundary."""

        from .ring_asset_preparation import ConditionAsset

        metadata = self.get_asset_metadata(asset_id)
        contract = self._call("get_asset_file", {"asset_id": asset_id}, read_only=True)
        content_type = str(
            metadata.get("content_type") or contract.get("content_type") or ""
        ).split(";", 1)[0].lower()
        relative_url = str(contract.get("url") or "")
        if not relative_url:
            raise McpCallError("current asset has no download capability")
        try:
            import httpx

            response = httpx.get(urljoin(self._url, relative_url), timeout=60.0)
            response.raise_for_status()
            data = response.content
        except Exception as exc:  # noqa: BLE001 - file transport varies.
            raise McpCallError("existing SVG download failed") from exc
        return ConditionAsset(
            asset_id=asset_id,
            content_type=content_type,
            alt_text=alt_text,
            data=data,
        )

    def replace_existing_svg_alt(self, target: Any, asset: Any, alt_text: str) -> Any:
        """Rewrite only current asset alt and require authoritative readback."""

        from dataclasses import replace

        write_error: McpCallError | None = None
        try:
            self._call(
                "replace_problem_asset",
                {
                    "problem_id": target.problem_id,
                    "transformation_target_id": f"asset:{target.asset_key}",
                    "replacement_asset_id": asset.asset_id,
                    "scope": "target",
                    "alt_text": alt_text,
                },
                read_only=False,
            )
        except McpCallError as exc:
            write_error = exc
        context = self.get_problem_asset_target_context(
            target.problem_id,
            f"asset:{target.asset_key}",
        )
        current = context.get("current_asset")
        if (
            not isinstance(current, dict)
            or str(context.get("current_asset_id") or current.get("asset_id") or "")
            != asset.asset_id
            or str(current.get("alt") or "") != alt_text
        ):
            raise McpCallError(
                "existing SVG alt readback differs from requested value"
            ) from write_error
        return replace(asset, alt_text=alt_text)

    def prepare_source_asset_upload(
        self,
        *,
        source_site_id: str,
        canonical_asset_key: str,
        content_type: str,
        byte_size: int,
        sha256: str,
    ) -> dict[str, Any]:
        """Create one source-asset upload target without blind retry."""

        return self._call(
            "prepare_source_asset_upload",
            {
                "source_site_id": source_site_id,
                "canonical_asset_key": canonical_asset_key,
                "content_type": content_type,
                "byte_size": byte_size,
                "sha256": sha256,
            },
            read_only=False,
        )

    def get_source_asset(self, source_asset_id: str) -> dict[str, Any]:
        """Return authoritative source-asset metadata."""

        return self._call(
            "get_source_asset",
            {"source_asset_id": source_asset_id},
            read_only=True,
        )

    def upload_solution_asset(
        self,
        *,
        source_problem_id: str,
        svg_bytes: bytes,
        sha256: str,
    ) -> dict[str, str]:
        """Upload exact solution bytes and verify SourceAsset readback."""

        if hashlib.sha256(svg_bytes).hexdigest() != sha256:
            raise McpCallError("solution SVG digest changed before upload")
        contract = self._call(
            "prepare_source_asset_upload",
            {
                "source_site_id": SOURCE_SITE_ID,
                "canonical_asset_key": f"grid-polygon-solution-{sha256[:48]}",
                "byte_size": len(svg_bytes),
                "sha256": sha256,
                "content_type": "image/svg+xml",
            },
            read_only=False,
        )
        if str(contract.get("method") or "") != "PUT":
            raise McpCallError("source asset upload contract is not PUT")
        upload_url = str(contract.get("upload_url") or "")
        headers = contract.get("headers")
        if not upload_url or not isinstance(headers, dict) or not headers:
            raise McpCallError("source asset upload contract is incomplete")
        try:
            import httpx

            response = httpx.put(
                upload_url,
                headers={str(key): str(value) for key, value in headers.items()},
                content=svg_bytes,
                timeout=60.0,
            )
            response.raise_for_status()
            upload = response.json()
        except Exception as exc:  # noqa: BLE001 - signed upload transport varies.
            raise McpCallError(
                "solution upload returned an ambiguous response; reconcile by digest"
            ) from exc
        if not isinstance(upload, dict):
            raise McpCallError("source asset upload returned no JSON object")
        source_asset_id = str(upload.get("source_asset_id") or "")
        if not source_asset_id or str(upload.get("sha256") or "").lower() != sha256:
            raise McpCallError("source asset upload identity or digest is invalid")
        readback = self.get_source_asset(source_asset_id).get("source_asset")
        if (
            not isinstance(readback, dict)
            or str(readback.get("sha256") or "").lower() != sha256
            or str(readback.get("content_type") or "").split(";", 1)[0].lower()
            != "image/svg+xml"
        ):
            raise McpCallError("uploaded solution asset readback differs from local SVG")
        return {
            "source_asset_id": source_asset_id,
            "url": f"/assets/{source_asset_id}",
            "sha256": sha256,
            "source_problem_id": source_problem_id,
        }

    def upload_condition_svg(
        self,
        *,
        source_problem_id: str,
        svg_bytes: bytes,
        sha256: str,
    ) -> dict[str, str]:
        """Upload one ring condition SVG and verify its SourceAsset readback."""

        if hashlib.sha256(svg_bytes).hexdigest() != sha256:
            raise McpCallError("condition SVG digest changed before upload")
        contract = self.prepare_source_asset_upload(
            source_site_id=SOURCE_SITE_ID,
            canonical_asset_key=f"grid-ring-condition-{sha256[:48]}",
            content_type="image/svg+xml",
            byte_size=len(svg_bytes),
            sha256=sha256,
        )
        if str(contract.get("method") or "") != "PUT":
            raise McpCallError("condition asset upload contract is not PUT")
        upload_url = str(contract.get("upload_url") or "")
        headers = contract.get("headers")
        if not upload_url or not isinstance(headers, dict) or not headers:
            raise McpCallError("condition asset upload contract is incomplete")
        try:
            import httpx

            response = httpx.put(
                upload_url,
                headers={str(key): str(value) for key, value in headers.items()},
                content=svg_bytes,
                timeout=60.0,
            )
            response.raise_for_status()
            upload = response.json()
        except Exception as exc:  # noqa: BLE001 - signed upload transport varies.
            raise McpCallError(
                "condition upload returned an ambiguous response; reconcile by digest"
            ) from exc
        if not isinstance(upload, dict):
            raise McpCallError("condition asset upload returned no JSON object")
        source_asset_id = str(upload.get("source_asset_id") or "")
        if not source_asset_id or str(upload.get("sha256") or "").lower() != sha256:
            raise McpCallError("condition asset upload identity or digest is invalid")
        readback = self.get_source_asset(source_asset_id).get("source_asset")
        if (
            not isinstance(readback, dict)
            or str(readback.get("sha256") or "").lower() != sha256
            or str(readback.get("content_type") or "").split(";", 1)[0].lower()
            != "image/svg+xml"
        ):
            raise McpCallError("uploaded condition asset readback differs from local SVG")
        return {
            "source_asset_id": source_asset_id,
            "sha256": sha256,
            "source_problem_id": source_problem_id,
        }

    def replace_condition_asset(
        self,
        target: Any,
        *,
        replacement_asset_id: str,
        alt_text: str,
    ) -> dict[str, str]:
        """Replace one condition target and require exact identity and alt readback."""

        target_id = f"asset:{target.asset_key}"
        return self.replace_problem_asset_target(
            problem_id=target.problem_id,
            transformation_target_id=target_id,
            replacement_asset_id=replacement_asset_id,
            alt_text=alt_text,
        )

    def replace_problem_asset_target(
        self,
        *,
        problem_id: str,
        transformation_target_id: str,
        replacement_asset_id: str,
        alt_text: str,
    ) -> dict[str, str]:
        """Replace one exact problem asset target and require matching readback."""

        self.get_problem_asset_target_context(problem_id, transformation_target_id)
        write_error: McpCallError | None = None
        try:
            self._call(
                "replace_problem_asset",
                {
                    "problem_id": problem_id,
                    "transformation_target_id": transformation_target_id,
                    "replacement_asset_id": replacement_asset_id,
                    "scope": "target",
                    "alt_text": alt_text,
                },
                read_only=False,
            )
        except McpCallError as exc:
            write_error = exc
        context = self.get_problem_asset_target_context(
            problem_id,
            transformation_target_id,
        )
        current = context.get("current_asset")
        current_asset_id = str(
            context.get("current_asset_id")
            or (current.get("asset_id") if isinstance(current, dict) else "")
            or ""
        )
        current_alt = str(current.get("alt") or "") if isinstance(current, dict) else ""
        if current_asset_id != replacement_asset_id or current_alt != alt_text:
            raise McpCallError("asset replacement readback differs") from write_error
        return {"asset_id": current_asset_id, "alt": current_alt}

    def apply_problem_transformations(
        self,
        problem_id: str,
        transformations: Sequence[dict[str, Any]],
    ) -> dict[str, Any]:
        """Apply one problem transformation batch without blind retry."""

        return self._call(
            "apply_problem_transformations_batch",
            {
                "problem_id": problem_id,
                "transformations": list(transformations),
            },
            read_only=False,
        )

    def attach_source_asset_to_problems(
        self,
        *,
        source_asset_id: str,
        section_id: str,
        alt_text: str,
        problem_ids: list[str],
    ) -> dict[str, Any]:
        """Attach one reusable SourceAsset to explicit solution sections."""

        return self._call(
            "attach_source_asset_to_problems",
            {
                "source_asset_id": source_asset_id,
                "section_id": section_id,
                "alt_text": alt_text,
                "problem_ids": problem_ids,
            },
            read_only=False,
        )

    def get_problem_asset_target_context(
        self,
        problem_id: str,
        transformation_target_id: str,
    ) -> dict[str, Any]:
        """Return authoritative problem asset-target readback."""

        return self._call(
            "get_problem_asset_target_context",
            {
                "problem_id": problem_id,
                "transformation_target_id": transformation_target_id,
            },
            read_only=True,
        )

    def get_problem_pipeline_state(self, problem_id: str) -> dict[str, Any]:
        """Return pipeline stage values and concurrency tokens."""

        return self._call(
            "get_problem_pipeline_state",
            {"problem_id": problem_id},
            read_only=True,
        )

    def reject_problem_content_pipeline(self, problem_id: str, reason: str) -> dict[str, Any]:
        """Explicitly reject one problem without invoking a model or runner."""

        return self._call(
            "reject_problem_content_pipeline",
            {"problem_id": problem_id, "reason": reason},
            read_only=False,
        )

    def set_problem_pipeline_stage_state_batch(
        self,
        stage: str,
        updates: Sequence[dict[str, Any]],
        reason: str,
    ) -> dict[str, Any]:
        """Apply stage updates without blindly repeating an ambiguous write."""

        return self._call(
            "set_problem_pipeline_stage_state_batch",
            {"stage": stage, "updates": list(updates), "reason": reason},
            read_only=False,
        )
