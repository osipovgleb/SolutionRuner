"""Verify explicit-group orchestration, one image pass, and restart boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from pathlib import Path
import threading
from typing import Any

import pytest

from solution_runner.pipelines.core.group_profiles import CATALOG_SNAPSHOT_ID
from solution_runner.pipelines.grid_polygon.inventory import GroupInventory
from solution_runner.pipelines.grid_polygon.launcher import LauncherDependencies, main
from solution_runner.pipelines.core.models import (
    PreparedGridPolygon,
    ProblemStageResult,
    ProblemTarget,
)


@dataclass
class Calls:
    """Collect injected orchestration calls."""

    inventories: list[str]
    image_runs: list[bool]
    strategy_keys: list[str]
    solution_runs: int = 0
    helpers_runs: int = 0
    inventory_workers: list[int] | None = None
    solution_workers: list[int] | None = None
    helpers_workers: list[int] | None = None

    def __post_init__(self) -> None:
        """Allocate optional worker observations without shared list defaults."""

        self.inventory_workers = self.inventory_workers or []
        self.solution_workers = self.solution_workers or []
        self.helpers_workers = self.helpers_workers or []


def _dependencies(tmp_path: Path, calls: Calls, *, helpers_only: bool = False) -> LauncherDependencies:
    """Build one completely local launcher dependency set."""

    target = ProblemTarget(
        problem_id="problem-1",
        source_problem_id="247203",
        source_group_id="96309f98-73c1-4abc-8005-73a4307e7295",
        group_key="27547",
        problem_order_index=1,
    )

    def inventory(
        _gateway: object,
        profile: object,
        *,
        max_workers: int = 1,
    ) -> GroupInventory:
        """Return one explicit PNG target."""

        calls.inventories.append(profile.group_key)
        assert calls.inventory_workers is not None
        calls.inventory_workers.append(max_workers)
        return GroupInventory(targets=(target,), png_targets=(target,), svg_targets=())

    def prepare_images(
        _executor: object,
        *,
        profile: object,
        run_dir: Path,
        expected_targets: tuple[ProblemTarget, ...],
        apply: bool,
        **_: object,
    ) -> tuple[PreparedGridPolygon, ...]:
        """Freeze one synthetic SVG and record the single image pass."""

        calls.image_runs.append(apply)
        artifact = run_dir / "condition.svg"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("<svg></svg>")
        return (
            PreparedGridPolygon(
                problem_id=target.problem_id,
                source_problem_id=target.source_problem_id,
                condition_asset_id="asset-1",
                condition_svg_path=artifact,
                condition_svg_sha256=hashlib.sha256(b"<svg></svg>").hexdigest(),
                coordinates=((1, 2), (7, 2), (1, 6)),
                vertex_count=3,
                condition_was_replaced=True,
                converter_diagnostics={},
            ),
        )

    def solution_stage(
        _gateway: object,
        prepared: tuple[PreparedGridPolygon, ...],
        profile: object,
        strategy: object,
        _reporter: object,
        *,
        apply: bool,
        max_workers: int = 1,
    ) -> tuple[ProblemStageResult, ...]:
        """Record selected strategy and return one verified result."""

        calls.solution_runs += 1
        calls.strategy_keys.append(strategy.key)
        assert calls.solution_workers is not None
        calls.solution_workers.append(max_workers)
        assert apply is (not helpers_only) and len(prepared) == 1 and profile.group_key == "27547"
        return (
            ProblemStageResult(
                problem_id=target.problem_id,
                source_problem_id=target.source_problem_id,
                stage="solution_answer",
                status="planned" if helpers_only else "applied",
            ),
        )

    def helpers_stage(
        _gateway: object,
        solution_results: tuple[ProblemStageResult, ...],
        _profile: object,
        _reporter: object,
        *,
        apply: bool,
        max_workers: int = 1,
    ) -> tuple[ProblemStageResult, ...]:
        """Record Helpers invocation for the verified target only."""

        calls.helpers_runs += 1
        assert calls.helpers_workers is not None
        calls.helpers_workers.append(max_workers)
        assert apply is True and solution_results[0].status == ("already_complete" if helpers_only else "applied")
        return (
            ProblemStageResult(
                problem_id=target.problem_id,
                source_problem_id=target.source_problem_id,
                stage="helpers",
                status="applied",
            ),
        )

    def targeted_inventory(
        _gateway: object,
        profile: object,
        *,
        source_problem_ids: tuple[str, ...],
        problem_ids: tuple[str, ...],
        max_workers: int = 1,
    ) -> GroupInventory:
        """Return the one explicit target without invoking full inventory."""

        assert profile.group_key == "27547" and max_workers > 0
        assert (source_problem_ids, problem_ids) in {
            (("247203",), ()),
            ((), ("problem-1",)),
        }
        return GroupInventory(targets=(target,), png_targets=(target,), svg_targets=())

    class Gateway:
        def get_problem_context(self, _problem_id: str) -> dict[str, object]:
            return {"normalized_content": {"sections": [
                {"key": "solution", "html": "<p>Решение</p>"},
                {"key": "answer", "html": "<p>5</p>"},
            ]}}

    return LauncherDependencies(
        gateway_factory=lambda _api_key: Gateway(),
        inventory=inventory,
        targeted_inventory=targeted_inventory,
        image_executor=lambda _command: 0,
        prepare_images=prepare_images,
        prepare_rings=lambda *args, **kwargs: pytest.fail(
            "unexpected ring preparation"
        ),
        prepare_existing=lambda *args, **kwargs: pytest.fail("unexpected existing SVG"),
        solution_stage=solution_stage,
        helpers_stage=helpers_stage,
        output_root=tmp_path / "runs",
        now=lambda: datetime(2026, 8, 30, 3, 30, 44, tzinfo=UTC),
    )


def test_launcher_uses_explicit_group_and_one_apply_image_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not discover a next group or duplicate apply with a dry-run pass."""

    calls = Calls([], [], [])
    monkeypatch.setenv("TEACHERHELPER_MCP_API_KEY", "test-key")
    exit_code = main(
        [
            "--group",
            "27547",
            "--confirm-catalog",
            CATALOG_SNAPSHOT_ID,
            "--apply",
        ],
        deps=_dependencies(tmp_path, calls),
    )

    assert exit_code == 0
    assert calls.inventories == ["27547"]
    assert calls.image_runs == [True]
    assert calls.strategy_keys == ["base-height-triangle"]
    assert calls.solution_runs == calls.helpers_runs == 1


def test_geometry_helpers_only_does_not_apply_solution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = Calls([], [], [])
    monkeypatch.setenv("TEACHERHELPER_MCP_API_KEY", "test-key")

    assert main(
        [
            "--group", "27547",
            "--confirm-catalog", CATALOG_SNAPSHOT_ID,
            "--apply",
            "--helpers-from-existing-solution",
        ],
        deps=_dependencies(tmp_path, calls, helpers_only=True),
    ) == 0

    assert calls.solution_runs == 0
    assert calls.helpers_runs == 1
    assert calls.image_runs == []


def test_internal_problem_selector_uses_targeted_initialization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Do not run full inventory before selecting one internal problem UUID."""

    calls = Calls([], [], [])
    monkeypatch.setenv("TEACHERHELPER_MCP_API_KEY", "test-key")

    assert main(
        [
            "--group",
            "27547",
            "--confirm-catalog",
            CATALOG_SNAPSHOT_ID,
            "--only-problem-id",
            "problem-1",
            "--apply",
        ],
        deps=_dependencies(tmp_path, calls),
    ) == 0

    assert calls.inventories == []
    output = capsys.readouterr().out
    assert "\x1b[" in output
    assert "TARGET SELECTION STARTED" in output
    assert "TARGET SELECTION COMPLETED  TARGETS 1" in output
    assert "INVENTORY STARTED" not in output


def test_launcher_routes_content_rule_group_without_geometry_preparation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reuse orchestration and Helpers without invoking the grid image pipeline."""

    calls = Calls([], [], [])
    base = _dependencies(tmp_path, calls)
    targets = tuple(
        ProblemTarget(
            problem_id=f"problem-{index}",
            source_problem_id=source_problem_id,
            source_group_id="8b5a2cb7-4831-4355-9d47-e473b8aef65c",
            group_key="27238",
            problem_order_index=index,
        )
        for index, source_problem_id in enumerate(("27238", "4583"), start=1)
    )
    content_calls: list[tuple[str, ...]] = []

    def inventory(
        _gateway: object,
        profile: object,
        *,
        max_workers: int = 1,
    ) -> GroupInventory:
        """Return two targets whose assets must not enter geometry preparation."""

        assert profile.group_key == "27238" and max_workers == 3
        return GroupInventory(targets=targets, png_targets=targets, svg_targets=())

    def content_rule_stage(
        _gateway: object,
        selected_targets: tuple[ProblemTarget, ...],
        asset_source_target: ProblemTarget,
        profile: object,
        _reporter: object,
        *,
        run_dir: Path,
        resume: bool,
        apply: bool,
        batch_size: int,
        batch_pause_seconds: float,
        max_workers: int,
    ) -> tuple[ProblemStageResult, ...]:
        """Record the content-rule branch and return isolated task outcomes."""

        assert run_dir.is_dir()
        assert not resume and apply
        assert (batch_size, batch_pause_seconds, max_workers) == (10, 0, 3)
        assert asset_source_target == targets[0]
        content_calls.append(tuple(target.source_problem_id for target in selected_targets))
        return tuple(
            ProblemStageResult(
                problem_id=target.problem_id,
                source_problem_id=target.source_problem_id,
                stage="solution_answer",
                status="applied",
            )
            for target in selected_targets
        )

    deps = LauncherDependencies(
        **{
            **base.__dict__,
            "inventory": inventory,
            "prepare_images": lambda *args, **kwargs: pytest.fail(
                "content rule must not prepare grid images"
            ),
            "solution_stage": lambda *args, **kwargs: pytest.fail(
                "content rule must not enter geometry solution runtime"
            ),
            "content_rule_stage": content_rule_stage,
        }
    )
    monkeypatch.setenv("TEACHERHELPER_MCP_API_KEY", "test-key")

    assert main(
        [
            "--group",
            "27238",
            "--confirm-catalog",
            "41bc4d03-40cd-4407-8dea-df76e3f47ea8",
            "--max-workers",
            "3",
            "--apply",
        ],
        deps=deps,
    ) == 0
    assert content_calls == [("27238", "4583")]
    assert calls.helpers_runs == 1


def test_content_rule_group_can_run_every_task_except_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep the canonical first task as source context, never as an apply target."""

    calls = Calls([], [], [])
    base = _dependencies(tmp_path, calls)
    targets = tuple(
        ProblemTarget(
            problem_id=f"problem-{index}",
            source_problem_id=source_problem_id,
            source_group_id="8b5a2cb7-4831-4355-9d47-e473b8aef65c",
            group_key="27238",
            problem_order_index=index,
        )
        for index, source_problem_id in enumerate(("27238", "4583", "4584"), start=1)
    )
    observed: list[tuple[tuple[str, ...], str]] = []

    def content_rule_stage(
        _gateway: object,
        selected_targets: tuple[ProblemTarget, ...],
        asset_source_target: ProblemTarget,
        _profile: object,
        _reporter: object,
        **_: object,
    ) -> tuple[ProblemStageResult, ...]:
        observed.append(
            (
                tuple(target.source_problem_id for target in selected_targets),
                asset_source_target.source_problem_id,
            )
        )
        return tuple(
            ProblemStageResult(
                problem_id=target.problem_id,
                source_problem_id=target.source_problem_id,
                stage="solution_answer",
                status="applied",
            )
            for target in selected_targets
        )

    deps = LauncherDependencies(
        **{
            **base.__dict__,
            "inventory": lambda *_args, **_kwargs: GroupInventory(
                targets=targets, png_targets=(), svg_targets=()
            ),
            "content_rule_stage": content_rule_stage,
        }
    )
    monkeypatch.setenv("TEACHERHELPER_MCP_API_KEY", "test-key")

    assert main(
        [
            "--group",
            "27238",
            "--confirm-catalog",
            "41bc4d03-40cd-4407-8dea-df76e3f47ea8",
            "--exclude-parent-problem",
            "--apply",
        ],
        deps=deps,
    ) == 0
    assert observed == [(("4583", "4584"), "27238")]


def test_launcher_passes_explicit_worker_bound_to_parallel_stages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use one validated worker bound across inventory, solution, and Helpers."""

    calls = Calls([], [], [])
    monkeypatch.setenv("TEACHERHELPER_MCP_API_KEY", "test-key")

    assert main(
        [
            "--group",
            "27547",
            "--confirm-catalog",
            CATALOG_SNAPSHOT_ID,
            "--max-workers",
            "3",
            "--apply",
        ],
        deps=_dependencies(tmp_path, calls),
    ) == 0

    assert calls.inventory_workers == [3]
    assert calls.solution_workers == [3]
    assert calls.helpers_workers == [3]


def test_launcher_rejects_catalog_before_gateway_creation(tmp_path: Path) -> None:
    """Fail closed on catalog mismatch before any runtime side effect."""

    calls = Calls([], [], [])
    deps = _dependencies(tmp_path, calls)
    gateway_calls = 0

    def gateway_factory(_api_key: str) -> object:
        """Record a gateway creation that must not occur."""

        nonlocal gateway_calls
        gateway_calls += 1
        return object()

    deps = LauncherDependencies(**{**deps.__dict__, "gateway_factory": gateway_factory})

    with pytest.raises(SystemExit):
        main(
            ["--group", "27547", "--confirm-catalog", "wrong", "--apply"],
            deps=deps,
        )
    assert gateway_calls == 0


def test_content_rule_group_rejects_geometry_image_resume(tmp_path: Path) -> None:
    """Keep a content-only group from overwriting a run through the wrong resume mode."""

    calls = Calls([], [], [])
    with pytest.raises(SystemExit):
        main(
            [
                "--group",
                "27238",
                "--confirm-catalog",
                "41bc4d03-40cd-4407-8dea-df76e3f47ea8",
                "--resume-images",
                str(tmp_path),
                "--apply",
            ],
            deps=_dependencies(tmp_path, calls),
        )
    assert calls.inventories == []


def test_launcher_can_resume_solutions_without_image_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Read one frozen prepared manifest and never rerun the converter."""

    calls = Calls([], [], [])
    deps = _dependencies(tmp_path, calls)
    monkeypatch.setenv("TEACHERHELPER_MCP_API_KEY", "test-key")
    assert main(
        [
            "--group",
            "27547",
            "--confirm-catalog",
            CATALOG_SNAPSHOT_ID,
            "--apply",
        ],
        deps=deps,
    ) == 0
    run_dir = next((tmp_path / "runs").iterdir())
    calls.image_runs.clear()

    assert main(
        [
            "--group",
            "27547",
            "--confirm-catalog",
            CATALOG_SNAPSHOT_ID,
            "--resume-solutions",
            str(run_dir),
            "--apply",
        ],
        deps=deps,
    ) == 0
    assert calls.image_runs == []


def test_launcher_resumes_successful_prepared_subset_after_image_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resume only frozen prepared records when another image target had failed."""

    calls = Calls([], [], [])
    base = _dependencies(tmp_path, calls)
    base_inventory = base.inventory
    failed_target = ProblemTarget(
        problem_id="problem-image-failed",
        source_problem_id="247205",
        source_group_id="96309f98-73c1-4abc-8005-73a4307e7295",
        group_key="27547",
        problem_order_index=2,
    )

    def inventory(
        gateway: object,
        profile: object,
        *,
        max_workers: int = 1,
    ) -> GroupInventory:
        """Return one prepared target and one target that never prepared."""

        assert max_workers > 0
        original = base_inventory(gateway, profile)
        return GroupInventory(
            targets=(*original.targets, failed_target),
            png_targets=(*original.png_targets, failed_target),
            svg_targets=(),
        )

    deps = LauncherDependencies(**{**base.__dict__, "inventory": inventory})
    monkeypatch.setenv("TEACHERHELPER_MCP_API_KEY", "test-key")
    assert main(
        [
            "--group",
            "27547",
            "--confirm-catalog",
            CATALOG_SNAPSHOT_ID,
            "--apply",
        ],
        deps=deps,
    ) == 0
    run_dir = next((tmp_path / "runs").iterdir())
    calls.image_runs.clear()

    assert main(
        [
            "--group",
            "27547",
            "--confirm-catalog",
            CATALOG_SNAPSHOT_ID,
            "--resume-solutions",
            str(run_dir),
            "--apply",
        ],
        deps=deps,
    ) == 0
    assert calls.image_runs == []


def test_launcher_filters_multiple_source_problem_ids_after_one_inventory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prepare and mutate only all explicitly repeated source problem ids."""

    calls = Calls([], [], [])
    base = _dependencies(tmp_path, calls)
    targets = tuple(
        ProblemTarget(
            problem_id=f"problem-{index}",
            source_problem_id=source_problem_id,
            source_group_id="96309f98-73c1-4abc-8005-73a4307e7295",
            group_key="27547",
            problem_order_index=index,
        )
        for index, source_problem_id in enumerate(
            ("247203", "247205", "247207"),
            start=1,
        )
    )
    prepared_source_problem_ids: list[str] = []
    solution_source_problem_ids: list[str] = []
    preparation_lock = threading.Lock()
    second_preparation_entered = threading.Event()
    active_preparations = 0
    max_active_preparations = 0

    def inventory(
        _gateway: object,
        profile: object,
        *,
        max_workers: int = 1,
    ) -> GroupInventory:
        """Return three existing SVG targets from one inventory read."""

        assert max_workers > 0
        calls.inventories.append(profile.group_key)
        return GroupInventory(targets=targets, png_targets=(), svg_targets=targets)

    def targeted_inventory(
        _gateway: object,
        profile: object,
        *,
        source_problem_ids: tuple[str, ...],
        problem_ids: tuple[str, ...],
        max_workers: int = 1,
    ) -> GroupInventory:
        """Return only requested records without invoking full inventory."""

        assert profile.group_key == "27547" and max_workers > 0
        assert source_problem_ids == ("247203", "247207")
        assert problem_ids == ()
        requested = set(source_problem_ids)
        selected = tuple(
            target for target in targets if target.source_problem_id in requested
        )
        return GroupInventory(targets=selected, png_targets=(), svg_targets=selected)

    def prepare_existing(
        _gateway: object,
        target: ProblemTarget,
        *,
        artifact_dir: Path,
        **_: object,
    ) -> PreparedGridPolygon:
        """Freeze one selected existing SVG without external I/O."""

        nonlocal active_preparations, max_active_preparations
        with preparation_lock:
            active_preparations += 1
            max_active_preparations = max(
                max_active_preparations,
                active_preparations,
            )
            if active_preparations == 2:
                second_preparation_entered.set()
        second_preparation_entered.wait(timeout=0.2)
        prepared_source_problem_ids.append(target.source_problem_id)
        artifact = artifact_dir / f"{target.source_problem_id}.svg"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("<svg></svg>", encoding="utf-8")
        with preparation_lock:
            active_preparations -= 1
        return PreparedGridPolygon(
            problem_id=target.problem_id,
            source_problem_id=target.source_problem_id,
            condition_asset_id=f"asset-{target.source_problem_id}",
            condition_svg_path=artifact,
            condition_svg_sha256=hashlib.sha256(b"<svg></svg>").hexdigest(),
            coordinates=((1, 2), (7, 2), (1, 6)),
            vertex_count=3,
            condition_was_replaced=False,
            converter_diagnostics={},
        )

    def solution_stage(
        _gateway: object,
        prepared: tuple[PreparedGridPolygon, ...],
        _profile: object,
        _strategy: object,
        _reporter: object,
        *,
        apply: bool,
        max_workers: int = 1,
    ) -> tuple[ProblemStageResult, ...]:
        """Record the selected multi-target scope presented to writes."""

        assert apply is True and max_workers > 0
        solution_source_problem_ids.extend(
            record.source_problem_id for record in prepared
        )
        return tuple(
            ProblemStageResult(
                problem_id=record.problem_id,
                source_problem_id=record.source_problem_id,
                stage="solution_answer",
                status="applied",
            )
            for record in prepared
        )

    def helpers_stage(
        _gateway: object,
        solution_results: tuple[ProblemStageResult, ...],
        _profile: object,
        _reporter: object,
        *,
        apply: bool,
        max_workers: int = 1,
    ) -> tuple[ProblemStageResult, ...]:
        """Return successful Helpers results for the same selected scope."""

        assert apply is True and max_workers > 0
        return tuple(
            ProblemStageResult(
                problem_id=result.problem_id,
                source_problem_id=result.source_problem_id,
                stage="helpers",
                status="applied",
            )
            for result in solution_results
        )

    deps = LauncherDependencies(
        **{
            **base.__dict__,
            "inventory": lambda *args, **kwargs: pytest.fail(
                "full inventory must not run for exact selectors"
            ),
            "targeted_inventory": targeted_inventory,
            "prepare_existing": prepare_existing,
            "solution_stage": solution_stage,
            "helpers_stage": helpers_stage,
        }
    )
    monkeypatch.setenv("TEACHERHELPER_MCP_API_KEY", "test-key")

    assert main(
        [
            "--group",
            "27547",
            "--confirm-catalog",
            CATALOG_SNAPSHOT_ID,
            "--only-source-problem-id",
            "247203",
            "--only-source-problem-id",
            "247207",
            "--apply",
        ],
        deps=deps,
    ) == 0
    assert calls.inventories == []
    assert sorted(prepared_source_problem_ids) == ["247203", "247207"]
    assert max_active_preparations == 2
    assert solution_source_problem_ids == ["247203", "247207"]
