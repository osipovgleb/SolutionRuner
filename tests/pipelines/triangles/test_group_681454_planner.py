"""Parent/child fixtures for the frozen 681454 bisector-angle grammar."""

import pytest

from solution_runner.pipelines.triangles.general.group_681454_planner import (
    RULE,
    build_repair_plan,
)
from solution_runner.pipelines.triangles.right.planner import (
    RightTrianglePlanError,
)


ASSET = "7d48c070-eedf-486d-8852-e04ea2d578f8"


def context(*, bad: int, acb: int, asset: str | None = ASSET) -> dict:
    assets = [] if asset is None else [
        {"asset_key": "image_1", "asset_id": asset, "kind": "ordinary_image"}
    ]
    return {
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": assets,
            "sections": [
                {
                    "key": "condition",
                    "html": (
                        "<p>В треугольнике ABC проведена биссектриса AD. "
                        f"Найдите угол ABD, если угол BAD равен {bad}°, "
                        f"а угол ACB равен {acb}°.</p>"
                    ),
                },
                {"key": "answer", "html": "<p>wrong</p>"},
                {"key": "solution", "html": "<p>compressed</p>"},
            ],
        }
    }


def exterior_angle_context(*, bad: int, c: int) -> dict:
    return {
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": [
                {"asset_key": "image_1", "asset_id": ASSET, "kind": "ordinary_image"}
            ],
            "sections": [
                {
                    "key": "condition",
                    "html": (
                        "<p>В треугольнике ABC угол C равен "
                        f"{c}°, AD — биссектриса, угол BAD равен {bad}°. "
                        "Найдите величину угла ADB. Ответ дайте в градусах.</p>"
                    ),
                },
                {"key": "answer", "html": "<p>wrong</p>"},
                {"key": "solution", "html": "<p>compressed</p>"},
            ],
        }
    }


@pytest.mark.parametrize(
    ("bad", "acb", "answer", "cab", "substitution"),
    [
        (29, 55, "67", r"\angle CAB=2\cdot\angle BAD=2\cdot 29^{\circ}=58^{\circ}", r"\angle ABD=180^{\circ}-58^{\circ}-55^{\circ}=67^{\circ}"),
        (18, 61, "83", r"\angle CAB=2\cdot\angle BAD=2\cdot 18^{\circ}=36^{\circ}", r"\angle ABD=180^{\circ}-36^{\circ}-61^{\circ}=83^{\circ}"),
    ],
)
def test_parent_and_child_keep_bisector_method_with_readable_adjacent_steps(
    bad, acb, answer, cab, substitution
):
    plan = build_repair_plan(
        context(bad=bad, acb=acb), parent_condition_asset_id=ASSET
    )
    solution = next(
        item
        for item in plan.transformations
        if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]

    assert plan.answer == answer
    assert RULE in solution
    assert cab in solution
    assert r"\angle ABD=180^{\circ}-\angle CAB-\angle ACB" in solution
    assert substitution in solution


def test_second_researched_child_uses_exterior_angle_method():
    plan = build_repair_plan(
        exterior_angle_context(bad=23, c=54), parent_condition_asset_id=ASSET
    )
    solution = next(
        item
        for item in plan.transformations
        if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]

    assert plan.answer == "77"
    assert r"\angle CAD=\angle BAD=23^{\circ}" in solution
    assert r"\angle ADB=\angle CAD+\angle ACD" in solution
    assert r"\angle ADB=23^{\circ}+54^{\circ}=77^{\circ}" in solution


def test_missing_parent_asset_is_added_and_unsupported_records_fail_closed():
    missing = build_repair_plan(
        context(bad=18, acb=61, asset=None), parent_condition_asset_id=ASSET
    )
    assert any(
        item["transformation_target_id"] == "asset:image_1"
        for item in missing.transformations
    )
    with pytest.raises(RightTrianglePlanError):
        build_repair_plan(
            context(bad=18, acb=61, asset="foreign"),
            parent_condition_asset_id=ASSET,
        )


def test_duplicate_assets_and_malformed_condition_fail_closed():
    duplicate = context(bad=18, acb=61)
    duplicate["normalized_content"]["assets"].append(
        {"asset_key": "image_2", "asset_id": ASSET, "kind": "ordinary_image"}
    )
    with pytest.raises(RightTrianglePlanError):
        build_repair_plan(duplicate, parent_condition_asset_id=ASSET)

    malformed = context(bad=18, acb=61)
    malformed["normalized_content"]["sections"][0]["html"] = (
        "<p>Найдите угол ABD.</p>"
    )
    with pytest.raises(RightTrianglePlanError):
        build_repair_plan(malformed, parent_condition_asset_id=ASSET)
