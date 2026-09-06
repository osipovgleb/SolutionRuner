"""Strict group-27663 coverage from the parent and one real repair child."""

from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
from pathlib import Path

import pytest

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.models import ProblemTarget
from solution_runner.pipelines.grid_polygon.progress import ProgressReporter
from solution_runner.pipelines.triangles.right.planner import (
    RightTrianglePlanError,
)
from solution_runner.pipelines.triangles.right.runtime import (
    apply_frozen_manifest,
    run_content_rule_stage,
)
from solution_runner.pipelines.vectors.vector_length_planner import (
    PARENT_PROBLEM_ID,
    RULE,
    build_repair_plan,
)


CHILD_ID = "20f692c9-8189-4a1d-91fb-e9d10f5b10b5"


def _context(
    problem_id: str,
    formula: str,
    *,
    answer: str | None,
    solution: str | None = None,
    assets: list[dict] | None = None,
) -> dict:
    sections = [
        {
            "key": "condition",
            "section_id": "condition:1",
            "transformation_target_id": "section:condition:1",
            "title": "Условие",
            "asset_keys": [],
            "html": (
                '<p>Най­ди­те длину век­то­ра  '
                f'<span data-inline-latex="{formula}"></span> .</p>'
            ),
        }
    ]
    if answer is not None:
        sections.append(
            {
                "key": "answer",
                "section_id": "answer:1",
                "transformation_target_id": "section:answer:1",
                "title": "Ответ",
                "asset_keys": [],
                "html": f'<p><span data-effect="spaced">{answer}</span></p>',
            }
        )
    if solution is not None:
        sections.append(
            {
                "key": "solution",
                "section_id": "solution:1",
                "transformation_target_id": "section:solution:1",
                "title": "Решение",
                "asset_keys": [],
                "html": solution,
            }
        )
    return {
        "problem_id": problem_id,
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": assets or [],
            "sections": sections,
        },
    }


PARENT = _context(PARENT_PROBLEM_ID, r"\vec{a}(6;8)", answer="10")
REPAIR_CHILD = _context(CHILD_ID, r"\overrightarrow{a}(-15,8)", answer=None)
EQUALS_CHILD = _context(
    "bef72bfb-4a66-4db8-b4a8-6913dfcc584c",
    r"\overrightarrow{a}=(-10;24)",
    answer="26",
    solution="<p>stale</p>",
)
LATEX_COMMA_CHILD = _context(
    "be3f30b4-1cf4-4904-8cec-8fa4c628a7b3",
    r"\overrightarrow{a}=(-24{,}10)",
    answer="26",
    solution="<p>stale</p>",
)


def _plan(context: dict):
    return build_repair_plan(context, parent_condition_asset_id=None)


def _targets(plan) -> dict[str, dict]:
    return {item["transformation_target_id"]: item for item in plan.transformations}


def test_profile_registers_exact_scope_and_assetless_rule() -> None:
    profile = get_group_profile("27663")

    assert profile.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
    assert profile.source_group_id == "9e75ee4e-534e-4c70-b364-586e57afcc5d"
    assert profile.group_order_index == 0
    assert profile.content_rule_key == RULE
    assert profile.condition_asset_id is None
    assert profile.existing_solution_policy == "rewrite"


def test_parent_and_real_child_recompute_different_values() -> None:
    parent = _plan(PARENT)
    child = _plan(REPAIR_CHILD)

    assert parent.answer == "10"
    assert child.answer == "17"
    child_targets = _targets(child)
    assert set(child_targets) == {"section:solution", "section:answer"}
    solution = child_targets["section:solution"]["value"]["html"]
    assert r"\sqrt{(-15)^{2}+8^{2}}=\sqrt{289}=17" in solution
    assert "asset:image_1" not in child_targets


def test_real_equals_form_recomputes_58455() -> None:
    plan = _plan(EQUALS_CHILD)

    assert plan.answer == "26"
    targets = _targets(plan)
    assert set(targets) == {"section:solution:1"}
    assert r"\sqrt{(-10)^{2}+24^{2}}=\sqrt{676}=26" in (
        targets["section:solution:1"]["value"]["html"]
    )


def test_real_latex_comma_form_recomputes_58457() -> None:
    plan = _plan(LATEX_COMMA_CHILD)

    assert plan.answer == "26"
    targets = _targets(plan)
    assert set(targets) == {"section:solution:1"}
    assert r"\sqrt{(-24)^{2}+10^{2}}=\sqrt{676}=26" in (
        targets["section:solution:1"]["value"]["html"]
    )


def test_wrong_existing_answer_is_rewritten_and_converges() -> None:
    context = _context(
        CHILD_ID,
        r"\overrightarrow{a}(-15,8)",
        answer="99",
        solution="<p>stale</p>",
    )
    first = _plan(context)
    targets = _targets(first)

    assert targets["section:answer:1"]["operation"] == "rewrite"
    for section in context["normalized_content"]["sections"]:
        target = targets.get(section["transformation_target_id"])
        if target:
            section.update(target["value"])
    assert _plan(context).transformations == ()


@pytest.mark.parametrize(
    "formula",
    [
        r"\vec{b}(6;8)",
        r"\vec{a}(6:8)",
        r"\vec{a}(6;8;10)",
        r"\vec{a}==(6;8)",
        r"\vec{a}(6{;}8)",
    ],
)
def test_unsupported_condition_forms_fail_closed(formula: str) -> None:
    with pytest.raises(RightTrianglePlanError):
        _plan(_context("problem", formula, answer="10"))


def test_non_square_length_and_unexpected_asset_fail_closed() -> None:
    with pytest.raises(RightTrianglePlanError, match="supported exact answer"):
        _plan(_context("problem", r"\vec{a}(1;1)", answer=None))

    foreign = deepcopy(PARENT)
    foreign["normalized_content"]["assets"] = [{"asset_id": "png"}]
    with pytest.raises(RightTrianglePlanError, match="does not allow assets"):
        _plan(foreign)


class _Gateway:
    def __init__(self) -> None:
        self.contexts = {
            PARENT_PROBLEM_ID: deepcopy(PARENT),
            CHILD_ID: deepcopy(REPAIR_CHILD),
        }
        self.writes: list[str] = []

    def get_problem_context(self, problem_id: str) -> dict:
        return deepcopy(self.contexts[problem_id])

    def apply_problem_transformations(
        self, problem_id: str, transformations: list[dict]
    ) -> dict:
        self.writes.append(problem_id)
        content = self.contexts[problem_id]["normalized_content"]
        for item in transformations:
            target = item["transformation_target_id"]
            key = target.split(":", 2)[1]
            content["sections"] = [
                section for section in content["sections"] if section["key"] != key
            ]
            content["sections"].append(
                {
                    "key": key,
                    "section_id": f"{key}:1",
                    "transformation_target_id": f"section:{key}:1",
                    **deepcopy(item["value"]),
                }
            )
        return {"problem_id": problem_id}


def test_assetless_manifest_prepares_and_applies_with_readback(tmp_path: Path) -> None:
    gateway = _Gateway()
    targets = (
        ProblemTarget(
            problem_id=CHILD_ID,
            source_problem_id="58461",
            source_group_id="9e75ee4e-534e-4c70-b364-586e57afcc5d",
            group_key="27663",
            problem_order_index=31,
        ),
    )
    parent = ProblemTarget(
        problem_id=PARENT_PROBLEM_ID,
        source_problem_id="27663",
        source_group_id="9e75ee4e-534e-4c70-b364-586e57afcc5d",
        group_key="27663",
        problem_order_index=0,
    )
    reporter = ProgressReporter(console=StringIO(), internal=StringIO(), color=False)

    results = run_content_rule_stage(
        gateway,
        targets,
        parent,
        get_group_profile("27663"),
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

    assert results[0].status == "planned"
    assert manifest["condition_asset"]["source_asset_id"] is None
    assert [
        item["transformation_target_id"]
        for item in manifest["records"][0]["transformations"]
    ] == ["section:solution", "section:answer"]

    summary = apply_frozen_manifest(
        gateway,
        manifest,
        batch_size=1,
        max_workers=1,
        checkpoint_path=tmp_path / "apply-results.json",
    )
    assert summary["applied_count"] == 1
    assert summary["failed_count"] == 0
    assert gateway.writes == [CHILD_ID]
