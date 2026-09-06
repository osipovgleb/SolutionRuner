"""Strict group-27707 coverage from the parent and one real repair child."""

from __future__ import annotations

from copy import deepcopy

import pytest

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.triangles.right.planner import (
    RightTrianglePlanError,
)
from solution_runner.pipelines.vectors.rectangle_diagonal_planner import (
    CONDITION_ASSET_ID,
    CONDITION_ASSET_SHA256,
    RULE,
    build_repair_plan,
)


PARENT_ID = "a9cfd690-0933-40aa-b48c-044b8ac52a18"
CHILD_ID = "652e12b3-534e-48f1-8b9e-692f8a22cdd1"


def _condition_html(a: int, b: int, asset_id: str | None = None) -> str:
    image = (
        f'<img alt="" data-asset-id="{asset_id}" data-asset-key="image_1" '
        f'data-transformation-target-id="asset:image_1" '
        f'src="/assets/{asset_id}"/>'
        if asset_id
        else ""
    )
    return (
        f"<p>{image}Две сто­ро­ны пря­мо­уголь­ни­ка <i>ABCD</i> равны "
        f"{a} и {b}. Най­ди­те длину век­то­ра "
        '<span data-inline-latex="\\overrightarrow{AC}"></span>.</p>'
    )


def _solution_html(a: int, b: int, answer: int) -> str:
    square_sum = a * a + b * b
    return (
        '<p>Век­тор  <span data-inline-latex="\\overrightarrow{AC}"></span> '
        'яв­ля­ет­ся диа­го­на­лью пря­мо­уголь­ни­ка. По тео­ре­ме '
        'Пи­фа­го­ра из тре­уголь­ни­ка '
        '<var data-math-identifier="ADC">ADC</var> по­лу­ча­ем:</p>'
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
    sections = [
        {
            "key": "condition",
            "section_id": "condition:1",
            "transformation_target_id": "section:condition:1",
            "title": "Условие",
            "asset_keys": ["image_1"] if asset_id else [],
            "html": _condition_html(a, b, asset_id),
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


PARENT = _context(
    PARENT_ID,
    6,
    8,
    asset_id=CONDITION_ASSET_ID,
    answer="10",
    solution=_solution_html(6, 8, 10),
)
REPAIR_CHILD = _context(CHILD_ID, 15, 20, asset_id=None, answer="25")


def _plan(context: dict, content_type: str | None):
    return build_repair_plan(
        context,
        parent_condition_asset_id=CONDITION_ASSET_ID,
        current_asset_content_type=content_type,
    )


def _targets(plan) -> dict[str, dict]:
    return {
        item["transformation_target_id"]: item for item in plan.transformations
    }


def _find(plan, prefix: str) -> dict:
    return next(
        item
        for item in plan.transformations
        if item["transformation_target_id"].startswith(prefix)
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
            image = value["html"].replace(
                " data-asset-key=",
                ' data-transformation-target-id="asset:image_1" data-asset-key=',
            )
            if "<img" in condition["html"]:
                start = condition["html"].find("<img")
                end = condition["html"].find("/>", start) + 2
                condition["html"] = condition["html"][:start] + image + condition["html"][end:]
            else:
                condition["html"] = condition["html"].replace("<p>", f"<p>{image}", 1)
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


def test_profile_pins_group_scope_rule_and_svg() -> None:
    profile = get_group_profile("27707")

    assert profile.source_group_id == "f60e3532-b35b-4da1-abd1-c2a5031c58cd"
    assert profile.group_order_index == 2
    assert profile.category_key == "2"
    assert profile.snapshot_theme_id == "64fdf550-dcad-489a-aea5-0682edf81d76"
    assert profile.content_rule_key == RULE
    assert profile.condition_asset_id == CONDITION_ASSET_ID
    assert profile.condition_asset_sha256 == CONDITION_ASSET_SHA256
    assert profile.existing_solution_policy == "rewrite"


def test_parent_is_complete_and_real_child_gets_adapted_solution() -> None:
    assert _plan(deepcopy(PARENT), "image/svg+xml").transformations == ()

    plan = _plan(deepcopy(REPAIR_CHILD), None)
    solution = _targets(plan)["section:solution"]["value"]["html"]
    assert plan.answer == "25"
    assert r"AC=\sqrt{15^{2}+20^{2}}=\sqrt{625}=25" in solution
    assert r"AC=\sqrt{6^{2}+8^{2}}" not in solution
    assert [item["transformation_target_id"] for item in plan.transformations] == [
        "asset:image_1",
        "section:solution",
    ]
    assert _targets(plan)["asset:image_1"]["operation"] == "add"


@pytest.mark.parametrize("content_type", ["image/png", "image/jpeg"])
def test_existing_raster_is_rewritten_to_parent_svg(content_type: str) -> None:
    context = _context("raster", 9, 12, asset_id="raster-id", answer="15")

    asset = _targets(_plan(context, content_type))["asset:image_1"]
    assert asset["operation"] == "rewrite"
    assert asset["value"]["asset_id"] == CONDITION_ASSET_ID


@pytest.mark.parametrize("stored", [None, "", "-", "24", "25,1"])
def test_missing_malformed_and_wrong_answer_is_repaired(stored: str | None) -> None:
    context = _context("answer", 15, 20, asset_id=None, answer=stored)

    answer = _find(_plan(context, None), "section:answer")["value"]["html"]
    assert answer == '<p><span data-effect="spaced">25</span></p>'


@pytest.mark.parametrize(
    "html",
    [
        _condition_html(5, 5),
        _condition_html(15, 20).replace("Две", "Три", 1),
        _condition_html(15, 20).replace(
            r"\overrightarrow{AC}", r"\overrightarrow{BD}"
        ),
        _condition_html(15, 20).replace("<p>", '<p class="hidden">'),
    ],
)
def test_unsupported_conditions_fail_closed(html: str) -> None:
    context = deepcopy(REPAIR_CHILD)
    context["normalized_content"]["sections"][0]["html"] = html

    with pytest.raises(RightTrianglePlanError):
        _plan(context, None)


def test_foreign_svg_and_duplicate_assets_fail_closed() -> None:
    foreign = _context("foreign", 9, 12, asset_id="foreign-svg", answer="15")
    duplicate = deepcopy(PARENT)
    duplicate["normalized_content"]["assets"].append(
        {
            "asset_key": "image_2",
            "asset_id": "duplicate",
            "url": "/assets/duplicate",
            "kind": "ordinary_image",
            "alt": "",
        }
    )

    with pytest.raises(RightTrianglePlanError):
        _plan(foreign, "image/svg+xml")
    with pytest.raises(RightTrianglePlanError):
        _plan(duplicate, None)


def test_fresh_materialized_readback_has_no_repairs() -> None:
    materialized = _materialize(REPAIR_CHILD, _plan(REPAIR_CHILD, None))

    assert _plan(materialized, "image/svg+xml").transformations == ()
