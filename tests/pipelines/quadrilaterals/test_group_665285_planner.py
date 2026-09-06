"""Parent/child fixtures for the frozen 665285 parallelogram grammar."""

import pytest

from solution_runner.pipelines.quadrilaterals.parallelogram.group_665285_planner import (
    RULE,
    build_repair_plan,
)
from solution_runner.pipelines.triangles.right.planner import (
    RightTrianglePlanError,
)


ASSET = "f751e689-ec08-4bc6-9de7-d55c46285ba8"


def context(*, area: int, asset: str | None = ASSET) -> dict:
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
                        "<p>Площадь параллелограмма ABCD равна "
                        f"{area}. Точка E — середина стороны AD. "
                        "Найдите площадь трапеции BCDE.</p>"
                    ),
                },
                {"key": "answer", "html": "<p>wrong</p>"},
                {"key": "solution", "html": "<p>compressed</p>"},
            ],
        }
    }


@pytest.mark.parametrize(
    ("area", "answer", "substitution"),
    [
        (24, "18", r"S_{BCDE}=\frac{3}{4}\cdot 24=18"),
        (12, "9", r"S_{BCDE}=\frac{3}{4}\cdot 12=9"),
        (70, "52,5", r"S_{BCDE}=\frac{3}{4}\cdot 70=52{,}5"),
    ],
)
def test_parent_and_repair_child_expand_the_same_trapezoid_area_method(
    area, answer, substitution
):
    plan = build_repair_plan(context(area=area), parent_condition_asset_id=ASSET)
    solution = next(
        item
        for item in plan.transformations
        if item["transformation_target_id"] == "section:solution"
    )["value"]["html"]

    assert plan.answer == answer
    assert RULE in solution
    assert r"ED+BC=\frac{1}{2}AD+AD=\frac{3}{2}AD" in solution
    assert r"S_{BCDE}=\frac{ED+BC}{2}\cdot h" in solution
    assert substitution in solution


def test_asset_handling_and_unsupported_conditions_fail_closed():
    missing = build_repair_plan(context(area=12, asset=None), parent_condition_asset_id=ASSET)
    assert any(
        item["transformation_target_id"] == "asset:image_1"
        for item in missing.transformations
    )
    with pytest.raises(RightTrianglePlanError):
        build_repair_plan(context(area=12, asset="foreign"), parent_condition_asset_id=ASSET)
    with pytest.raises(RightTrianglePlanError):
        build_repair_plan(context(area=0), parent_condition_asset_id=ASSET)
