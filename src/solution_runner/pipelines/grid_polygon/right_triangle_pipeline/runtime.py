"""Run a manifest-scoped right-triangle repair through the MCP boundary."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any, Protocol

from ..models import GroupProfile, ProblemStageResult, ProblemTarget
from ..progress import ProgressReporter, TargetProgress
from .planner import (
    RightTrianglePlanError,
    build_altitude_repair_plan,
    build_elementary_repair_plan,
    build_repair_plan,
    build_tangent_bc_repair_plan,
    build_universal_repair_plan,
)


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

    def get_problem_asset_target_context(
        self, problem_id: str, transformation_target_id: str
    ) -> dict[str, Any]:
        """Read the current image target before an explicit image repair."""

    def apply_problem_transformations(
        self, problem_id: str, transformations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Apply one atomic problem transformation batch."""

    def get_problem_pipeline_state(self, problem_id: str) -> dict[str, Any]:
        """Return the current Helpers values and concurrency token."""

    def set_problem_pipeline_stage_state_batch(
        self, stage: str, updates: list[dict[str, Any]], reason: str
    ) -> dict[str, Any]:
        """Persist an exact token-bound pipeline stage override."""


def _children(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract the current group problem rows from either MCP list envelope."""

    candidates = payload.get("children")
    if not isinstance(candidates, list):
        candidates = payload.get("items")
    if not isinstance(candidates, list):
        raise RightTrianglePlanError("source group omitted children")
    return [item for item in candidates if isinstance(item, dict)]


def _problem_identity(item: dict[str, Any]) -> tuple[str, str]:
    """Return canonical and source ids for one source-group child row."""

    problem_id = str(item.get("problem_id") or item.get("id") or item.get("uuid") or "")
    source_problem_id = str(item.get("source_problem_id") or "")
    if not source_problem_id:
        match = re.fullmatch(r"\s*Задача\s+(.+?)\s*", str(item.get("name") or ""))
        source_problem_id = match.group(1) if match is not None else ""
    if not problem_id or not source_problem_id:
        raise RightTrianglePlanError("source group child omitted problem identity")
    return problem_id, source_problem_id


def _helpers_update(gateway: RightTriangleGateway, problem_id: str) -> None:
    """Set the verified P2–P5/P6 terminal branches and validate setter readback."""

    state = gateway.get_problem_pipeline_state(problem_id)
    current_helpers = (state.get("stage_details") or {}).get("helpers")
    if (
        isinstance(current_helpers, dict)
        and current_helpers.get("helpers_status") == "ready"
    ):
        return
    token = ((state.get("stage_state_tokens") or {}).get("helpers"))
    if not isinstance(token, str) or not token:
        raise RightTrianglePlanError("Helpers token is unavailable")
    branches = {
        **{
            branch: {"status": "ready", "revision": 2, "attempted_revision": 2}
            for branch in ("p2", "p3", "p4", "p5")
        },
        "p6": {"status": "not_required", "revision": 1, "attempted_revision": 1},
    }
    response = gateway.set_problem_pipeline_stage_state_batch(
        "helpers",
        [
            {
                "problem_id": problem_id,
                "expected_stage_state_token": token,
                "values": {"operation": "set_branches", "branches": branches},
            }
        ],
        "Verified right-triangle condition asset, solution, and answer",
    )
    results = response.get("results")
    if not isinstance(results, list) or len(results) != 1:
        raise RightTrianglePlanError("Helpers setter omitted single-target readback")
    values = results[0].get("values") if isinstance(results[0], dict) else None
    if not isinstance(values, dict) or values.get("helpers_status") != "ready":
        raise RightTrianglePlanError("Helpers readback is not ready")


def _resolved_group(payload: dict[str, Any]) -> str:
    """Extract one stable source-group UUID from a path-resolution response."""

    matches = payload.get("matches")
    group_id = ""
    if isinstance(matches, list) and len(matches) == 1:
        match = matches[0]
        group = match.get("group") if isinstance(match, dict) else None
        group_id = str(group.get("uuid") or "") if isinstance(group, dict) else ""
    if not group_id:
        raise RightTrianglePlanError(
            "source group path resolution must return one group UUID"
        )
    return group_id


def _condition_asset_id(context: dict[str, Any]) -> str:
    """Return the first group task's unique ordinary image_1 asset identity."""

    content = context.get("normalized_content")
    assets = content.get("assets") if isinstance(content, dict) else None
    matches = [
        item
        for item in (assets if isinstance(assets, list) else [])
        if isinstance(item, dict)
        and item.get("asset_key") == "image_1"
        and item.get("kind") == "ordinary_image"
        and item.get("asset_id")
    ]
    if len(matches) != 1:
        raise RightTrianglePlanError(
            "first group problem must have one ordinary image_1 asset"
        )
    return str(matches[0]["asset_id"])


def _solution_assets(context: dict[str, Any]) -> tuple[dict[str, str], ...]:
    """Return parent assets explicitly referenced by its solution section."""

    content = context.get("normalized_content")
    sections = content.get("sections") if isinstance(content, dict) else None
    solution_matches = [
        item
        for item in (sections if isinstance(sections, list) else [])
        if isinstance(item, dict) and item.get("key") == "solution"
    ]
    if len(solution_matches) > 1:
        raise RightTrianglePlanError("first group problem has multiple solutions")
    if not solution_matches:
        return ()
    keys = tuple(str(value) for value in solution_matches[0].get("asset_keys", []) if str(value))
    assets = content.get("assets") if isinstance(content, dict) else None
    by_key = {
        str(item.get("asset_key")): item
        for item in (assets if isinstance(assets, list) else [])
        if isinstance(item, dict) and item.get("asset_key") and item.get("asset_id")
    }
    if any(key not in by_key for key in keys):
        raise RightTrianglePlanError("first group solution asset is unresolved")
    return tuple(
        {
            "asset_key": key,
            "source_asset_id": str(by_key[key]["asset_id"]),
            "url": str(by_key[key].get("url") or f'/assets/{by_key[key]["asset_id"]}'),
            "alt": str(by_key[key].get("alt") or ""),
        }
        for key in keys
    )


def _context_fingerprint(context: dict[str, Any]) -> str:
    """Fingerprint the materialized inputs used to freeze one repair record."""

    content = context.get("normalized_content")
    encoded = json.dumps(
        content,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _planner_constraints(content_rule_key: str | None) -> dict[str, str]:
    """Return strict condition requirements selected by one content-rule profile."""

    if content_rule_key in {None, "right-triangle-sine"}:
        return {}
    if content_rule_key == "right-triangle-cosine-hypotenuse":
        return {"required_trig_name": "cos", "required_requested": "AB"}
    if content_rule_key == "right-triangle-tangent-hypotenuse":
        return {"required_trig_name": "tg", "required_requested": "AB"}
    if content_rule_key == "right-triangle-tangent-opposite-cathetus":
        return {}
    if content_rule_key == "right-triangle-universal":
        return {}
    if content_rule_key == "right-triangle-altitude-universal":
        return {}
    if content_rule_key == "isosceles-triangle-27284-base-from-sine":
        return {}
    if content_rule_key == "isosceles-triangle-27285-side-from-base-sine":
        return {}
    if content_rule_key in {
        "isosceles-triangle-27286-base-from-cosine",
        "isosceles-triangle-27287-side-from-base-cosine",
        "isosceles-triangle-27288-base-from-tangent",
        "isosceles-triangle-27289-side-from-base-tangent",
        "isosceles-triangle-27320-altitude-from-base-sine",
        "isosceles-triangle-27321-projection-from-base-sine",
        "isosceles-triangle-27322-altitude-from-base-cosine",
        "isosceles-triangle-27323-projection-from-base-cosine",
        "isosceles-triangle-27324-altitude-from-base-tangent",
        "isosceles-triangle-27325-projection-from-base-tangent",
        "isosceles-triangle-27326-altitude-from-side-sine",
        "isosceles-triangle-27327-projection-from-side-sine",
        "isosceles-triangle-27328-altitude-from-side-cosine",
        "isosceles-triangle-27329-projection-from-side-cosine",
        "isosceles-triangle-27330-sine-from-altitude-and-base",
        "isosceles-triangle-27331-cosine-from-altitude-and-base",
        "isosceles-triangle-27345-obtuse-sine-from-side-and-altitude",
        "isosceles-triangle-27346-obtuse-cosine-from-side-and-altitude",
        "isosceles-triangle-27347-obtuse-tangent-from-side-and-altitude",
        "isosceles-triangle-27349-obtuse-cosine-from-side-and-projection",
        "isosceles-triangle-27350-obtuse-tangent-from-side-and-projection",
        "isosceles-triangle-27351-obtuse-sine-from-altitude-and-projection",
        "isosceles-triangle-27352-obtuse-cosine-from-altitude-and-projection",
        "isosceles-triangle-27353-obtuse-tangent-from-altitude-and-projection",
        "isosceles-triangle-27589-area-from-side-and-30-degree-vertex-angle",
        "isosceles-triangle-27590-area-from-side-and-150-degree-vertex-angle",
        "isosceles-triangle-27619-area-from-side-and-base",
        "isosceles-triangle-27620-side-from-area-and-30-degree-vertex-angle",
        "isosceles-triangle-27621-side-from-area-and-150-degree-vertex-angle",
        "isosceles-triangle-27744-vertex-angle-from-base-angle",
        "isosceles-triangle-27745-base-angle-from-vertex-angle",
        "isosceles-triangle-27746-exterior-angle-from-vertex-angle",
        "isosceles-triangle-27747-vertex-angle-from-exterior-base-angle",
        "isosceles-triangle-27748-base-angle-from-exterior-vertex-angle",
        "isosceles-triangle-27750-smaller-angle-from-larger-angle",
        "isosceles-triangle-27754-smaller-angle-from-angle-difference",
        "isosceles-triangle-27760-vertex-angle-from-altitude-angle",
        "isosceles-triangle-27792-equilateral-height-from-side",
        "isosceles-triangle-27793-equilateral-side-from-height",
        "isosceles-triangle-27794-vertex-angle-from-base-altitude",
        "isosceles-triangle-27795-altitude-from-side-vertex-angle",
        "isosceles-triangle-27796-angle-from-side-altitude",
        "isosceles-triangle-27797-side-from-altitude-vertex-angle",
        "isosceles-triangle-27798-obtuse-altitude-from-side-angle",
        "isosceles-triangle-27799-side-from-base-vertex-angle",
        "isosceles-triangle-27800-base-from-side-vertex-angle",
        "isosceles-triangle-628232-base-from-side-tangent",
        "isosceles-triangle-676342-base-angle-from-exterior-angle",
        "isosceles-triangle-701874-base-angle-from-apex-exterior-angle",
    }:
        return {}
    if content_rule_key in {
        "right-triangle-leg-hypotenuse-area",
        "right-triangle-area-leg-difference",
        "right-triangle-acute-angle-difference",
        "right-triangle-acute-angle-ratio",
        "right-triangle-median-angle",
        "right-triangle-bisector-intersection-angle",
        "right-triangle-altitude-bisector-angle",
        "right-triangle-altitude-bisector-inverse",
        "right-triangle-altitude-line-angle",
        "right-triangle-altitude-median-inverse",
        "right-triangle-bisector-median-angle",
        "right-triangle-bisector-median-inverse",
        "right-triangle-altitude-length",
        "right-triangle-hypotenuse-projection-ah",
        "right-triangle-hypotenuse-projection-bh",
    }:
        return {}
    raise RightTrianglePlanError("unsupported content rule")


def _build_content_plan(
    context: dict[str, Any],
    *,
    parent_asset_id: str,
    content_rule_key: str | None,
    parent_solution_assets: tuple[dict[str, str], ...] = (),
):
    """Build one repair with the strict planner selected by the group profile."""

    if content_rule_key == "isosceles-triangle-27284-base-from-sine":
        from ..isosceles_triangle_pipeline.planner import (
            build_repair_plan as build_isosceles_repair_plan,
        )

        return build_isosceles_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27285-side-from-base-sine":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27285_repair_plan,
        )

        return build_group_27285_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27286-base-from-cosine":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27286_repair_plan,
        )

        return build_group_27286_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27287-side-from-base-cosine":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27287_repair_plan,
        )

        return build_group_27287_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27288-base-from-tangent":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27288_repair_plan,
        )

        return build_group_27288_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27289-side-from-base-tangent":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27289_repair_plan,
        )

        return build_group_27289_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
            parent_solution_assets=parent_solution_assets,
        )
    if content_rule_key == "isosceles-triangle-27320-altitude-from-base-sine":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27320_repair_plan,
        )

        return build_group_27320_repair_plan(
            context,
            parent_solution_assets=parent_solution_assets,
        )
    if content_rule_key == "isosceles-triangle-27321-projection-from-base-sine":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27321_repair_plan,
        )

        return build_group_27321_repair_plan(
            context,
            parent_solution_assets=parent_solution_assets,
        )
    if content_rule_key == "isosceles-triangle-27322-altitude-from-base-cosine":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27322_repair_plan,
        )

        return build_group_27322_repair_plan(
            context,
            parent_solution_assets=parent_solution_assets,
        )
    if content_rule_key == "isosceles-triangle-27323-projection-from-base-cosine":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27323_repair_plan,
        )

        return build_group_27323_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27324-altitude-from-base-tangent":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27324_repair_plan,
        )

        return build_group_27324_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27325-projection-from-base-tangent":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27325_repair_plan,
        )

        return build_group_27325_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27326-altitude-from-side-sine":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27326_repair_plan,
        )

        return build_group_27326_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27327-projection-from-side-sine":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27327_repair_plan,
        )

        return build_group_27327_repair_plan(
            context,
            parent_solution_assets=parent_solution_assets,
        )
    if content_rule_key == "isosceles-triangle-27328-altitude-from-side-cosine":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27328_repair_plan,
        )

        return build_group_27328_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27329-projection-from-side-cosine":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27329_repair_plan,
        )

        return build_group_27329_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27330-sine-from-altitude-and-base":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27330_repair_plan,
        )

        return build_group_27330_repair_plan(
            context,
            parent_solution_assets=parent_solution_assets,
        )
    if content_rule_key == "isosceles-triangle-27331-cosine-from-altitude-and-base":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27331_repair_plan,
        )

        return build_group_27331_repair_plan(
            context,
            parent_solution_assets=parent_solution_assets,
        )
    if content_rule_key == "isosceles-triangle-27345-obtuse-sine-from-side-and-altitude":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27345_repair_plan,
        )

        return build_group_27345_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27346-obtuse-cosine-from-side-and-altitude":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27346_repair_plan,
        )

        return build_group_27346_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27347-obtuse-tangent-from-side-and-altitude":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27347_repair_plan,
        )

        return build_group_27347_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27349-obtuse-cosine-from-side-and-projection":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27349_repair_plan,
        )

        return build_group_27349_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27350-obtuse-tangent-from-side-and-projection":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27350_repair_plan,
        )

        return build_group_27350_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27351-obtuse-sine-from-altitude-and-projection":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27351_repair_plan,
        )

        return build_group_27351_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27352-obtuse-cosine-from-altitude-and-projection":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27352_repair_plan,
        )

        return build_group_27352_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27353-obtuse-tangent-from-altitude-and-projection":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27353_repair_plan,
        )

        return build_group_27353_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27589-area-from-side-and-30-degree-vertex-angle":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27589_repair_plan,
        )

        return build_group_27589_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27590-area-from-side-and-150-degree-vertex-angle":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27590_repair_plan,
        )

        return build_group_27590_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27619-area-from-side-and-base":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27619_repair_plan,
        )

        return build_group_27619_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27620-side-from-area-and-30-degree-vertex-angle":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27620_repair_plan,
        )

        return build_group_27620_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27621-side-from-area-and-150-degree-vertex-angle":
        from ..isosceles_triangle_pipeline.planner import (
            build_group_27621_repair_plan,
        )

        return build_group_27621_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27744-vertex-angle-from-base-angle":
        from ..isosceles_triangle_pipeline.planner import build_group_27744_repair_plan

        return build_group_27744_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27745-base-angle-from-vertex-angle":
        from ..isosceles_triangle_pipeline.planner import build_group_27745_repair_plan

        return build_group_27745_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27746-exterior-angle-from-vertex-angle":
        from ..isosceles_triangle_pipeline.planner import build_group_27746_repair_plan

        return build_group_27746_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27747-vertex-angle-from-exterior-base-angle":
        from ..isosceles_triangle_pipeline.planner import build_group_27747_repair_plan

        return build_group_27747_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27748-base-angle-from-exterior-vertex-angle":
        from ..isosceles_triangle_pipeline.planner import build_group_27748_repair_plan

        return build_group_27748_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27750-smaller-angle-from-larger-angle":
        from ..isosceles_triangle_pipeline.planner import build_group_27750_repair_plan

        return build_group_27750_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27754-smaller-angle-from-angle-difference":
        from ..isosceles_triangle_pipeline.planner import build_group_27754_repair_plan

        return build_group_27754_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27760-vertex-angle-from-altitude-angle":
        from ..isosceles_triangle_pipeline.planner import build_group_27760_repair_plan

        return build_group_27760_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27792-equilateral-height-from-side":
        from ..isosceles_triangle_pipeline.planner import build_group_27792_repair_plan

        return build_group_27792_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27793-equilateral-side-from-height":
        from ..isosceles_triangle_pipeline.planner import build_group_27793_repair_plan

        return build_group_27793_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27794-vertex-angle-from-base-altitude":
        from ..isosceles_triangle_pipeline.planner import build_group_27794_repair_plan

        return build_group_27794_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27795-altitude-from-side-vertex-angle":
        from ..isosceles_triangle_pipeline.planner import build_group_27795_repair_plan

        return build_group_27795_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27796-angle-from-side-altitude":
        from ..isosceles_triangle_pipeline.planner import build_group_27796_repair_plan

        return build_group_27796_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27797-side-from-altitude-vertex-angle":
        from ..isosceles_triangle_pipeline.planner import build_group_27797_repair_plan

        return build_group_27797_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27798-obtuse-altitude-from-side-angle":
        from ..isosceles_triangle_pipeline.planner import build_group_27798_repair_plan

        return build_group_27798_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27799-side-from-base-vertex-angle":
        from ..isosceles_triangle_pipeline.planner import build_group_27799_repair_plan

        return build_group_27799_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-27800-base-from-side-vertex-angle":
        from ..isosceles_triangle_pipeline.planner import build_group_27800_repair_plan

        return build_group_27800_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-628232-base-from-side-tangent":
        from ..isosceles_triangle_pipeline.planner import build_group_628232_repair_plan

        return build_group_628232_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
            parent_solution_assets=parent_solution_assets,
        )
    if content_rule_key == "isosceles-triangle-676342-base-angle-from-exterior-angle":
        from ..isosceles_triangle_pipeline.planner import build_group_676342_repair_plan

        return build_group_676342_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )
    if content_rule_key == "isosceles-triangle-701874-base-angle-from-apex-exterior-angle":
        from ..isosceles_triangle_pipeline.planner import build_group_701874_repair_plan

        return build_group_701874_repair_plan(
            context,
            parent_condition_asset_id=parent_asset_id,
        )

    if content_rule_key == "right-triangle-tangent-opposite-cathetus":
        return build_tangent_bc_repair_plan(
            context,
            parent_asset_id=parent_asset_id,
        )
    if content_rule_key == "right-triangle-universal":
        return build_universal_repair_plan(
            context,
            parent_asset_id=parent_asset_id,
        )
    if content_rule_key == "right-triangle-altitude-universal":
        return build_altitude_repair_plan(
            context,
            parent_asset_id=parent_asset_id,
        )
    if content_rule_key in {
        "right-triangle-leg-hypotenuse-area",
        "right-triangle-area-leg-difference",
        "right-triangle-acute-angle-difference",
        "right-triangle-acute-angle-ratio",
        "right-triangle-median-angle",
        "right-triangle-bisector-intersection-angle",
        "right-triangle-altitude-bisector-angle",
        "right-triangle-altitude-bisector-inverse",
        "right-triangle-altitude-line-angle",
        "right-triangle-altitude-median-inverse",
        "right-triangle-bisector-median-angle",
        "right-triangle-bisector-median-inverse",
        "right-triangle-altitude-length",
        "right-triangle-hypotenuse-projection-ah",
        "right-triangle-hypotenuse-projection-bh",
    }:
        return build_elementary_repair_plan(
            context,
            parent_asset_id=parent_asset_id,
            content_rule_key=content_rule_key,
        )
    return build_repair_plan(
        context,
        parent_asset_id=parent_asset_id,
        **_planner_constraints(content_rule_key),
    )


def _prepared_record(
    gateway: RightTriangleGateway,
    child: dict[str, Any],
    parent_asset_id: str,
    content_rule_key: str | None = None,
    parent_solution_assets: tuple[dict[str, str], ...] = (),
) -> dict[str, Any]:
    """Freeze one group's current plan without changing source content."""

    problem_id, source_problem_id = _problem_identity(child)
    try:
        context = gateway.get_problem_context(problem_id)
        plan = _build_content_plan(
            context,
            parent_asset_id=parent_asset_id,
            content_rule_key=content_rule_key,
            parent_solution_assets=parent_solution_assets,
        )
        return {
            "problem_id": problem_id,
            "source_problem_id": source_problem_id,
            "status": "prepared",
            "input_fingerprint": _context_fingerprint(context),
            "expected_answer": plan.answer,
            "transformations": [deepcopy(item) for item in plan.transformations],
        }
    except Exception as exc:  # noqa: BLE001 - freeze one explicit blocker per task.
        return {
            "problem_id": problem_id,
            "source_problem_id": source_problem_id,
            "status": "blocked",
            "message": " ".join(str(exc).split())[:500],
            "transformations": [],
        }


def prepare_manifest(
    gateway: RightTriangleGateway,
    *,
    catalog_snapshot_id: str,
    source_group_number: str,
    max_workers: int,
) -> dict[str, Any]:
    """Discover one group and freeze every current deterministic repair."""

    if not 1 <= max_workers <= 10:
        raise RightTrianglePlanError("max_workers must be between 1 and 10")
    source_group_id = _resolved_group(
        gateway.find_source_catalog_path(
            catalog_snapshot_id,
            source_group_number,
            "group",
        )
    )
    children = _children(
        gateway.get_source_catalog_children(source_group_id, "group")
    )
    identities = [_problem_identity(child) for child in children]
    if not identities:
        raise RightTrianglePlanError("selected source group has no problems")
    asset_source_problem_id, asset_source_source_problem_id = identities[0]
    asset_source_context = gateway.get_problem_context(asset_source_problem_id)
    parent_asset_id = _condition_asset_id(asset_source_context)
    parent_solution_assets = _solution_assets(asset_source_context)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        records = list(
            executor.map(
                lambda child: _prepared_record(
                    gateway,
                    child,
                    parent_asset_id,
                    parent_solution_assets=parent_solution_assets,
                ),
                children,
            )
        )
    return {
        "schema_version": 1,
        "kind": "right_triangle_sine_solution_repair",
        "prepared_at": datetime.now(UTC).isoformat(),
        "catalog_snapshot_id": catalog_snapshot_id,
        "source_group_id": source_group_id,
        "source_group_number": source_group_number,
        "condition_asset": {
            "source_asset_id": parent_asset_id,
            "source_problem_id": asset_source_source_problem_id,
            "transformation_target_id": "asset:image_1",
        },
        "solution_assets": list(parent_solution_assets),
        "records": records,
    }


def _has_current_image(context: dict[str, Any]) -> bool:
    """Return whether image_1 currently exists and therefore needs target readback."""

    content = context.get("normalized_content")
    assets = content.get("assets") if isinstance(content, dict) else None
    return any(
        isinstance(item, dict) and item.get("asset_key") == "image_1"
        for item in (assets if isinstance(assets, list) else [])
    )


def _apply_record(
    gateway: RightTriangleGateway,
    record: dict[str, Any],
    parent_asset_id: str,
    content_rule_key: str | None,
    parent_solution_assets: tuple[dict[str, str], ...] = (),
) -> dict[str, Any]:
    """Converge one frozen record through content and Helpers readback."""

    problem_id = str(record.get("problem_id") or "")
    source_problem_id = str(record.get("source_problem_id") or "")
    if record.get("status") != "prepared":
        return {
            "problem_id": problem_id,
            "source_problem_id": source_problem_id,
            "status": "blocked",
            "message": str(record.get("message") or "manifest record is blocked"),
        }
    try:
        context = gateway.get_problem_context(problem_id)
        current_plan = _build_content_plan(
            context,
            parent_asset_id=parent_asset_id,
            content_rule_key=content_rule_key,
            parent_solution_assets=parent_solution_assets,
        )
        expected_answer = str(record.get("expected_answer") or "")
        frozen = record.get("transformations")
        if not isinstance(frozen, list) or not expected_answer:
            raise RightTrianglePlanError("prepared record is incomplete")
        if current_plan.answer != expected_answer:
            raise RightTrianglePlanError("condition or computed answer drifted after prepare")
        current_transformations = list(current_plan.transformations)
        changed = False
        if current_transformations:
            if current_transformations != frozen:
                raise RightTrianglePlanError("current repair differs from frozen manifest")
            if (
                any(item.get("transformation_target_id") == "asset:image_1" for item in frozen)
                and _has_current_image(context)
            ):
                gateway.get_problem_asset_target_context(problem_id, "asset:image_1")
            gateway.apply_problem_transformations(problem_id, deepcopy(frozen))
            changed = True
        readback = gateway.get_problem_context(problem_id)
        verified = _build_content_plan(
            readback,
            parent_asset_id=parent_asset_id,
            content_rule_key=content_rule_key,
            parent_solution_assets=parent_solution_assets,
        )
        if verified.answer != expected_answer or verified.transformations:
            raise RightTrianglePlanError("post-write content readback is incomplete")
        return {
            "problem_id": problem_id,
            "source_problem_id": source_problem_id,
            "status": "applied" if changed else "already_complete",
        }
    except Exception as exc:  # noqa: BLE001 - preserve one target-local failure.
        return {
            "problem_id": problem_id,
            "source_problem_id": source_problem_id,
            "status": "failed",
            "message": " ".join(str(exc).split())[:500],
        }


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build one content-free application summary from frozen-order results."""

    return {
        "applied_count": sum(item["status"] == "applied" for item in results),
        "already_complete_count": sum(
            item["status"] == "already_complete" for item in results
        ),
        "blocked_count": sum(item["status"] == "blocked" for item in results),
        "failed_count": sum(item["status"] == "failed" for item in results),
        "results": results,
    }


def _write_checkpoint(path: Path, summary: dict[str, Any]) -> None:
    """Atomically replace one local apply checkpoint after a completed batch."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def apply_frozen_manifest(
    gateway: RightTriangleGateway,
    manifest: dict[str, Any],
    *,
    batch_size: int,
    max_workers: int,
    checkpoint_path: Path,
    batch_pause_seconds: float = 0.0,
) -> dict[str, Any]:
    """Apply frozen records in bounded batches with restartable readback."""

    if batch_size <= 0:
        raise RightTrianglePlanError("batch_size must be positive")
    if batch_pause_seconds < 0:
        raise RightTrianglePlanError("batch_pause_seconds cannot be negative")
    if not 1 <= max_workers <= 10:
        raise RightTrianglePlanError("max_workers must be between 1 and 10")
    records = manifest.get("records")
    content_rule_key = manifest.get("content_rule_key")
    if content_rule_key is not None and not isinstance(content_rule_key, str):
        raise RightTrianglePlanError("prepared manifest content rule is invalid")
    _planner_constraints(content_rule_key)
    raw_solution_assets = manifest.get("solution_assets", [])
    if not isinstance(raw_solution_assets, list) or not all(
        isinstance(item, dict) for item in raw_solution_assets
    ):
        raise RightTrianglePlanError("manifest solution assets are invalid")
    parent_solution_assets = tuple(deepcopy(item) for item in raw_solution_assets)
    parent_asset_id = str(
        (manifest.get("condition_asset") or {}).get("source_asset_id") or ""
    )
    if not isinstance(records, list) or not parent_asset_id:
        raise RightTrianglePlanError("prepared manifest is incomplete")
    results: list[dict[str, Any]] = []
    for offset in range(0, len(records), batch_size):
        batch = records[offset : offset + batch_size]
        with ThreadPoolExecutor(max_workers=min(max_workers, len(batch) or 1)) as executor:
            results.extend(
                executor.map(
                    lambda record: _apply_record(
                        gateway,
                        record,
                        parent_asset_id,
                        content_rule_key,
                        parent_solution_assets,
                    ),
                    batch,
                )
            )
        _write_checkpoint(checkpoint_path, _summary(results))
        if offset + batch_size < len(records) and batch_pause_seconds:
            time.sleep(batch_pause_seconds)
    return _summary(results)


def _content_rule_manifest(
    gateway: RightTriangleGateway,
    targets: tuple[ProblemTarget, ...],
    *,
    profile: GroupProfile,
    parent_asset_id: str,
    parent_solution_assets: tuple[dict[str, str], ...],
    max_workers: int,
) -> dict[str, Any]:
    """Freeze exact per-task repairs for one already inventoried source group."""

    children = tuple(
        {
            "problem_id": target.problem_id,
            "source_problem_id": target.source_problem_id,
        }
        for target in targets
    )
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        records = list(
            executor.map(
                lambda child: _prepared_record(
                    gateway,
                    child,
                    parent_asset_id,
                    profile.content_rule_key,
                    parent_solution_assets,
                ),
                children,
            )
        )
    return {
        "schema_version": 1,
        "kind": "right_triangle_sine_solution_repair",
        "prepared_at": datetime.now(UTC).isoformat(),
        "catalog_snapshot_id": profile.catalog_snapshot_id,
        "source_group_id": profile.source_group_id,
        "source_group_number": profile.group_key,
        "content_rule_key": profile.content_rule_key,
        "condition_asset": {
            "source_asset_id": parent_asset_id,
            "transformation_target_id": "asset:image_1",
        },
        "solution_assets": list(parent_solution_assets),
        "records": records,
    }


def _read_content_rule_manifest(
    path: Path,
    targets: tuple[ProblemTarget, ...],
    profile: GroupProfile,
) -> dict[str, Any]:
    """Read and validate one frozen content-rule scope before resume."""

    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RightTrianglePlanError("prepared content-rule manifest is unreadable") from exc
    records = manifest.get("records") if isinstance(manifest, dict) else None
    if (
        not isinstance(records, list)
        or manifest.get("schema_version") != 1
        or manifest.get("catalog_snapshot_id") != profile.catalog_snapshot_id
        or manifest.get("source_group_id") != profile.source_group_id
        or manifest.get("content_rule_key") != profile.content_rule_key
        or [record.get("problem_id") for record in records]
        != [target.problem_id for target in targets]
    ):
        raise RightTrianglePlanError("prepared content-rule manifest scope drifted")
    return manifest


def _report_content_result(
    reporter: ProgressReporter,
    profile: GroupProfile,
    result: dict[str, Any],
    progress: TargetProgress,
) -> ProblemStageResult:
    """Emit old-pipeline milestones and project one content result."""

    status = str(result.get("status") or "failed")
    source_problem_id = str(result.get("source_problem_id") or "")
    problem_id = str(result.get("problem_id") or "")
    message = str(result.get("message") or "") or None
    if status == "applied":
        solution_action, answer_action, severity = (
            "SOLUTION WRITTEN",
            "ANSWER VERIFIED",
            "success",
        )
        stage_status = "applied"
    elif status == "already_complete":
        solution_action, answer_action, severity = (
            "SOLUTION ALREADY COMPLETE",
            "ANSWER VERIFIED",
            "success",
        )
        stage_status = "already_complete"
    elif status == "planned":
        solution_action, answer_action, severity = (
            "SOLUTION PLANNED",
            "ANSWER PLANNED",
            "info",
        )
        stage_status = "planned"
    else:
        solution_action, answer_action, severity = (
            "SOLUTION FAILED",
            "ANSWER SKIPPED",
            "error",
        )
        stage_status = "failed"
    details = {"message": message} if message else None
    reporter.task(
        profile.theme_title,
        profile.group_key,
        source_problem_id,
        progress,
        solution_action,
        severity=severity,
        stage="solution",
        details=details,
    )
    reporter.task(
        profile.theme_title,
        profile.group_key,
        source_problem_id,
        progress,
        answer_action,
        severity=severity,
        stage="answer",
        details=details,
    )
    return ProblemStageResult(
        problem_id=problem_id,
        source_problem_id=source_problem_id,
        stage="solution_answer",
        status=stage_status,
        message=message,
    )


def run_content_rule_stage(
    gateway: RightTriangleGateway,
    targets: tuple[ProblemTarget, ...],
    asset_source_target: ProblemTarget,
    profile: GroupProfile,
    reporter: ProgressReporter,
    *,
    run_dir: Path,
    resume: bool,
    apply: bool,
    batch_size: int,
    batch_pause_seconds: float,
    max_workers: int,
) -> tuple[ProblemStageResult, ...]:
    """Run the sine rule through frozen records and old-pipeline progress."""

    if profile.content_rule_key not in {
        "right-triangle-sine",
        "right-triangle-cosine-hypotenuse",
        "right-triangle-tangent-hypotenuse",
        "right-triangle-tangent-opposite-cathetus",
        "right-triangle-universal",
        "right-triangle-altitude-universal",
        "right-triangle-leg-hypotenuse-area",
        "right-triangle-area-leg-difference",
        "right-triangle-acute-angle-difference",
        "right-triangle-acute-angle-ratio",
        "right-triangle-median-angle",
        "right-triangle-bisector-intersection-angle",
        "right-triangle-altitude-bisector-angle",
        "right-triangle-altitude-bisector-inverse",
        "right-triangle-altitude-line-angle",
        "right-triangle-altitude-median-inverse",
        "right-triangle-bisector-median-angle",
        "right-triangle-bisector-median-inverse",
        "right-triangle-altitude-length",
        "right-triangle-hypotenuse-projection-ah",
        "right-triangle-hypotenuse-projection-bh",
        "isosceles-triangle-27284-base-from-sine",
        "isosceles-triangle-27285-side-from-base-sine",
        "isosceles-triangle-27286-base-from-cosine",
        "isosceles-triangle-27287-side-from-base-cosine",
        "isosceles-triangle-27288-base-from-tangent",
        "isosceles-triangle-27289-side-from-base-tangent",
        "isosceles-triangle-27320-altitude-from-base-sine",
        "isosceles-triangle-27321-projection-from-base-sine",
        "isosceles-triangle-27322-altitude-from-base-cosine",
        "isosceles-triangle-27323-projection-from-base-cosine",
        "isosceles-triangle-27324-altitude-from-base-tangent",
        "isosceles-triangle-27325-projection-from-base-tangent",
        "isosceles-triangle-27326-altitude-from-side-sine",
        "isosceles-triangle-27327-projection-from-side-sine",
        "isosceles-triangle-27328-altitude-from-side-cosine",
        "isosceles-triangle-27329-projection-from-side-cosine",
        "isosceles-triangle-27330-sine-from-altitude-and-base",
        "isosceles-triangle-27331-cosine-from-altitude-and-base",
        "isosceles-triangle-27345-obtuse-sine-from-side-and-altitude",
        "isosceles-triangle-27346-obtuse-cosine-from-side-and-altitude",
        "isosceles-triangle-27347-obtuse-tangent-from-side-and-altitude",
        "isosceles-triangle-27349-obtuse-cosine-from-side-and-projection",
        "isosceles-triangle-27350-obtuse-tangent-from-side-and-projection",
        "isosceles-triangle-27351-obtuse-sine-from-altitude-and-projection",
        "isosceles-triangle-27352-obtuse-cosine-from-altitude-and-projection",
        "isosceles-triangle-27353-obtuse-tangent-from-altitude-and-projection",
        "isosceles-triangle-27589-area-from-side-and-30-degree-vertex-angle",
        "isosceles-triangle-27590-area-from-side-and-150-degree-vertex-angle",
        "isosceles-triangle-27619-area-from-side-and-base",
        "isosceles-triangle-27620-side-from-area-and-30-degree-vertex-angle",
        "isosceles-triangle-27621-side-from-area-and-150-degree-vertex-angle",
        "isosceles-triangle-27744-vertex-angle-from-base-angle",
        "isosceles-triangle-27745-base-angle-from-vertex-angle",
        "isosceles-triangle-27746-exterior-angle-from-vertex-angle",
        "isosceles-triangle-27747-vertex-angle-from-exterior-base-angle",
        "isosceles-triangle-27748-base-angle-from-exterior-vertex-angle",
        "isosceles-triangle-27750-smaller-angle-from-larger-angle",
        "isosceles-triangle-27754-smaller-angle-from-angle-difference",
        "isosceles-triangle-27760-vertex-angle-from-altitude-angle",
        "isosceles-triangle-27792-equilateral-height-from-side",
        "isosceles-triangle-27793-equilateral-side-from-height",
        "isosceles-triangle-27794-vertex-angle-from-base-altitude",
        "isosceles-triangle-27795-altitude-from-side-vertex-angle",
        "isosceles-triangle-27796-angle-from-side-altitude",
        "isosceles-triangle-27797-side-from-altitude-vertex-angle",
        "isosceles-triangle-27798-obtuse-altitude-from-side-angle",
        "isosceles-triangle-27799-side-from-base-vertex-angle",
        "isosceles-triangle-27800-base-from-side-vertex-angle",
        "isosceles-triangle-628232-base-from-side-tangent",
        "isosceles-triangle-676342-base-angle-from-exterior-angle",
        "isosceles-triangle-701874-base-angle-from-apex-exterior-angle",
    }:
        raise RightTrianglePlanError("unsupported content rule")
    if not targets:
        return ()
    manifest_path = run_dir / "prepared-manifest.json"
    if resume:
        manifest = _read_content_rule_manifest(manifest_path, targets, profile)
    else:
        source_context = gateway.get_problem_context(asset_source_target.problem_id)
        parent_asset_id = _condition_asset_id(source_context)
        parent_solution_assets = _solution_assets(source_context)
        manifest = _content_rule_manifest(
            gateway,
            targets,
            profile=profile,
            parent_asset_id=parent_asset_id,
            parent_solution_assets=parent_solution_assets,
            max_workers=max_workers,
        )
        _write_checkpoint(manifest_path, manifest)
    records = manifest["records"]
    if apply:
        summary = apply_frozen_manifest(
            gateway,
            manifest,
            batch_size=batch_size,
            max_workers=max_workers,
            checkpoint_path=run_dir / "apply-results.json",
            batch_pause_seconds=batch_pause_seconds,
        )
        raw_results = summary["results"]
    else:
        raw_results = [
            {
                "problem_id": record.get("problem_id"),
                "source_problem_id": record.get("source_problem_id"),
                "status": (
                    "planned" if record.get("status") == "prepared" else "failed"
                ),
                "message": record.get("message"),
            }
            for record in records
        ]
    total = len(raw_results)
    return tuple(
        _report_content_result(
            reporter,
            profile,
            result,
            TargetProgress(index=index, total=total),
        )
        for index, result in enumerate(raw_results, start=1)
    )


def run_manifest(
    gateway: RightTriangleGateway,
    manifest: dict[str, Any],
    *,
    apply: bool,
) -> dict[str, Any]:
    """Discover, repair, verify, and optionally mark ready one manifest group."""

    source_group_id = str(manifest.get("source_group_id") or "")
    parent_asset_id = str(
        (manifest.get("condition_asset") or {}).get("source_asset_id") or ""
    )
    content_rule_key = manifest.get("content_rule_key")
    if content_rule_key is not None and not isinstance(content_rule_key, str):
        raise RightTrianglePlanError("manifest content rule is invalid")
    _planner_constraints(content_rule_key)
    raw_solution_assets = manifest.get("solution_assets", [])
    if not isinstance(raw_solution_assets, list) or not all(
        isinstance(item, dict) for item in raw_solution_assets
    ):
        raise RightTrianglePlanError("manifest solution assets are invalid")
    parent_solution_assets = tuple(deepcopy(item) for item in raw_solution_assets)
    selection = manifest.get("selection") or {}
    skipped = {str(value) for value in selection.get("skip_source_problem_ids", [])}
    if not source_group_id or not parent_asset_id:
        raise RightTrianglePlanError("manifest requires source_group_id and parent asset")
    results: list[dict[str, Any]] = []
    verified_ids: list[str] = []
    for child in _children(gateway.get_source_catalog_children(source_group_id, "group")):
        problem_id, source_problem_id = _problem_identity(child)
        if source_problem_id in skipped:
            results.append(
                {
                    "source_problem_id": source_problem_id,
                    "problem_id": problem_id,
                    "status": "skipped",
                    "transformations": [],
                }
            )
            continue
        try:
            context = gateway.get_problem_context(problem_id)
            plan = _build_content_plan(
                context,
                parent_asset_id=parent_asset_id,
                content_rule_key=content_rule_key,
                parent_solution_assets=parent_solution_assets,
            )
            targets = [item["transformation_target_id"] for item in plan.transformations]
            if not apply:
                results.append(
                    {
                        "source_problem_id": source_problem_id,
                        "problem_id": problem_id,
                        "status": "planned",
                        "transformations": targets,
                    }
                )
                continue
            if plan.transformations:
                if "asset:image_1" in targets:
                    gateway.get_problem_asset_target_context(problem_id, "asset:image_1")
                gateway.apply_problem_transformations(problem_id, list(plan.transformations))
            readback = gateway.get_problem_context(problem_id)
            if _build_content_plan(
                readback,
                parent_asset_id=parent_asset_id,
                content_rule_key=content_rule_key,
                parent_solution_assets=parent_solution_assets,
            ).transformations:
                raise RightTrianglePlanError("post-write content readback is incomplete")
            verified_ids.append(problem_id)
            results.append(
                {
                    "source_problem_id": source_problem_id,
                    "problem_id": problem_id,
                    "status": "applied" if plan.transformations else "already_complete",
                    "transformations": targets,
                }
            )
        except Exception as exc:  # noqa: BLE001 - retain one failure per task.
            results.append(
                {
                    "source_problem_id": source_problem_id,
                    "problem_id": problem_id,
                    "status": "failed",
                    "transformations": [],
                    "message": " ".join(str(exc).split())[:500],
                }
            )
    if apply:
        for result in results:
            if result["problem_id"] not in verified_ids:
                continue
            try:
                _helpers_update(gateway, result["problem_id"])
                result["helpers"] = "ready"
            except Exception as exc:  # noqa: BLE001 - content remains verified if state fails.
                result["helpers"] = "failed"
                result["helpers_message"] = " ".join(str(exc).split())[:500]
    return {
        "planned_count": sum(item["status"] == "planned" for item in results),
        "applied_count": sum(item["status"] == "applied" for item in results),
        "already_complete_count": sum(item["status"] == "already_complete" for item in results),
        "failed_count": sum(item["status"] == "failed" for item in results),
        "results": results,
    }
