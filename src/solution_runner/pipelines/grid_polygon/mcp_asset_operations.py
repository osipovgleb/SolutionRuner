"""Download, upload and reconcile gateway assets."""

from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urljoin
from uuid import UUID

from .mcp_transport import McpCallError

SOURCE_SITE_ID = "7bed2492-5b8b-4c88-9be8-7d47916cd7c6"


class AssetOperations:
    """Provide verified asset transfer operations for a JSON-RPC gateway."""

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
        value = (
            transformation.get("value") if isinstance(transformation, dict) else None
        )
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
        content_type = (
            str(metadata.get("content_type") or contract.get("content_type") or "")
            .split(";", 1)[0]
            .lower()
        )
        relative_url = str(contract.get("url") or "")
        if not relative_url:
            raise McpCallError("current asset has no download capability")
        try:
            import httpx

            response = httpx.get(urljoin(self._url, relative_url), timeout=60.0)
            response.raise_for_status()
            data = response.content
        except Exception as exc:  # file transport varies.
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
        except Exception as exc:  # signed upload transport varies.
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
            raise McpCallError(
                "uploaded solution asset readback differs from local SVG"
            )
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
        except Exception as exc:  # signed upload transport varies.
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
            raise McpCallError(
                "uploaded condition asset readback differs from local SVG"
            )
        return {
            "source_asset_id": source_asset_id,
            "sha256": sha256,
            "source_problem_id": source_problem_id,
        }
