"""Strict group-27718 coverage from the parent and one real repair child."""

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
from solution_runner.pipelines.vectors.planner import (
    CONDITION_ASSET_ALT,
    CONDITION_ASSET_ID,
    CONDITION_ASSET_SHA256,
    RULE,
    build_repair_plan,
)


PARENT_ID = "26128435-2125-4369-87db-a9e21e89520e"
CHILD_ID = "3f375ffa-4aef-40e4-a2d5-c14ebb607271"
JPEG_ID = "01f9b476-6508-4e17-80f8-a7bedd3ab289"


def _condition_html(first: int, second: int, *, image_id: str | None) -> str:
    image = (
        f'<img alt="" data-asset-id="{image_id}" data-asset-key="image_1" '
        f'data-transformation-target-id="asset:image_1" '
        f'src="/assets/{image_id}"/>'
        if image_id
        else ""
    )
    return (
        f"<p>{image}Диа­го­на­ли ромба "
        '<var data-math-identifier="ABCD">ABCD</var> пе­ре­се­ка­ют­ся в точке '
        '<var data-math-identifier="O">O</var> и равны '
        f"{first} и {second}. Най­ди­те длину век­то­ра "
        '<span data-inline-latex="\\overrightarrow{AO}-\\overrightarrow{BO}"></span>.'
        "</p>"
    )


def _context(
    problem_id: str,
    first: int,
    second: int,
    *,
    asset_id: str | None,
    answer: str | None,
    solution: str | None = None,
) -> dict:
    sections = [
        {
            "key": "condition",
            "section_id": "condition:1",
            "transformation_target_id": "section:condition:1",
            "title": "Условие",
            "asset_keys": ["image_1"] if asset_id else [],
            "html": _condition_html(first, second, image_id=asset_id),
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
    assets = []
    if asset_id:
        assets.append(
            {
                "asset_key": "image_1",
                "asset_id": asset_id,
                "url": f"/assets/{asset_id}",
                "kind": "ordinary_image",
                "alt": "",
                "transformation_target_id": "asset:image_1",
            }
        )
    return {
        "problem_id": problem_id,
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": assets,
            "sections": sections,
        },
    }


PARENT = _context(PARENT_ID, 12, 16, asset_id=CONDITION_ASSET_ID, answer="10")
REPAIR_CHILD = _context(CHILD_ID, 24, 7, asset_id=JPEG_ID, answer="12,5")


def _plan(context: dict, content_type: str | None):
    return build_repair_plan(
        context,
        parent_condition_asset_id=CONDITION_ASSET_ID,
        current_asset_content_type=content_type,
    )


def _by_target(plan) -> dict[str, dict]:
    return {
        item["transformation_target_id"]: item for item in plan.transformations
    }


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
        target = item["transformation_target_id"]
        value = deepcopy(item["value"])
        if target == "asset:image_1":
            content["assets"] = [
                {
                    key: value[key]
                    for key in ("asset_key", "asset_id", "url", "kind", "alt")
                }
                | {"transformation_target_id": "asset:image_1"}
            ]
            condition = next(
                section for section in content["sections"] if section["key"] == "condition"
            )
            condition["asset_keys"] = ["image_1"]
            soup_html = condition["html"]
            start = soup_html.find("<img")
            end = soup_html.find("/>", start) + 2
            replacement = value["html"].replace(
                " data-asset-key=",
                ' data-transformation-target-id="asset:image_1" data-asset-key=',
            )
            condition["html"] = soup_html[:start] + replacement + soup_html[end:]
            continue
        key = target.split(":")[1]
        section = next(
            (section for section in content["sections"] if section["key"] == key),
            None,
        )
        if section is None:
            content["sections"].append(
                {
                    "key": key,
                    "section_id": f"{key}:1",
                    "transformation_target_id": f"section:{key}:1",
                    **value,
                }
            )
        else:
            section.update(value)
    return result


def test_profile_pins_vector_scope_rule_and_parent_svg() -> None:
    profile = get_group_profile("27718")

    assert profile.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
    assert profile.snapshot_theme_id == "64fdf550-dcad-489a-aea5-0682edf81d76"
    assert profile.source_group_id == "d50899c8-97e9-4f30-a76c-69f2e919f379"
    assert profile.category_key == "2"
    assert profile.group_order_index == 13
    assert profile.content_rule_key == RULE
    assert profile.condition_asset_id == CONDITION_ASSET_ID
    assert profile.condition_asset_sha256 == CONDITION_ASSET_SHA256
    assert profile.existing_solution_policy == "rewrite"


@pytest.mark.parametrize(
    ("context", "content_type", "answer", "formula"),
    [
        (PARENT, "image/svg+xml", "10", r"AB=\sqrt{8^2+6^2}=10"),
        (REPAIR_CHILD, "image/jpeg", "12,5", r"AB=\sqrt{3{,}5^2+12^2}=12{,}5"),
    ],
)
def test_parent_and_real_child_receive_value_adapted_solution(
    context: dict, content_type: str, answer: str, formula: str
) -> None:
    plan = _plan(deepcopy(context), content_type)
    solution = _by_target(plan)["section:solution"]["value"]["html"]

    assert plan.answer == answer
    assert formula in solution
    assert solution.count(r"\overrightarrow{AO}") == 1
    assert solution.count(r"\overrightarrow{BO}") == 1
    assert solution.count(r"\overrightarrow{AB}") == 2
    assert "Ответ:" not in solution


def test_real_child_rewrites_jpeg_target_instead_of_adding_second_asset() -> None:
    plan = _plan(deepcopy(REPAIR_CHILD), "image/jpeg")
    asset = _by_target(plan)["asset:image_1"]

    assert asset["operation"] == "rewrite"
    assert asset["value"]["asset_id"] == CONDITION_ASSET_ID
    assert asset["value"]["url"] == f"/assets/{CONDITION_ASSET_ID}"
    assert not any(
        item["transformation_target_id"].startswith("section:answer")
        for item in plan.transformations
    )


def test_png_target_uses_the_same_exact_replacement_rule() -> None:
    context = _context("png-child", 6, 8, asset_id="png-asset", answer="5")

    asset = _by_target(_plan(context, "image/png"))["asset:image_1"]
    assert asset["operation"] == "rewrite"
    assert asset["value"]["asset_id"] == CONDITION_ASSET_ID


def test_absent_asset_is_added_but_matching_svg_is_preserved() -> None:
    missing = _context("missing", 6, 8, asset_id=None, answer="5")
    add = _by_target(_plan(missing, None))["asset:image_1"]
    assert add["operation"] == "add"

    matching = _context(
        "matching", 6, 8, asset_id=CONDITION_ASSET_ID, answer="5"
    )
    assert "asset:image_1" not in _by_target(_plan(matching, "image/svg+xml"))


@pytest.mark.parametrize("stored", [None, "", "-", "99", "12,4"])
def test_missing_malformed_and_wrong_answers_are_repaired(stored: str | None) -> None:
    context = _context("answer", 24, 7, asset_id=JPEG_ID, answer=stored)

    answer = _transformation(_plan(context, "image/jpeg"), "section:answer")["value"]
    assert answer["html"] == '<p><span data-effect="spaced">12,5</span></p>'


@pytest.mark.parametrize(
    "condition_html",
    [
        _condition_html(5, 5, image_id=JPEG_ID),
        _condition_html(24, 7, image_id=JPEG_ID).replace("ромба", "квадрата"),
        _condition_html(24, 7, image_id=JPEG_ID).replace(
            r"\overrightarrow{AO}-\overrightarrow{BO}",
            r"\overrightarrow{AO}+\overrightarrow{BO}",
        ),
    ],
)
def test_unsupported_math_or_condition_form_fails_closed(condition_html: str) -> None:
    context = deepcopy(REPAIR_CHILD)
    context["normalized_content"]["sections"][0]["html"] = condition_html

    with pytest.raises(RightTrianglePlanError):
        _plan(context, "image/jpeg")


def test_foreign_svg_duplicate_and_unresolved_assets_fail_closed() -> None:
    foreign_svg = _context("foreign", 6, 8, asset_id="foreign-svg", answer="5")
    duplicate = deepcopy(REPAIR_CHILD)
    duplicate["normalized_content"]["assets"].append(
        {
            "asset_key": "image_2",
            "asset_id": "second",
            "url": "/assets/second",
            "kind": "ordinary_image",
            "alt": "",
        }
    )
    unresolved = deepcopy(REPAIR_CHILD)
    unresolved["normalized_content"]["assets"] = []

    with pytest.raises(RightTrianglePlanError):
        _plan(foreign_svg, "image/svg+xml")
    with pytest.raises(RightTrianglePlanError):
        _plan(duplicate, None)
    with pytest.raises(RightTrianglePlanError):
        _plan(unresolved, None)


def test_materialized_jpeg_replacement_has_no_second_plan() -> None:
    initial = deepcopy(REPAIR_CHILD)
    materialized = _materialize(initial, _plan(initial, "image/jpeg"))

    assert _plan(materialized, "image/svg+xml").transformations == ()


class _RuntimeGateway:
    def __init__(self, contexts: dict[str, dict], content_types: dict[str, str]) -> None:
        self.contexts = deepcopy(contexts)
        self.content_types = dict(content_types)
        self.context_reads: list[str] = []
        self.target_reads: list[tuple[str, str]] = []
        self.writes: list[str] = []

    def get_problem_context(self, problem_id: str) -> dict:
        self.context_reads.append(problem_id)
        return deepcopy(self.contexts[problem_id])

    def get_asset_metadata(self, asset_id: str) -> dict:
        return {"asset_id": asset_id, "content_type": self.content_types[asset_id]}

    def get_problem_asset_target_context(
        self, problem_id: str, transformation_target_id: str
    ) -> dict:
        self.target_reads.append((problem_id, transformation_target_id))
        return {
            "problem_id": problem_id,
            "transformation_target_id": transformation_target_id,
        }

    def apply_problem_transformations(
        self, problem_id: str, transformations: list[dict]
    ) -> dict:
        self.writes.append(problem_id)
        self.contexts[problem_id] = _materialize(
            self.contexts[problem_id],
            SimpleNamespace(transformations=tuple(deepcopy(transformations))),
        )
        self.content_types[CONDITION_ASSET_ID] = "image/svg+xml"
        return {"problem_id": problem_id, "applied_count": len(transformations)}


def _target(problem_id: str, source_problem_id: str, order: int) -> ProblemTarget:
    return ProblemTarget(
        problem_id=problem_id,
        source_problem_id=source_problem_id,
        source_group_id="d50899c8-97e9-4f30-a76c-69f2e919f379",
        group_key="27718",
        problem_order_index=order,
    )


def test_targeted_manifest_reads_only_selected_child_and_not_parent() -> None:
    other = _context("not-selected", 6, 8, asset_id="other-jpeg", answer="5")
    gateway = _RuntimeGateway(
        {PARENT_ID: PARENT, CHILD_ID: REPAIR_CHILD, "not-selected": other},
        {
            CONDITION_ASSET_ID: "image/svg+xml",
            JPEG_ID: "image/jpeg",
            "other-jpeg": "image/jpeg",
        },
    )

    manifest = _content_rule_manifest(
        gateway,
        (_target(CHILD_ID, "60705", 1),),
        profile=get_group_profile("27718"),
        parent_asset_id=CONDITION_ASSET_ID,
        parent_solution_assets=(),
        parent_solution_html="parent template already audited",
        max_workers=1,
    )

    assert gateway.context_reads == [CHILD_ID]
    assert [record["source_problem_id"] for record in manifest["records"]] == ["60705"]
    assert manifest["records"][0]["status"] == "prepared"


def test_unsupported_record_gets_no_writes_while_real_child_continues(
    tmp_path,
) -> None:
    unsupported = deepcopy(REPAIR_CHILD)
    unsupported["problem_id"] = "unsupported"
    unsupported["normalized_content"]["sections"][0]["html"] = unsupported[
        "normalized_content"
    ]["sections"][0]["html"].replace("ромба", "квадрата")
    gateway = _RuntimeGateway(
        {"unsupported": unsupported, CHILD_ID: REPAIR_CHILD},
        {JPEG_ID: "image/jpeg"},
    )
    manifest = _content_rule_manifest(
        gateway,
        (
            _target("unsupported", "bad", 0),
            _target(CHILD_ID, "60705", 1),
        ),
        profile=get_group_profile("27718"),
        parent_asset_id=CONDITION_ASSET_ID,
        parent_solution_assets=(),
        max_workers=1,
    )

    assert [record["status"] for record in manifest["records"]] == [
        "blocked",
        "prepared",
    ]
    summary = apply_frozen_manifest(
        gateway,
        manifest,
        batch_size=1,
        max_workers=1,
        checkpoint_path=tmp_path / "apply-results.json",
    )

    assert gateway.writes == [CHILD_ID]
    assert gateway.target_reads == [(CHILD_ID, "asset:image_1")]
    assert summary["blocked_count"] == 1
    assert summary["applied_count"] == 1
    assert summary["failed_count"] == 0
    assert _plan(gateway.contexts[CHILD_ID], "image/svg+xml").transformations == ()

    fresh = _content_rule_manifest(
        gateway,
        (_target(CHILD_ID, "60705", 1),),
        profile=get_group_profile("27718"),
        parent_asset_id=CONDITION_ASSET_ID,
        parent_solution_assets=(),
        max_workers=1,
    )
    assert fresh["records"][0]["transformations"] == []
