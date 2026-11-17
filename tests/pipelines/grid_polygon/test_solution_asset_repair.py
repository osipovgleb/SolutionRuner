"""Verify rectangle-diagram repairs remain asset-only and target-local."""

from __future__ import annotations

import hashlib
from pathlib import Path

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.models import PreparedGridPolygon
from solution_runner.pipelines.grid_polygon.solution_asset_repair import (
    repair_rectangle_solution_asset,
)
from solution_runner.pipelines.grid_polygon.strategies import get_solution_strategy


def _prepared(tmp_path: Path) -> PreparedGridPolygon:
    """Build the minimized 244997 missing-side reproduction."""

    coordinates = ((2, 3), (1, 1), (4, 2), (2, 2))
    svg = tmp_path / "condition.svg"
    lines = [
        *(
            f'<line x1="{x}" y1="0" x2="{x}" y2="100" stroke="#bbb"/>'
            for x in range(0, 121, 20)
        ),
        *(
            f'<line x1="0" y1="{y}" x2="120" y2="{y}" stroke="#bbb"/>'
            for y in range(0, 101, 20)
        ),
    ]
    points = " ".join(f"{x * 20},{y * 20}" for x, y in coordinates)
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 100">'
        + "".join(lines)
        + f'<polygon points="{points}" fill="#8da3cc" stroke="#111"/>'
        + "</svg>",
        encoding="utf-8",
    )
    return PreparedGridPolygon(
        problem_id="problem-244997",
        source_problem_id="244997",
        condition_asset_id="condition-asset",
        condition_svg_path=svg,
        condition_svg_sha256=hashlib.sha256(svg.read_bytes()).hexdigest(),
        coordinates=coordinates,
        ordered_coordinates=coordinates,
        vertex_count=4,
        condition_was_replaced=True,
        converter_diagnostics={},
    )


class Gateway:
    """Provide the exact external boundary used by one asset-only repair."""

    def __init__(self) -> None:
        """Record uploaded and replaced asset identities."""

        self.uploaded: bytes | None = None
        self.replaced: tuple[str, str, str, str] | None = None

    def get_problem_asset_target_context(
        self,
        problem_id: str,
        transformation_target_id: str,
    ) -> dict[str, object]:
        """Return one existing generated rectangle target."""

        assert problem_id == "problem-244997"
        assert transformation_target_id == "asset:generated_solution_diagram"
        return {
            "current_asset_id": "asset-old",
            "current_asset": {"asset_id": "asset-old", "alt": "old rectangle"},
        }

    def get_asset_metadata(self, asset_id: str) -> dict[str, object]:
        """Return a digest that requires replacement."""

        assert asset_id == "asset-old"
        return {
            "asset_id": asset_id,
            "content_type": "image/svg+xml",
            "sha256": "0" * 64,
        }

    def upload_solution_asset(
        self,
        *,
        source_problem_id: str,
        svg_bytes: bytes,
        sha256: str,
    ) -> dict[str, str]:
        """Capture the corrected complete-rectangle SVG."""

        assert source_problem_id == "244997"
        assert hashlib.sha256(svg_bytes).hexdigest() == sha256
        self.uploaded = svg_bytes
        return {
            "source_asset_id": "asset-new",
            "url": "/assets/asset-new",
            "sha256": sha256,
        }

    def replace_problem_asset_target(
        self,
        *,
        problem_id: str,
        transformation_target_id: str,
        replacement_asset_id: str,
        alt_text: str,
    ) -> dict[str, str]:
        """Capture the one exact target replacement."""

        self.replaced = (
            problem_id,
            transformation_target_id,
            replacement_asset_id,
            alt_text,
        )
        return {"asset_id": replacement_asset_id, "alt": alt_text}


def test_repair_replaces_only_the_rectangle_solution_asset(tmp_path: Path) -> None:
    """Upload a closed rectangle and replace its existing asset target only."""

    prepared = _prepared(tmp_path)
    profile = get_group_profile("244997")
    strategy = get_solution_strategy(profile.strategy_key)
    gateway = Gateway()

    result = repair_rectangle_solution_asset(
        gateway,
        prepared,
        profile,
        strategy,
        apply=True,
    )

    assert result.status == "applied"
    assert gateway.uploaded is not None
    assert gateway.uploaded.count(b'data-kind="decomposition"') == 1
    assert gateway.replaced == (
        "problem-244997",
        "asset:generated_solution_diagram",
        "asset-new",
        str(list(prepared.coordinates)),
    )


def test_repair_reports_include_ordered_results_and_status_counts(tmp_path):
    import json

    from solution_runner.pipelines.core.models import ProblemStageResult
    from solution_runner.pipelines.grid_polygon.solution_asset_repair import (
        _write_reports,
    )

    results = (
        ProblemStageResult("p1", "1", "rectangle_solution_asset", "applied"),
        ProblemStageResult("p2", "2", "rectangle_solution_asset", "failed"),
    )
    _write_reports(tmp_path, results, ("g1",), True)
    rows = json.loads((tmp_path / "results.json").read_text())
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert [row["problem_id"] for row in rows] == ["p1", "p2"]
    assert summary == {
        "apply": True,
        "groups": ["g1"],
        "status_counts": {"applied": 1, "failed": 1},
        "targets": 2,
    }
