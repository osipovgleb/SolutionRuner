"""Strict group-27708 coverage from the parent and one real repair child."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.models import ProblemTarget
from solution_runner.pipelines.triangles.right.planner import (
    RightTrianglePlanError,
)
from solution_runner.pipelines.triangles.right.runtime import (
    _content_rule_manifest,
    apply_frozen_manifest,
)
from solution_runner.pipelines.vectors.rectangle_vector_sum_planner import (
    CONDITION_ASSET_ID,
    CONDITION_ASSET_SHA256,
    RULE,
    build_repair_plan,
)


PARENT_ID = "a5911e86-63f8-4612-93d9-8751707fe3aa"
CHILD_ID = "bd05d461-9415-42b9-b00c-92d08f302b8e"
PNG_ID = "sample-png"


def _condition_html(a: int, b: int, asset_id: str | None = None) -> str:
    image = (
        f'<img alt="" data-asset-id="{asset_id}" data-asset-key="image_1" '
        'data-transformation-target-id="asset:image_1" '
        f'src="/assets/{asset_id}"/>'
        if asset_id
        else ""
    )
    return (
        f"<p>{image}Две сто­ро­ны пря­мо­уголь­ни­ка <i>ABCD</i> равны "
        f"{a} и {b}. Най­ди­те длину суммы век­то­ров "
        '<span data-inline-latex="\\overrightarrow{AB}"></span> и '
        '<span data-inline-latex="\\overrightarrow{AD}"></span>.</p>'
    )


def _solution_html(a: int, b: int, answer: int) -> str:
    square_sum = a * a + b * b
    return (
        '<p>Сумма век­то­ров  '
        '<span data-inline-latex="\\overrightarrow{AB}"></span> и  '
        '<span data-inline-latex="\\overrightarrow{AD}"></span> равна век­то­ру  '
        '<span data-inline-latex="\\overrightarrow{AC}"></span>. Век­тор  '
        '<span data-inline-latex="\\overrightarrow{AC}"></span> делит '
        'пря­мо­уголь­ник на два пря­мо­уголь­ных тре­уголь­ни­ка. '
        'Сле­до­ва­тель­но, по тео­ре­ме Пи­фа­го­ра по­лу­ча­ем:</p>'
        '<center><p> '
        f'<span data-inline-latex="AC=\\sqrt{{{a}^{{2}}+{b}^{{2}}}}='
        f'\\sqrt{{{square_sum}}}={answer}"></span>.</p></center>'
    )


def _context(
    problem_id: str,
    a: int,
    b: int,
    *,
    asset_id: str | None,
    answer: str | None,
    solution: str | None = None,
) -> dict:
    sections = [{
        "key": "condition",
        "section_id": "condition:1",
        "transformation_target_id": "section:condition:1",
        "title": "Условие",
        "asset_keys": ["image_1"] if asset_id else [],
        "html": _condition_html(a, b, asset_id),
    }]
    if answer is not None:
        sections.append({
            "key": "answer", "section_id": "answer:1",
            "transformation_target_id": "section:answer:1", "title": "Ответ",
            "asset_keys": [],
            "html": f'<p><span data-effect="spaced">{answer}</span></p>',
        })
    if solution is not None:
        sections.append({
            "key": "solution", "section_id": "solution:1",
            "transformation_target_id": "section:solution:1", "title": "Решение",
            "asset_keys": [], "html": solution,
        })
    assets = [] if asset_id is None else [{
        "asset_key": "image_1", "asset_id": asset_id,
        "url": f"/assets/{asset_id}", "kind": "ordinary_image", "alt": "",
        "transformation_target_id": "asset:image_1",
    }]
    return {"problem_id": problem_id, "normalized_content": {
        "format": "teacherhelper-normalized", "schema_version": 3,
        "assets": assets, "sections": sections,
    }}


PARENT = _context(
    PARENT_ID, 6, 8, asset_id=CONDITION_ASSET_ID, answer="10",
    solution=_solution_html(6, 8, 10),
)
REPAIR_CHILD = _context(CHILD_ID, 14, 48, asset_id=None, answer="50")


def _plan(context: dict, content_type: str | None):
    return build_repair_plan(
        context, parent_condition_asset_id=CONDITION_ASSET_ID,
        current_asset_content_type=content_type,
    )


def _by_target(plan) -> dict[str, dict]:
    return {item["transformation_target_id"]: item for item in plan.transformations}


def _transformation(plan, target_prefix: str) -> dict:
    return next(
        item
        for item in plan.transformations
        if item["transformation_target_id"].startswith(target_prefix)
    )


def _materialize(context: dict, plan) -> dict:
    result = deepcopy(context)
    content = result["normalized_content"]
    for item in plan.transformations:
        target, value = item["transformation_target_id"], deepcopy(item["value"])
        if target == "asset:image_1":
            content["assets"] = [{key: value[key] for key in (
                "asset_key", "asset_id", "url", "kind", "alt"
            )} | {"transformation_target_id": "asset:image_1"}]
            condition = next(s for s in content["sections"] if s["key"] == "condition")
            condition["asset_keys"] = ["image_1"]
            image = value["html"].replace(
                " data-asset-key=",
                ' data-transformation-target-id="asset:image_1" data-asset-key=',
            )
            condition["html"] = condition["html"].replace("<p>", f"<p>{image}", 1)
            continue
        key = target.split(":")[1]
        section = next((s for s in content["sections"] if s["key"] == key), None)
        if section is None:
            content["sections"].append({
                "key": key, "section_id": f"{key}:1",
                "transformation_target_id": f"section:{key}:1", **value,
            })
        else:
            section.update(value)
    return result


def test_profile_pins_scope_rule_and_parent_svg() -> None:
    profile = get_group_profile("27708")
    assert profile.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
    assert profile.snapshot_theme_id == "64fdf550-dcad-489a-aea5-0682edf81d76"
    assert profile.source_group_id == "363c95ed-4a3d-421e-a382-240b162aa85b"
    assert profile.group_order_index == 3
    assert profile.content_rule_key == RULE
    assert profile.condition_asset_id == CONDITION_ASSET_ID
    assert profile.condition_asset_sha256 == CONDITION_ASSET_SHA256
    assert profile.existing_solution_policy == "rewrite"


def test_parent_is_complete_and_child_receives_value_adapted_solution() -> None:
    parent_plan = _plan(deepcopy(PARENT), "image/svg+xml")
    child_plan = _plan(deepcopy(REPAIR_CHILD), None)
    solution = _transformation(child_plan, "section:solution")["value"]["html"]

    assert parent_plan.answer == "10"
    assert parent_plan.transformations == ()
    assert r"AC=\sqrt{6^{2}+8^{2}}=\sqrt{100}=10" in _solution_html(6, 8, 10)
    assert child_plan.answer == "50"
    assert r"AC=\sqrt{14^{2}+48^{2}}=\sqrt{2500}=50" in solution
    assert solution.count(r"\overrightarrow{AB}") == 1
    assert solution.count(r"\overrightarrow{AD}") == 1
    assert solution.count(r"\overrightarrow{AC}") == 2
    assert "Ответ:" not in solution


def test_missing_asset_is_added_and_png_is_rewritten_to_svg() -> None:
    added = _by_target(_plan(REPAIR_CHILD, None))["asset:image_1"]
    png = _context("png", 14, 48, asset_id=PNG_ID, answer="50")
    rewritten = _by_target(_plan(png, "image/png"))["asset:image_1"]
    assert added["operation"] == "add"
    assert rewritten["operation"] == "rewrite"
    assert rewritten["value"]["asset_id"] == CONDITION_ASSET_ID


def test_matching_svg_is_preserved() -> None:
    matching = _context("matching", 14, 48, asset_id=CONDITION_ASSET_ID, answer="50")
    assert "asset:image_1" not in _by_target(_plan(matching, "image/svg+xml"))


@pytest.mark.parametrize("stored", [None, "", "-", "49", "50,0"])
def test_missing_malformed_and_wrong_answers_are_repaired(stored: str | None) -> None:
    context = _context("answer", 14, 48, asset_id=None, answer=stored)
    answer = _transformation(_plan(context, None), "section:answer")["value"]
    assert answer["html"] == '<p><span data-effect="spaced">50</span></p>'


@pytest.mark.parametrize("stored", [None, "", "<p>-</p>", _solution_html(6, 8, 10)])
def test_missing_malformed_and_wrong_solutions_are_repaired(
    stored: str | None,
) -> None:
    context = _context(
        "solution", 14, 48, asset_id=None, answer="50", solution=stored
    )
    solution = _transformation(_plan(context, None), "section:solution")["value"]
    assert solution["html"] == _solution_html(14, 48, 50)


def test_unsupported_math_and_foreign_assets_fail_closed() -> None:
    non_square = _context("bad-math", 2, 3, asset_id=None, answer="4")
    wrong_vectors = deepcopy(REPAIR_CHILD)
    wrong_vectors["normalized_content"]["sections"][0]["html"] = _condition_html(
        14, 48
    ).replace(r"\overrightarrow{AD}", r"\overrightarrow{CD}")
    foreign_svg = _context("foreign", 14, 48, asset_id="foreign-svg", answer="50")
    duplicate = deepcopy(REPAIR_CHILD)
    duplicate["normalized_content"]["assets"] = [
        {"asset_key": "image_1", "asset_id": "one", "url": "/assets/one", "kind": "ordinary_image", "alt": ""},
        {"asset_key": "image_2", "asset_id": "two", "url": "/assets/two", "kind": "ordinary_image", "alt": ""},
    ]
    for context, content_type in (
        (non_square, None), (wrong_vectors, None),
        (foreign_svg, "image/svg+xml"), (duplicate, None),
    ):
        with pytest.raises(RightTrianglePlanError):
            _plan(context, content_type)


def test_fresh_materialized_readback_has_no_repairs() -> None:
    materialized = _materialize(REPAIR_CHILD, _plan(REPAIR_CHILD, None))
    assert _plan(materialized, "image/svg+xml").transformations == ()


class _RuntimeGateway:
    def __init__(self, contexts: dict[str, dict]) -> None:
        self.contexts = deepcopy(contexts)
        self.context_reads: list[str] = []
        self.target_reads: list[tuple[str, str]] = []
        self.writes: list[str] = []

    def get_problem_context(self, problem_id: str) -> dict:
        self.context_reads.append(problem_id)
        return deepcopy(self.contexts[problem_id])

    def get_asset_metadata(self, asset_id: str) -> dict:
        content_type = "image/svg+xml" if asset_id == CONDITION_ASSET_ID else "image/png"
        return {"asset_id": asset_id, "content_type": content_type}

    def get_problem_asset_target_context(self, problem_id: str, transformation_target_id: str) -> dict:
        self.target_reads.append((problem_id, transformation_target_id))
        return {"problem_id": problem_id, "transformation_target_id": transformation_target_id}

    def apply_problem_transformations(self, problem_id: str, transformations: list[dict]) -> dict:
        self.writes.append(problem_id)
        self.contexts[problem_id] = _materialize(
            self.contexts[problem_id],
            SimpleNamespace(transformations=tuple(deepcopy(transformations))),
        )
        return {"problem_id": problem_id, "applied_count": len(transformations)}


def _target(problem_id: str, source_problem_id: str, order: int) -> ProblemTarget:
    return ProblemTarget(
        problem_id=problem_id, source_problem_id=source_problem_id,
        source_group_id="363c95ed-4a3d-421e-a382-240b162aa85b",
        group_key="27708", problem_order_index=order,
    )


def test_targeted_manifest_reads_only_selected_child() -> None:
    other = _context("not-selected", 9, 40, asset_id=None, answer="41")
    gateway = _RuntimeGateway({PARENT_ID: PARENT, CHILD_ID: REPAIR_CHILD, "not-selected": other})
    manifest = _content_rule_manifest(
        gateway, (_target(CHILD_ID, "60205", 2),),
        profile=get_group_profile("27708"), parent_asset_id=CONDITION_ASSET_ID,
        parent_solution_assets=(), parent_solution_html="audited parent template",
        max_workers=1,
    )
    assert gateway.context_reads == [CHILD_ID]
    assert [record["source_problem_id"] for record in manifest["records"]] == ["60205"]


def test_unsupported_record_gets_no_writes_while_child_continues(tmp_path) -> None:
    unsupported = _context("unsupported", 2, 3, asset_id=None, answer="4")
    gateway = _RuntimeGateway({"unsupported": unsupported, CHILD_ID: REPAIR_CHILD})
    manifest = _content_rule_manifest(
        gateway,
        (_target("unsupported", "bad", 1), _target(CHILD_ID, "60205", 2)),
        profile=get_group_profile("27708"), parent_asset_id=CONDITION_ASSET_ID,
        parent_solution_assets=(), max_workers=1,
    )
    assert [record["status"] for record in manifest["records"]] == ["blocked", "prepared"]
    summary = apply_frozen_manifest(
        gateway, manifest, batch_size=1, max_workers=1,
        checkpoint_path=tmp_path / "apply-results.json",
    )
    assert gateway.writes == [CHILD_ID]
    assert summary["blocked_count"] == 1
    assert summary["applied_count"] == 1
    assert _plan(gateway.contexts[CHILD_ID], "image/svg+xml").transformations == ()
