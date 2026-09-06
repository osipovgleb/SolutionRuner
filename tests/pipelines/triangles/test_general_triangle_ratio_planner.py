"""Strict group-27752 planner coverage using only parent and one repair child."""

from __future__ import annotations

from copy import deepcopy

import pytest

from solution_runner.pipelines.triangles.general.ratio_planner import (
    CONDITION_ASSET_ALT,
    CONDITION_ASSET_ID,
    CONDITION_ASSET_SHA256,
    RULE,
    build_repair_plan,
)
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.triangles.right.planner import (
    RightTrianglePlanError,
)
from solution_runner.pipelines.triangles.right.runtime import (
    _pinned_condition_asset_id,
)


PARENT = {
    "problem_id": "11a2a614-4daf-412f-b03a-f33eab3e7e11",
    "normalized_content": {
        "format": "teacherhelper-normalized",
        "schema_version": 3,
        "assets": [],
        "sections": [
            {
                "key": "condition",
                "section_id": "condition:1",
                "transformation_target_id": "section:condition:1",
                "title": "Условие",
                "asset_keys": [],
                "html": (
                    "<p>Углы тре­уголь­ни­ка от­но­сят­ся как 2 : 3 : 4. "
                    "Най­ди­те мень­ший из них. Ответ дайте в гра­ду­сах.</p>"
                ),
            },
            {
                "key": "answer",
                "section_id": "answer:1",
                "transformation_target_id": "section:answer:1",
                "title": "Ответ",
                "asset_keys": [],
                "html": '<p><span data-effect="spaced">40</span></p>',
            },
            {
                "key": "solution",
                "section_id": "solution:1",
                "transformation_target_id": "section:solution:1",
                "title": "Решение",
                "asset_keys": [],
                "html": "<p>Старое решение без LaTeX.</p>",
            },
        ],
    },
}

REPAIR_CHILD = {
    "problem_id": "6e5c52ee-6b02-4faf-a14f-e2bf0d74bb37",
    "normalized_content": {
        "format": "teacherhelper-normalized",
        "schema_version": 3,
        "assets": [],
        "sections": [
            {
                "key": "condition",
                "section_id": "condition:1",
                "transformation_target_id": "section:condition:1",
                "title": "Условие",
                "asset_keys": [],
                "html": (
                    '<p>Углы тре­уголь­ни­ка от­но­сят­ся как '
                    '<span data-inline-latex="3\\colon 13\\colon 14"></span>. '
                    "Най­ди­те мень­ший из них. Ответ дайте в гра­ду­сах.</p>"
                ),
            },
            {
                "key": "answer",
                "section_id": "answer:1",
                "transformation_target_id": "section:answer:1",
                "title": "Ответ",
                "asset_keys": [],
                "html": '<p><span data-effect="spaced">18</span></p>',
            },
        ],
    },
}


def _section(context: dict, key: str) -> dict:
    return next(
        section
        for section in context["normalized_content"]["sections"]
        if section["key"] == key
    )


def _plan(context: dict):
    return build_repair_plan(
        context,
        parent_condition_asset_id=CONDITION_ASSET_ID,
    )


def _transformation(plan, key: str) -> dict:
    return next(
        item for item in plan.transformations if key in item["transformation_target_id"]
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
            ]
            condition = _section(result, "condition")
            condition["asset_keys"] = ["image_1"]
            condition["html"] += value["html"].replace(
                " data-asset-key=",
                ' data-transformation-target-id="asset:image_1" data-asset-key=',
            )
            continue
        key = target.split(":")[1]
        current = next(
            (section for section in content["sections"] if section["key"] == key),
            None,
        )
        if current is None:
            content["sections"].append(
                {
                    "key": key,
                    "section_id": f"{key}:1",
                    "transformation_target_id": f"section:{key}:1",
                    **value,
                }
            )
        else:
            current.update(value)
    return result


def test_group_27752_profile_pins_scope_rule_and_shared_svg() -> None:
    profile = get_group_profile("27752")

    assert profile.source_group_id == "d79679bf-ed11-4924-bc43-84ff8c2bb900"
    assert profile.group_order_index == 4
    assert profile.content_rule_key == RULE
    assert profile.existing_solution_policy == "rewrite"
    assert profile.condition_asset_id == CONDITION_ASSET_ID
    assert profile.condition_asset_sha256 == CONDITION_ASSET_SHA256


@pytest.mark.parametrize(
    ("context", "answer", "formula", "last_formula"),
    [
        (
            PARENT,
            "40",
            r"2x+3x+4x=180^{\circ}\iff 9x=180^{\circ}\iff x=20^{\circ}",
            r"2x=2\cdot20^{\circ}=40^{\circ}",
        ),
        (
            REPAIR_CHILD,
            "18",
            r"3x+13x+14x=180^{\circ}\iff 30x=180^{\circ}\iff x=6^{\circ}",
            r"3x=3\cdot6^{\circ}=18^{\circ}",
        ),
    ],
)
def test_parent_and_real_repair_child_receive_adapted_latex_solution(
    context: dict, answer: str, formula: str, last_formula: str
) -> None:
    plan = _plan(deepcopy(context))
    solution = _transformation(plan, "solution")["value"]["html"]

    assert plan.answer == answer
    assert formula in solution
    assert last_formula in solution
    assert solution.count("<p>") == 4
    assert "<p>Следовательно,</p>" in solution
    assert "Наименьшему коэффициенту" not in solution
    assert "Ответ:" not in solution
    assert _transformation(plan, "asset:image_1")["value"]["asset_id"] == CONDITION_ASSET_ID


@pytest.mark.parametrize("stored", [None, "", "<p>-</p>", "<p>999</p>"])
def test_missing_malformed_or_wrong_answer_is_repaired(stored: str | None) -> None:
    context = deepcopy(REPAIR_CHILD)
    answer = _section(context, "answer")
    if stored is None:
        context["normalized_content"]["sections"].remove(answer)
    else:
        answer["html"] = stored

    transformation = _transformation(_plan(context), "answer")
    assert transformation["value"]["html"] == (
        '<p><span data-effect="spaced">18</span></p>'
    )


@pytest.mark.parametrize(
    "bad_html",
    [
        "<p>Углы треугольника относятся как 0 : 3 : 4. Найдите меньший из них. Ответ дайте в градусах.</p>",
        "<p>Углы треугольника относятся как 2 : 3 : 4. Найдите больший из них. Ответ дайте в градусах.</p>",
        "<p style=\"display:none\">Углы треугольника относятся как 2 : 3 : 4. Найдите меньший из них. Ответ дайте в градусах.</p>",
        "<p>Углы треугольника относятся как 2 : 3 : 6. Найдите меньший из них. Ответ дайте в градусах.</p>",
    ],
)
def test_unknown_condition_forms_fail_closed(bad_html: str) -> None:
    context = deepcopy(PARENT)
    _section(context, "condition")["html"] = bad_html

    with pytest.raises(RightTrianglePlanError):
        _plan(context)


def test_foreign_or_duplicate_condition_assets_fail_closed() -> None:
    for assets in (
        [{"asset_key": "image_1", "asset_id": "foreign", "kind": "ordinary_image"}],
        [
            {"asset_key": "image_1", "asset_id": CONDITION_ASSET_ID, "kind": "ordinary_image"},
            {"asset_key": "image_2", "asset_id": "foreign", "kind": "ordinary_image"},
        ],
    ):
        context = deepcopy(PARENT)
        context["normalized_content"]["assets"] = assets
        with pytest.raises(RightTrianglePlanError):
            _plan(context)


def test_foreign_materialized_image_markup_fails_closed() -> None:
    context = deepcopy(PARENT)
    condition = _section(context, "condition")
    condition["html"] += (
        '<center><img alt="" data-asset-id="foreign" '
        'data-asset-key="image_1" src="/assets/foreign"/></center>'
    )

    with pytest.raises(RightTrianglePlanError):
        _plan(context)


def test_materialized_readback_has_no_second_plan() -> None:
    initial = deepcopy(REPAIR_CHILD)
    materialized = _materialize(initial, _plan(initial))

    assert _plan(materialized).transformations == ()


class _AssetGateway:
    def get_source_asset(self, source_asset_id: str) -> dict:
        assert source_asset_id == CONDITION_ASSET_ID
        return {
            "source_asset": {
                "source_asset_id": CONDITION_ASSET_ID,
                "sha256": CONDITION_ASSET_SHA256,
                "content_type": "image/svg+xml",
            }
        }


def test_pinned_source_asset_requires_exact_remote_readback() -> None:
    profile = get_group_profile("27752")
    assert _pinned_condition_asset_id(_AssetGateway(), profile) == CONDITION_ASSET_ID
