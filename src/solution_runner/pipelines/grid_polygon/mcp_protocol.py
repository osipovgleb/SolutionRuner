"""Read and write operations required by geometry pipeline gateways."""

from collections.abc import Sequence
from typing import Any, Protocol


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

    def reject_problem_content_pipeline(
        self, problem_id: str, reason: str
    ) -> dict[str, Any]:
        """Explicitly reject one problem across the full content pipeline."""

    def set_problem_pipeline_stage_state_batch(
        self,
        stage: str,
        updates: Sequence[dict[str, Any]],
        reason: str,
    ) -> dict[str, Any]:
        """Apply token-bound pipeline state updates without blind retry."""
