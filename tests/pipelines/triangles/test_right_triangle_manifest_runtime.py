"""Protect frozen manifest preparation, batched application, and resume behavior."""

from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
from pathlib import Path

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.models import ProblemTarget
from solution_runner.pipelines.grid_polygon.progress import ProgressReporter
from solution_runner.pipelines.triangles.right.runtime import (
    apply_frozen_manifest,
    prepare_manifest,
    run_content_rule_stage,
)


CATALOG_ID = "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
GROUP_ID = "8b5a2cb7-4831-4355-9d47-e473b8aef65c"
PARENT_ASSET_ID = "8f8988bb-fa85-47a8-be0e-75edaf5a7604"


def _context(
    problem_id: str,
    source_problem_id: str,
    *,
    answer: str,
    with_solution: bool,
    asset_id: str | None,
) -> dict:
    """Return one complete materialized transformation-context fixture."""

    sections = [
        {
            "key": "condition",
            "section_id": "condition:1",
            "html": (
                '<p>В треугольнике ABC угол C равен 90°, '
                '<span data-inline-latex="\\sin A=\\frac{3}{5}"></span>, '
                '<span data-inline-latex="AC=4"></span>. Найдите AB.</p>'
            ),
        },
        {
            "key": "answer",
            "section_id": "answer:1",
            "html": f'<p><span data-effect="spaced">{answer}</span></p>',
        },
    ]
    if with_solution:
        sections.append(
            {
                "key": "solution",
                "section_id": "solution:1",
                "html": "<p>Проверенное решение.</p>",
            }
        )
    assets = []
    if asset_id:
        assets.append(
            {
                "asset_key": "image_1",
                "asset_id": asset_id,
                "url": f"/assets/{asset_id}",
                "kind": "ordinary_image",
                "alt": "",
            }
        )
    return {
        "problem_id": problem_id,
        "source_problem_id": source_problem_id,
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "sections": sections,
            "assets": assets,
        },
    }


class _PreparationGateway:
    """Supply real-shaped source navigation and transformation-context reads."""

    def __init__(self) -> None:
        """Create a parent and one repair candidate in stable source order."""

        self.contexts = {
            "parent-problem": _context(
                "parent-problem",
                "27238",
                answer="5",
                with_solution=True,
                asset_id=PARENT_ASSET_ID,
            ),
            "child-problem": _context(
                "child-problem",
                "4583",
                answer="7",
                with_solution=False,
                asset_id=None,
            ),
        }

    def find_source_catalog_path(
        self, catalog_snapshot_id: str, source_id: str, target_type: str
    ) -> dict:
        """Resolve the visible group number to its stable internal UUID."""

        assert (catalog_snapshot_id, source_id, target_type) == (
            CATALOG_ID,
            "27238",
            "group",
        )
        return {
            "matches": [
                {
                    "catalog": {"uuid": CATALOG_ID, "name": "Каталог"},
                    "category": {"uuid": "category-uuid", "name": "Категория"},
                    "theme": {"uuid": "theme-uuid", "name": "Тема"},
                    "group": {"uuid": GROUP_ID, "name": "Группа 27238"},
                }
            ]
        }

    def get_source_catalog_children(self, parent_id: str, parent_type: str) -> dict:
        """Return both group tasks in deterministic order."""

        assert (parent_id, parent_type) == (GROUP_ID, "group")
        return {
            "items": [
                {"uuid": "parent-problem", "name": "Задача 27238"},
                {"uuid": "child-problem", "name": "Задача 4583"},
            ]
        }

    def get_problem_context(self, problem_id: str) -> dict:
        """Return an isolated copy of one materialized context."""

        return deepcopy(self.contexts[problem_id])


def test_prepare_manifest_resolves_group_and_freezes_computed_repairs() -> None:
    """Catch a manifest that retains only group metadata and recomputes during apply."""

    manifest = prepare_manifest(
        _PreparationGateway(),
        catalog_snapshot_id=CATALOG_ID,
        source_group_number="27238",
        max_workers=2,
    )

    assert manifest["source_group_id"] == GROUP_ID
    assert manifest["group_key"] == "27238"
    assert manifest["condition_asset"]["source_asset_id"] == PARENT_ASSET_ID
    assert [record["source_problem_id"] for record in manifest["records"]] == [
        "27238",
        "4583",
    ]
    child = manifest["records"][1]
    assert child["expected_answer"] == "5"
    assert [item["transformation_target_id"] for item in child["transformations"]] == [
        "asset:image_1",
        "section:solution",
        "section:answer:1",
    ]


def test_prepare_manifest_uses_first_problem_only_as_the_asset_source() -> None:
    """Keep solution selection independent from a group-level prototype."""

    manifest = prepare_manifest(
        _PreparationGateway(),
        catalog_snapshot_id=CATALOG_ID,
        source_group_number="27238",
        max_workers=2,
    )

    assert manifest["condition_asset"]["source_problem_id"] == "27238"
    assert "prototype_source_problem_id" not in manifest
    assert "prototype_problem_id" not in manifest


class _ApplyGateway(_PreparationGateway):
    """Materialize frozen transformations and record Helpers readback."""

    def __init__(self) -> None:
        """Track content writes and Helpers completion independently."""

        super().__init__()
        self.content_writes: list[str] = []
        self.helpers_ready: set[str] = set()

    def find_source_catalog_path(self, *_args: object) -> dict:
        """Prove apply never resolves or rediscovers the source group."""

        raise AssertionError("apply must use frozen records")

    def get_source_catalog_children(self, *_args: object) -> dict:
        """Prove apply never reloads source-group membership."""

        raise AssertionError("apply must use frozen records")

    def get_problem_asset_target_context(
        self, problem_id: str, transformation_target_id: str
    ) -> dict:
        """Return the exact current image target required before replacement."""

        return {
            "problem_id": problem_id,
            "transformation_target_id": transformation_target_id,
        }

    def apply_problem_transformations(
        self, problem_id: str, transformations: list[dict]
    ) -> dict:
        """Apply the frozen values to the fake schema-v3 materialization."""

        self.content_writes.append(problem_id)
        content = self.contexts[problem_id]["normalized_content"]
        for item in transformations:
            target = item["transformation_target_id"]
            value = deepcopy(item["value"])
            if target == "asset:image_1":
                content["assets"] = [
                    {
                        "asset_key": value["asset_key"],
                        "asset_id": value["asset_id"],
                        "url": value["url"],
                        "kind": value["kind"],
                        "alt": value["alt"],
                    }
                ]
            else:
                key = "solution" if target == "section:solution" else "answer"
                content["sections"] = [
                    section for section in content["sections"] if section["key"] != key
                ]
                content["sections"].append(
                    {
                        "key": key,
                        "section_id": f"{key}:1",
                        "html": value["html"],
                    }
                )
        return {"problem_id": problem_id, "applied_count": len(transformations)}

    def get_problem_pipeline_state(self, problem_id: str) -> dict:
        """Return one fresh concurrency token per verified task."""

        return {
            "problem_id": problem_id,
            "stage_state_tokens": {"helpers": f"helpers-{problem_id}"},
        }

    def set_problem_pipeline_stage_state_batch(
        self, stage: str, updates: list[dict], reason: str
    ) -> dict:
        """Materialize the ready aggregate returned by the real setter."""

        assert stage == "helpers"
        assert reason
        problem_id = updates[0]["problem_id"]
        self.helpers_ready.add(problem_id)
        return {
            "stage": "helpers",
            "requested_count": 1,
            "results": [
                {
                    "problem_id": problem_id,
                    "values": {"helpers_status": "ready"},
                }
            ],
        }

    def close(self) -> None:
        """Match the production gateway lifecycle used by the launcher."""


class _CombinedGateway(_ApplyGateway):
    """Allow preparation followed by apply through one gateway lifecycle."""

    find_source_catalog_path = _PreparationGateway.find_source_catalog_path
    get_source_catalog_children = _PreparationGateway.get_source_catalog_children


def test_apply_uses_frozen_records_batches_and_resumes_from_readback(tmp_path: Path) -> None:
    """Catch rediscovery, missing checkpoints, or repeated writes on a resumed run."""

    prepare_gateway = _PreparationGateway()
    manifest = prepare_manifest(
        prepare_gateway,
        catalog_snapshot_id=CATALOG_ID,
        source_group_number="27238",
        max_workers=2,
    )
    gateway = _ApplyGateway()
    checkpoint = tmp_path / "apply-results.json"

    first = apply_frozen_manifest(
        gateway,
        manifest,
        batch_size=1,
        max_workers=2,
        checkpoint_path=checkpoint,
    )
    second = apply_frozen_manifest(
        gateway,
        manifest,
        batch_size=1,
        max_workers=2,
        checkpoint_path=checkpoint,
    )

    assert first["failed_count"] == 0
    assert checkpoint.is_file()
    assert gateway.content_writes == ["child-problem"]
    assert gateway.helpers_ready == set()
    assert second["already_complete_count"] == 2


def test_content_rule_stage_reports_and_continues_after_one_blocked_task(
    tmp_path: Path,
) -> None:
    """Reuse old-pipeline progress while isolating malformed Normalized content."""

    gateway = _CombinedGateway()
    gateway.contexts["blocked-problem"] = {
        "problem_id": "blocked-problem",
        "source_problem_id": "4636",
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 2,
            "sections": [],
            "assets": [],
        },
    }
    targets = tuple(
        ProblemTarget(
            problem_id=problem_id,
            source_problem_id=source_problem_id,
            source_group_id=GROUP_ID,
            group_key="27238",
            problem_order_index=index,
        )
        for index, (problem_id, source_problem_id) in enumerate(
            (
                ("parent-problem", "27238"),
                ("child-problem", "4583"),
                ("blocked-problem", "4636"),
            ),
            start=1,
        )
    )
    console = StringIO()
    internal = StringIO()
    reporter = ProgressReporter(console=console, internal=internal, color=False)

    results = run_content_rule_stage(
        gateway,
        targets,
        targets[0],
        get_group_profile("27238"),
        reporter,
        run_dir=tmp_path,
        resume=False,
        apply=True,
        batch_size=2,
        batch_pause_seconds=0,
        max_workers=2,
    )

    assert [result.status for result in results] == [
        "already_complete",
        "applied",
        "failed",
    ]
    assert gateway.content_writes == ["child-problem"]
    assert gateway.helpers_ready == set()
    assert (tmp_path / "prepared-manifest.json").is_file()
    assert (tmp_path / "apply-results.json").is_file()
    assert "SOLUTION ALREADY COMPLETE" in console.getvalue()
    assert "SOLUTION WRITTEN" in console.getvalue()
    assert "SOLUTION FAILED" in console.getvalue()
    assert '"source_problem_id": "4636"' in internal.getvalue()


def test_group_27243_runtime_freezes_the_strict_tangent_bc_solution(
    tmp_path: Path,
) -> None:
    """Route group 27243 through its definition-first parent HTML planner."""

    gateway = _CombinedGateway()
    context = gateway.contexts["parent-problem"]
    content = context["normalized_content"]
    content["sections"] = [
        {
            "key": "condition",
            "section_id": "condition:1",
            "html": (
                '<p>В треугольнике ABC угол C равен 90°, '
                '<span data-inline-latex="AC=8"></span>, '
                '<span data-inline-latex="\\tg A=0{,}5"></span>. '
                'Найдите <span data-inline-latex="BC"></span>.</p>'
            ),
        },
        {
            "key": "answer",
            "section_id": "answer:1",
            "html": '<p><span data-effect="spaced">3</span></p>',
        },
    ]
    target = ProblemTarget(
        problem_id="parent-problem",
        source_problem_id="27243",
        source_group_id="f8e433ab-6dc0-41fc-9841-6de9135566c4",
        group_key="27243",
        problem_order_index=1,
    )
    reporter = ProgressReporter(
        console=StringIO(),
        internal=StringIO(),
        color=False,
    )

    results = run_content_rule_stage(
        gateway,
        (target,),
        target,
        get_group_profile("27243"),
        reporter,
        run_dir=tmp_path,
        resume=False,
        apply=False,
        batch_size=1,
        batch_pause_seconds=0,
        max_workers=1,
    )

    manifest = json.loads(
        (tmp_path / "prepared-manifest.json").read_text(encoding="utf-8")
    )
    transformations = manifest["records"][0]["transformations"]
    solution = next(
        item
        for item in transformations
        if item["transformation_target_id"] == "section:solution"
    )
    assert results[0].status == "planned"
    assert manifest["content_rule_key"] == "right-triangle-tangent-opposite-cathetus"
    assert manifest["records"][0]["expected_answer"] == "4"
    assert r"\tg A=\frac{BC}{AC}" in solution["value"]["html"]
    assert r"BC=AC\tg A=8\cdot 0{,}5=4" in solution["value"]["html"]
