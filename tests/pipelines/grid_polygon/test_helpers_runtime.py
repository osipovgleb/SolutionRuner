"""Verify Helpers state is limited to fully verified solution targets."""

from __future__ import annotations

from io import StringIO
import threading
from typing import Any

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.grid_polygon.helpers_runtime import (
    run_helpers_stage,
    verify_existing_solutions,
)
from solution_runner.pipelines.core.models import ProblemStageResult
from solution_runner.pipelines.core.models import ProblemTarget
from solution_runner.pipelines.grid_polygon.progress import ProgressReporter


def _result(source_id: str, *, stage: str, status: str) -> ProblemStageResult:
    """Build one upstream solution outcome."""

    return ProblemStageResult(
        problem_id=f"problem-{source_id}",
        source_problem_id=source_id,
        stage=stage,
        status=status,
    )


class RecordingGateway:
    """Record token-bound Helpers writes and return database-style readback."""

    def __init__(self) -> None:
        """Create empty state with optional per-problem failures."""

        self.states: dict[str, dict[str, Any]] = {}
        self.write_problem_ids: list[str] = []
        self.fail_for: set[str] = set()

    def get_problem_pipeline_state(self, problem_id: str) -> dict[str, Any]:
        """Return Helpers values plus one concurrency token."""

        values = self.states.get(
            problem_id,
            {"helpers_status": "pending", "helpers_json": {"schema_version": 2}},
        )
        return {
            "problem_id": problem_id,
            "stage_details": {"helpers": values},
            "stage_state_tokens": {"helpers": f"token-{problem_id}"},
        }

    def set_problem_pipeline_stage_state_batch(
        self,
        stage: str,
        updates: list[dict[str, Any]],
        reason: str,
    ) -> dict[str, Any]:
        """Apply one target update and return authoritative values."""

        assert stage == "helpers"
        results = []
        for update in updates:
            problem_id = update["problem_id"]
            self.write_problem_ids.append(problem_id)
            if problem_id in self.fail_for:
                raise RuntimeError("fake Helpers failure")
            branches = update["values"]["branches"]
            values = {
                "helpers_status": "ready",
                "helpers_json": {"schema_version": 2, **branches},
            }
            self.states[problem_id] = values
            results.append(
                {
                    "problem_id": problem_id,
                    "read_from_database": True,
                    "values": values,
                }
            )
        return {
            "stage": "helpers",
            "requested_count": len(updates),
            "results": results,
        }


def _reporter() -> tuple[ProgressReporter, StringIO]:
    """Return one compact no-color test reporter."""

    console = StringIO()
    return ProgressReporter(console=console, internal=StringIO(), color=False), console


def test_helpers_excludes_failed_solution_and_answer_targets() -> None:
    """Never mark a task ready when image/solution/answer did not complete."""

    gateway = RecordingGateway()
    reporter, _ = _reporter()
    results = run_helpers_stage(
        gateway,
        (
            _result("1", stage="solution_answer", status="applied"),
            _result("2", stage="solution", status="failed"),
            _result("3", stage="answer", status="failed"),
        ),
        get_group_profile("27547"),
        reporter,
        apply=True,
    )

    assert gateway.write_problem_ids == ["problem-1"]
    assert [result.status for result in results] == ["applied", "skipped", "skipped"]


def test_helpers_sets_profile_branches_and_verifies_readback() -> None:
    """Set p2-p5 ready and p6 not_required only after token-bound readback."""

    gateway = RecordingGateway()
    reporter, console = _reporter()
    result = run_helpers_stage(
        gateway,
        (_result("1", stage="solution_answer", status="applied"),),
        get_group_profile("27547"),
        reporter,
        apply=True,
    )[0]

    helpers = gateway.states["problem-1"]["helpers_json"]
    assert result.status == "applied"
    assert all(helpers[branch]["status"] == "ready" for branch in ("p2", "p3", "p4", "p5"))
    assert helpers["p6"]["status"] == "not_required"
    assert "[1/1]  HELPERS READY" in console.getvalue()


def test_helpers_accepts_verified_existing_solution_and_matching_answer() -> None:
    """Mark Helpers ready when content planning found no repair to apply."""

    gateway = RecordingGateway()
    reporter, console = _reporter()

    result = run_helpers_stage(
        gateway,
        (_result("1", stage="solution_answer", status="already_complete"),),
        get_group_profile("27243"),
        reporter,
        apply=True,
    )[0]

    assert result.status == "applied"
    assert gateway.write_problem_ids == ["problem-1"]
    assert "[1/1]  HELPERS READY" in console.getvalue()


def test_one_helpers_failure_does_not_abort_next_target() -> None:
    """Isolate one status failure while continuing in frozen order."""

    gateway = RecordingGateway()
    gateway.fail_for.add("problem-1")
    reporter, console = _reporter()
    results = run_helpers_stage(
        gateway,
        (
            _result("1", stage="solution_answer", status="applied"),
            _result("2", stage="solution_answer", status="applied"),
        ),
        get_group_profile("27547"),
        reporter,
        apply=True,
    )

    assert [result.status for result in results] == ["failed", "applied"]
    assert "[1/2]  HELPERS FAILED" in console.getvalue()
    assert "[2/2]  HELPERS READY" in console.getvalue()


def test_helpers_preview_performs_no_write() -> None:
    """Plan eligible targets without changing pipeline state."""

    gateway = RecordingGateway()
    reporter, _ = _reporter()
    result = run_helpers_stage(
        gateway,
        (_result("1", stage="solution_answer", status="planned"),),
        get_group_profile("27547"),
        reporter,
        apply=False,
    )[0]

    assert result.status == "planned"
    assert gateway.write_problem_ids == []


class ExistingSolutionGateway(RecordingGateway):
    """Expose a fixed normalized content payload for reconciliation tests."""

    def __init__(self, context: dict[str, Any]) -> None:
        super().__init__()
        self.context = context

    def get_problem_context(self, _problem_id: str) -> dict[str, Any]:
        return self.context


def test_existing_solution_verification_requires_exact_final_numeric_answer() -> None:
    """Only an exact final numeric equality may unlock the Helpers stage."""

    target = ProblemTarget(
        problem_id="problem-1",
        source_problem_id="1",
        source_group_id="group-1",
        group_key="27547",
        problem_order_index=1,
    )
    context = {
        "normalized_content": {
            "sections": [
                {"key": "answer", "html": "<p>18,4</p>"},
                {
                    "key": "solution",
                    "html": '<p><span data-inline-latex="\\frac{23}{5}\\cdot4=18{,}4"></span></p>',
                },
            ]
        }
    }
    reporter, _ = _reporter()
    results = verify_existing_solutions(
        ExistingSolutionGateway(context), (target,), get_group_profile("27547"), reporter
    )

    assert results[0].status == "already_complete"

    context["normalized_content"]["sections"][0]["html"] = "<p>18,5</p>"
    results = verify_existing_solutions(
        ExistingSolutionGateway(context), (target,), get_group_profile("27547"), reporter
    )
    assert results[0].status == "skipped"
    assert results[0].message == "solution ends in 18{,}4, answer is 18{,}5"


class ConcurrentHelpersGateway(RecordingGateway):
    """Hold two state reads long enough to prove target overlap."""

    def __init__(self) -> None:
        """Create synchronized overlap accounting."""

        super().__init__()
        self._lock = threading.Lock()
        self._second_entered = threading.Event()
        self._active = 0
        self.max_active = 0

    def get_problem_pipeline_state(self, problem_id: str) -> dict[str, Any]:
        """Record concurrent entry before returning the real fake state."""

        with self._lock:
            self._active += 1
            self.max_active = max(self.max_active, self._active)
            if self._active == 2:
                self._second_entered.set()
        self._second_entered.wait(timeout=0.2)
        with self._lock:
            self._active -= 1
        return super().get_problem_pipeline_state(problem_id)


def test_helpers_workers_overlap_targets_and_return_frozen_order() -> None:
    """Apply eligible statuses concurrently without changing result order."""

    gateway = ConcurrentHelpersGateway()
    reporter, _ = _reporter()
    results = run_helpers_stage(
        gateway,
        (
            _result("1", stage="solution_answer", status="applied"),
            _result("2", stage="solution_answer", status="applied"),
        ),
        get_group_profile("27547"),
        reporter,
        apply=True,
        max_workers=2,
    )

    assert gateway.max_active == 2
    assert [result.source_problem_id for result in results] == ["1", "2"]
    assert [result.status for result in results] == ["applied", "applied"]
