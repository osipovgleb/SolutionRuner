"""Gateway operations needed by content-rule repair stages."""

from typing import Any, Protocol

from .models import ProblemTarget


class RightTriangleGateway(Protocol):
    """Expose only the MCP operations used by this deterministic runner."""

    def get_source_catalog_children(
        self, parent_id: str, parent_type: str
    ) -> dict[str, Any]:
        """Return the ordered children of one explicit source group."""

    def find_source_catalog_path(
        self, catalog_snapshot_id: str, source_id: str, target_type: str
    ) -> dict[str, Any]:
        """Resolve one visible source id within an explicit catalog."""

    def get_problem_context(self, problem_id: str) -> dict[str, Any]:
        """Return one current schema-v3 transformation context."""

    def get_source_asset(self, source_asset_id: str) -> dict[str, Any]:
        """Return authoritative metadata for one pinned shared asset."""

    def get_asset_metadata(self, asset_id: str) -> dict[str, Any]:
        """Return authoritative metadata for one current condition asset."""

    def download_condition_asset(self, target: ProblemTarget) -> Any:
        """Download one current condition image for a declared content rule."""

    def get_problem_asset_target_context(
        self, problem_id: str, transformation_target_id: str
    ) -> dict[str, Any]:
        """Read the current image target before an explicit image repair."""

    def apply_problem_transformations(
        self, problem_id: str, transformations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Apply one atomic problem transformation batch."""

    def attach_source_asset_to_problems(
        self,
        *,
        source_asset_id: str,
        section_id: str,
        alt_text: str,
        problem_ids: list[str],
    ) -> dict[str, Any]:
        """Attach one shared library asset to explicit problem solution sections."""

    def get_problem_pipeline_state(self, problem_id: str) -> dict[str, Any]:
        """Return the current Helpers values and concurrency token."""

    def set_problem_pipeline_stage_state_batch(
        self, stage: str, updates: list[dict[str, Any]], reason: str
    ) -> dict[str, Any]:
        """Persist an exact token-bound pipeline stage override."""
