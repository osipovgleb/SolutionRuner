"""Verify one isolated solution/answer runtime over frozen prepared assets."""

from __future__ import annotations

from copy import deepcopy
import hashlib
from io import StringIO
from pathlib import Path
import threading
from typing import Any

from bs4 import BeautifulSoup
import pytest

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.models import PreparedGridPolygon
from solution_runner.pipelines.grid_polygon.progress import ProgressReporter
from solution_runner.pipelines.grid_polygon.solution_runtime import run_solution_stage
from solution_runner.pipelines.grid_polygon.strategies import get_solution_strategy


def _prepared(tmp_path: Path, source_problem_id: str, *, valid: bool = True) -> PreparedGridPolygon:
    """Create one prepared right triangle without any runtime discovery."""

    coordinates = ((1, 2), (7, 2), (1, 6)) if valid else ((1, 1), (4, 2), (2, 5))
    path = tmp_path / f"{source_problem_id}.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 160">'
        '<polygon points="20,40 140,40 20,120" fill="#8da3cc" stroke="#111"/>'
        '</svg>'
    )
    return PreparedGridPolygon(
        problem_id=f"problem-{source_problem_id}",
        source_problem_id=source_problem_id,
        condition_asset_id="condition",
        condition_svg_path=path,
        condition_svg_sha256="condition-sha",
        coordinates=coordinates,
        vertex_count=3,
        condition_was_replaced=True,
        converter_diagnostics={},
    )


def _rhombus_prepared(tmp_path: Path, source_problem_id: str) -> PreparedGridPolygon:
    """Create one prepared rhombus for the two-method solution profile."""

    path = tmp_path / f"{source_problem_id}.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 140">'
        '<polygon points="80,120 20,80 80,40 140,80" fill="#8da3cc" stroke="#111"/>'
        "</svg>"
    )
    return PreparedGridPolygon(
        problem_id=f"problem-{source_problem_id}",
        source_problem_id=source_problem_id,
        condition_asset_id="condition",
        condition_svg_path=path,
        condition_svg_sha256="condition-sha",
        coordinates=((4, 5), (1, 3), (4, 1), (7, 3)),
        vertex_count=4,
        condition_was_replaced=True,
        converter_diagnostics={},
    )


def _parallelogram_prepared(
    tmp_path: Path,
    source_problem_id: str,
) -> PreparedGridPolygon:
    """Create the audited group-348499 parent parallelogram."""

    path = tmp_path / f"{source_problem_id}.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 120">'
        '<polygon points="20,80 80,20 200,20 140,80" '
        'fill="#8da3cc" stroke="#111"/>'
        "</svg>"
    )
    return PreparedGridPolygon(
        problem_id=f"problem-{source_problem_id}",
        source_problem_id=source_problem_id,
        condition_asset_id="condition",
        condition_svg_path=path,
        condition_svg_sha256="condition-sha",
        coordinates=((1, 4), (4, 1), (10, 1), (7, 4)),
        vertex_count=4,
        condition_was_replaced=False,
        converter_diagnostics={},
    )


class RecordingGateway:
    """Apply transformations to in-memory normalized content with failure hooks."""

    def __init__(self, source_problem_ids: tuple[str, ...]) -> None:
        """Create empty schema-v3 content for every target."""

        self.content = {
            f"problem-{source_id}": {
                "format": "teacherhelper-normalized",
                "schema_version": 3,
                "sections": [],
                "assets": [],
            }
            for source_id in source_problem_ids
        }
        self.upload_calls: list[str] = []
        self.apply_calls: list[str] = []
        self.applied_transformations: dict[str, list[dict[str, Any]]] = {}
        self.context_read_calls: list[str] = []
        self.condition_download_calls: list[str] = []
        self.fail_apply_for: set[str] = set()
        self.ambiguous_apply_for: set[str] = set()
        self.canonicalize_solution_for: set[str] = set()
        self.reject_generated_asset_rewrite_for: set[str] = set()
        self.silently_ignore_answer_for: set[str] = set()
        self.asset_targets: dict[tuple[str, str], str] = {}
        self.asset_metadata: dict[str, dict[str, Any]] = {}

    def get_problem_context(self, problem_id: str) -> dict[str, Any]:
        """Return authoritative normalized content readback."""

        self.context_read_calls.append(problem_id)
        return {"problem_id": problem_id, "normalized_content": deepcopy(self.content[problem_id])}

    def upload_solution_asset(
        self,
        *,
        source_problem_id: str,
        svg_bytes: bytes,
        sha256: str,
    ) -> dict[str, str]:
        """Return one deterministic fake SourceAsset contract."""

        self.upload_calls.append(source_problem_id)
        suffix = "" if self.upload_calls.count(source_problem_id) == 1 else "-2"
        return {
            "source_asset_id": f"solution-{source_problem_id}{suffix}",
            "url": f"/assets/solution-{source_problem_id}{suffix}",
            "sha256": sha256,
        }

    def get_asset_metadata(self, asset_id: str) -> dict[str, Any]:
        """Return authoritative fake asset metadata."""

        return deepcopy(self.asset_metadata[asset_id])

    def apply_problem_transformations(
        self,
        problem_id: str,
        transformations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Apply normalized section/asset transformations in memory."""

        self.apply_calls.append(problem_id)
        self.applied_transformations[problem_id] = deepcopy(transformations)
        if problem_id in self.fail_apply_for:
            raise RuntimeError("fake apply failure")
        content = self.content[problem_id]
        for transformation in transformations:
            target = transformation["transformation_target_id"]
            if transformation["operation"] == "remove":
                if target.startswith("asset:"):
                    key = target.split(":", 1)[1]
                    content["assets"] = [
                        item for item in content["assets"] if item["asset_key"] != key
                    ]
                    self.asset_targets.pop((problem_id, target), None)
                continue
            value = deepcopy(transformation["value"])
            if target.startswith("section:"):
                key = target.split(":")[1]
                if key == "answer" and problem_id in self.silently_ignore_answer_for:
                    continue
                if key == "solution" and problem_id in self.canonicalize_solution_for:
                    expected = (
                        '<center><img src="/assets/solution-5089" '
                        'alt="[(1, 2), (7, 2), (1, 6)]" '
                        'data-asset-id="solution-5089" '
                        'data-asset-key="generated_solution_diagram" '
                        'data-transformation-target-id="asset:generated_solution_diagram">'
                        "</center>"
                    )
                    canonical = (
                        '<center><img alt="[(1, 2), (7, 2), (1, 6)]" '
                        'data-asset-id="solution-5089" '
                        'data-asset-key="generated_solution_diagram" '
                        'data-transformation-target-id="asset:generated_solution_diagram" '
                        'src="/assets/solution-5089"/></center>'
                    )
                    value["html"] = str(value["html"]).replace(expected, canonical)
                content["sections"] = [item for item in content["sections"] if item["key"] != key]
                content["sections"].append({"key": key, **value})
            elif target.startswith("asset:"):
                if (
                    problem_id in self.reject_generated_asset_rewrite_for
                    and transformation["operation"] == "rewrite"
                ):
                    raise RuntimeError(
                        "generated asset added by a transformation cannot become a base rewrite"
                    )
                key = value["asset_key"]
                content["assets"] = [item for item in content["assets"] if item["asset_key"] != key]
                content["assets"].append(value)
                self.asset_targets[(problem_id, target)] = value["asset_id"]
        if problem_id in self.ambiguous_apply_for:
            raise RuntimeError("fake response lost after commit")
        return {"results": [{"problem_id": problem_id}]}

    def get_problem_asset_target_context(
        self,
        problem_id: str,
        transformation_target_id: str,
    ) -> dict[str, Any]:
        """Return the current generated asset identity."""

        return {
            "current_asset_id": self.asset_targets.get((problem_id, transformation_target_id))
        }


def _reporter() -> tuple[ProgressReporter, StringIO]:
    """Return a no-color reporter and its console sink."""

    console = StringIO()
    return ProgressReporter(console=console, internal=StringIO(), color=False), console


def test_solution_runtime_never_downloads_or_converts_condition_asset(tmp_path: Path) -> None:
    """Consume prepared records only and never repeat image preparation."""

    gateway = RecordingGateway(("5089",))
    reporter, console = _reporter()
    results = run_solution_stage(
        gateway,
        (_prepared(tmp_path, "5089"),),
        get_group_profile("27543"),
        get_solution_strategy("right-triangle"),
        reporter,
        apply=True,
    )

    assert results[0].status == "applied"
    assert gateway.condition_download_calls == []
    assert gateway.upload_calls == []
    assert "[1/1]  SOLUTION WRITTEN" in console.getvalue()
    assert "[1/1]  ANSWER VERIFIED" in console.getvalue()


def test_existing_solution_is_preserved_while_answer_is_repaired(tmp_path: Path) -> None:
    """Keep real reference prose under preserve policy and audit its answer."""

    gateway = RecordingGateway(("5089",))
    gateway.content["problem-5089"]["sections"] = [
        {"key": "solution", "title": "Решение", "html": "<p>Эталонный текст</p>"},
        {"key": "answer", "title": "Ответ", "html": "<p>13</p>"},
    ]
    reporter, _ = _reporter()
    result = run_solution_stage(
        gateway,
        (_prepared(tmp_path, "5089"),),
        get_group_profile("27543"),
        get_solution_strategy("right-triangle"),
        reporter,
        apply=True,
    )[0]

    sections = {item["key"]: item for item in gateway.content["problem-5089"]["sections"]}
    assert result.status == "applied"
    assert sections["solution"]["html"] == "<p>Эталонный текст</p>"
    assert sections["answer"]["html"] == '<p><span data-effect="spaced">12</span></p>'
    assert "answer_mismatch_before_write" in (result.message or "")


@pytest.mark.parametrize(
    ("group_key", "source_problem_id", "expected_diagrams"),
    (("27553", "27553", 1), ("27554", "27554", 2)),
)
def test_two_method_rewrite_places_diagram_inside_first_solution(
    tmp_path: Path,
    group_key: str,
    source_problem_id: str,
    expected_diagrams: int,
) -> None:
    """Keep the generated diagram visible in the first method without a legacy tail."""

    gateway = RecordingGateway((source_problem_id,))
    problem_id = f"problem-{source_problem_id}"
    gateway.content[problem_id]["sections"] = [
        {
            "key": "solution",
            "title": "Решение",
            "html": (
                '<section data-content-kind="solution" data-solution-title="Решение">'
                '<p><img data-asset-key="image_2" src="/assets/legacy-outline"/>'
                "Старое решение</p></section>"
            ),
            "asset_keys": ["image_2"],
        },
        {"key": "answer", "title": "Ответ", "html": "<p>12</p>", "asset_keys": []},
    ]
    gateway.content[problem_id]["assets"] = [
        {
            "asset_key": "image_2",
            "asset_id": "legacy-outline",
            "url": "/assets/legacy-outline",
        }
    ]
    reporter, _ = _reporter()

    result = run_solution_stage(
        gateway,
        (_rhombus_prepared(tmp_path, source_problem_id),),
        get_group_profile(group_key),
        get_solution_strategy("bounding-rectangle-quadrilateral"),
        reporter,
        apply=True,
    )[0]

    solution = next(
        section
        for section in gateway.content[problem_id]["sections"]
        if section["key"] == "solution"
    )
    wrappers = BeautifulSoup(solution["html"], "html.parser").select(
        'section[data-content-kind="solution"]'
    )
    assert result.status == "applied"
    assert len(wrappers) == 2
    assert wrappers[0].select_one(
        'img[data-asset-key="generated_solution_diagram"]'
    ) is not None
    first_child = next(
        child for child in wrappers[0].children if getattr(child, "name", None)
    )
    assert first_child.name == "center"
    assert wrappers[1].select_one(
        'img[data-asset-key="generated_solution_diagram"]'
    ) is None
    pick = wrappers[1].select_one('img[data-asset-key="generated_pick_diagram"]')
    assert (pick is not None) == (group_key == "27554")
    assert wrappers[0].select_one('img[data-asset-key="generated_pick_diagram"]') is None
    assert len(
        BeautifulSoup(solution["html"], "html.parser").select(
            'img[data-asset-key="generated_solution_diagram"]'
        )
    ) == 1
    assert solution["asset_keys"] == (
        ["generated_solution_diagram", "generated_pick_diagram"]
        if group_key == "27554"
        else ["generated_solution_diagram"]
    )
    assert len(gateway.upload_calls) == expected_diagrams
    assert all(
        asset["asset_key"] != "image_2"
        for asset in gateway.content[problem_id]["assets"]
    )


def test_parallelogram_runtime_places_all_three_diagrams_in_matching_methods(
    tmp_path: Path,
) -> None:
    """Catch lost, duplicated, or reordered diagrams at the transformation boundary."""

    gateway = RecordingGateway(("401034",))
    reporter, _ = _reporter()
    profile = get_group_profile("348499")

    result = run_solution_stage(
        gateway,
        (_parallelogram_prepared(tmp_path, "401034"),),
        profile,
        get_solution_strategy(profile.strategy_key),
        reporter,
        apply=True,
    )[0]

    solution = next(
        section
        for section in gateway.content["problem-401034"]["sections"]
        if section["key"] == "solution"
    )
    wrappers = BeautifulSoup(solution["html"], "html.parser").select(
        'section[data-content-kind="solution"]'
    )
    expected_keys = (
        "generated_solution_diagram",
        "generated_rectangle_diagram",
        "generated_pick_diagram",
    )

    assert result.status == "applied"
    assert len(wrappers) == 3
    assert len(gateway.upload_calls) == 3
    assert solution["asset_keys"] == list(expected_keys)
    for index, asset_key in enumerate(expected_keys):
        assert wrappers[index].select_one(
            f'img[data-asset-key="{asset_key}"]'
        ) is not None
        assert sum(
            wrapper.select_one(f'img[data-asset-key="{asset_key}"]') is not None
            for wrapper in wrappers
        ) == 1


def test_matching_solution_and_answer_are_not_rewritten(tmp_path: Path) -> None:
    """Skip upload and transformation when authoritative content is already exact."""

    gateway = RecordingGateway(("5089",))
    prepared = _prepared(tmp_path, "5089")
    profile = get_group_profile("27543")
    strategy = get_solution_strategy("right-triangle")
    analysis = strategy.analyze(prepared, profile)
    gateway.content["problem-5089"]["sections"] = [
        {
            "key": "solution",
            "title": "Решение",
            "html": strategy.build_solution_html(analysis, profile),
            "asset_keys": [],
        },
        {
            "key": "answer",
            "title": "Ответ",
            "html": strategy.build_answer_html(analysis),
            "asset_keys": [],
        },
    ]
    reporter, console = _reporter()

    result = run_solution_stage(
        gateway,
        (prepared,),
        profile,
        strategy,
        reporter,
        apply=True,
    )[0]

    assert result.status == "already_complete"
    assert gateway.upload_calls == []
    assert gateway.apply_calls == []
    assert "SOLUTION ALREADY COMPLETE" in console.getvalue()
    assert "ANSWER VERIFIED" in console.getvalue()


def test_one_failed_target_does_not_block_next_and_never_reaches_helpers(tmp_path: Path) -> None:
    """Return an isolated failure and continue with the next frozen position."""

    gateway = RecordingGateway(("bad", "good"))
    gateway.fail_apply_for.add("problem-bad")
    reporter, console = _reporter()
    results = run_solution_stage(
        gateway,
        (_prepared(tmp_path, "bad"), _prepared(tmp_path, "good")),
        get_group_profile("27543"),
        get_solution_strategy("right-triangle"),
        reporter,
        apply=True,
    )

    assert [result.status for result in results] == ["failed", "applied"]
    assert results[0].stage == "solution"
    assert "[1/2]  SOLUTION FAILED" in console.getvalue()
    assert "[2/2]  ANSWER VERIFIED" in console.getvalue()


def test_solution_workers_overlap_targets_but_return_frozen_order(tmp_path: Path) -> None:
    """Run independent targets concurrently without reordering stage results."""

    delegate = get_solution_strategy("right-triangle")
    barrier = threading.Barrier(2)

    class ConcurrentStrategy:
        """Pause both analyses until two worker threads have entered."""

        def __getattr__(self, name: str) -> Any:
            """Delegate the unchanged pure strategy contract."""

            return getattr(delegate, name)

        def analyze(self, target: PreparedGridPolygon, profile: Any) -> Any:
            """Require two targets to overlap before delegating analysis."""

            barrier.wait(timeout=1.0)
            return delegate.analyze(target, profile)

    gateway = RecordingGateway(("first", "second"))
    reporter, _ = _reporter()

    results = run_solution_stage(
        gateway,
        (_prepared(tmp_path, "first"), _prepared(tmp_path, "second")),
        get_group_profile("27543"),
        ConcurrentStrategy(),
        reporter,
        apply=False,
        max_workers=2,
    )

    assert [result.source_problem_id for result in results] == ["first", "second"]
    assert [result.status for result in results] == ["planned", "planned"]


def test_ambiguous_transformation_response_is_a_target_failure(tmp_path: Path) -> None:
    """Require an explicit successful MCP response instead of guessing by HTML."""

    gateway = RecordingGateway(("5089",))
    gateway.ambiguous_apply_for.add("problem-5089")
    reporter, _ = _reporter()

    result = run_solution_stage(
        gateway,
        (_prepared(tmp_path, "5089"),),
        get_group_profile("27543"),
        get_solution_strategy("right-triangle"),
        reporter,
        apply=True,
    )[0]

    assert result.status == "failed"


def test_successful_write_accepts_semantically_equal_html_readback(tmp_path: Path) -> None:
    """Accept parser-level HTML canonicalization during authoritative readback."""

    gateway = RecordingGateway(("5089",))
    gateway.canonicalize_solution_for.add("problem-5089")
    reporter, _ = _reporter()

    result = run_solution_stage(
        gateway,
        (_prepared(tmp_path, "5089"),),
        get_group_profile("27548"),
        get_solution_strategy("bounding-rectangle-triangle"),
        reporter,
        apply=True,
    )[0]

    assert result.status == "applied"
    assert gateway.context_read_calls == ["problem-5089", "problem-5089"]


def test_existing_sections_use_their_exact_transformation_targets(tmp_path: Path) -> None:
    """Rewrite exact section instances instead of stale section-key aliases."""

    gateway = RecordingGateway(("5089",))
    gateway.content["problem-5089"]["sections"] = [
        {
            "key": "solution",
            "section_id": "solution:1",
            "transformation_target_id": "section:solution:1",
            "title": "Решение",
            "html": "<p>Старое решение</p>",
        },
        {
            "key": "answer",
            "section_id": "answer:1",
            "transformation_target_id": "section:answer:1",
            "title": "Ответ",
            "html": "<p>13</p>",
        },
    ]
    reporter, _ = _reporter()

    result = run_solution_stage(
        gateway,
        (_prepared(tmp_path, "5089"),),
        get_group_profile("27543"),
        get_solution_strategy("right-triangle"),
        reporter,
        apply=True,
    )[0]

    targets = {
        item["transformation_target_id"]
        for item in gateway.applied_transformations["problem-5089"]
        if item["transformation_target_id"].startswith("section:")
    }
    assert result.status == "applied"
    assert targets == {"section:solution:1", "section:answer:1"}


def test_successful_write_requires_answer_readback_match(tmp_path: Path) -> None:
    """Fail one target when the server accepts but does not materialize its answer."""

    gateway = RecordingGateway(("5089",))
    gateway.content["problem-5089"]["sections"] = [
        {"key": "answer", "title": "Ответ", "html": "<p>13</p>"},
    ]
    gateway.silently_ignore_answer_for.add("problem-5089")
    reporter, console = _reporter()

    result = run_solution_stage(
        gateway,
        (_prepared(tmp_path, "5089"),),
        get_group_profile("27543"),
        get_solution_strategy("right-triangle"),
        reporter,
        apply=True,
    )[0]

    assert result.status == "failed"
    assert result.stage == "answer"
    assert "ANSWER FAILED" in console.getvalue()


def test_existing_solution_asset_is_reused_via_authoritative_metadata(tmp_path: Path) -> None:
    """Avoid another upload when normalized content omits an asset digest."""

    gateway = RecordingGateway(("5089",))
    prepared = _prepared(tmp_path, "5089")
    profile = get_group_profile("27548")
    strategy = get_solution_strategy("bounding-rectangle-triangle")
    analysis = strategy.analyze(prepared, profile)
    digest = hashlib.sha256(strategy.render_solution_svg(prepared, analysis)).hexdigest()
    gateway.content["problem-5089"]["assets"] = [
        {
            "asset_key": "generated_solution_diagram",
            "asset_id": "existing-solution-5089",
            "url": "/assets/existing-solution-5089",
        }
    ]
    gateway.asset_metadata["existing-solution-5089"] = {
        "asset_id": "existing-solution-5089",
        "content_type": "image/svg+xml",
        "sha256": digest,
        "url": "/assets/existing-solution-5089",
    }
    reporter, _ = _reporter()

    result = run_solution_stage(
        gateway,
        (prepared,),
        profile,
        strategy,
        reporter,
        apply=True,
    )[0]

    assert result.status == "applied"
    assert gateway.upload_calls == []


def test_existing_transformation_added_asset_preserves_add_operation(
    tmp_path: Path,
) -> None:
    """Update a generated asset without rewriting a nonexistent Parsed base asset."""

    gateway = RecordingGateway(("5089",))
    gateway.reject_generated_asset_rewrite_for.add("problem-5089")
    gateway.content["problem-5089"]["assets"] = [
        {
            "asset_key": "generated_solution_diagram",
            "asset_id": "old-solution-5089",
            "url": "/assets/old-solution-5089",
        }
    ]
    gateway.asset_metadata["old-solution-5089"] = {
        "asset_id": "old-solution-5089",
        "content_type": "image/svg+xml",
        "sha256": "0" * 64,
        "url": "/assets/old-solution-5089",
    }
    reporter, _ = _reporter()

    result = run_solution_stage(
        gateway,
        (_prepared(tmp_path, "5089"),),
        get_group_profile("27548"),
        get_solution_strategy("bounding-rectangle-triangle"),
        reporter,
        apply=True,
    )[0]

    assert result.status == "applied"


def test_geometry_failure_skips_upload_solution_answer_and_status(tmp_path: Path) -> None:
    """Stop all downstream work when prepared coordinates fail strategy checks."""

    gateway = RecordingGateway(("bad",))
    reporter, _ = _reporter()
    result = run_solution_stage(
        gateway,
        (_prepared(tmp_path, "bad", valid=False),),
        get_group_profile("27543"),
        get_solution_strategy("right-triangle"),
        reporter,
        apply=True,
    )[0]

    assert result.status == "failed"
    assert gateway.upload_calls == []
    assert gateway.apply_calls == []


def test_preview_builds_plan_without_upload_or_write(tmp_path: Path) -> None:
    """Keep preview entirely local while returning a planned terminal result."""

    gateway = RecordingGateway(("5089",))
    reporter, _ = _reporter()
    result = run_solution_stage(
        gateway,
        (_prepared(tmp_path, "5089"),),
        get_group_profile("27543"),
        get_solution_strategy("right-triangle"),
        reporter,
        apply=False,
    )[0]

    assert result.status == "planned"
    assert gateway.upload_calls == []
    assert gateway.apply_calls == []
