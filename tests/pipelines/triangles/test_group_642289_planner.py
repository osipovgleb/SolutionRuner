"""Contract tests for the bounded 642289 parent/child sine grammar."""

import pytest

from solution_runner.pipelines.triangles.right.group_642289_planner import (
    RULE,
    build_repair_plan,
)
from solution_runner.pipelines.triangles.right.planner import RightTrianglePlanError


ASSET = "8f8988bb-fa85-47a8-be0e-75edaf5a7604"


def context(*, ab: str, sine: str, angle: bool = False, asset: str | None = ASSET) -> dict:
    angle_part = r"\angle A" if angle else "A"
    assets = [] if asset is None else [{"asset_key": "image_1", "asset_id": asset, "kind": "ordinary_image"}]
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3,
        "assets": assets, "sections": [
            {"key": "condition", "html": f'<p>В треугольнике ABC угол C равен 90°, AB = {ab}, <span data-inline-latex="\\sin {angle_part}={sine}"></span>. Найдите BC.</p>'},
            {"key": "answer", "html": '<p><span data-effect="spaced">wrong</span></p>'},
            {"key": "solution", "html": "<p>too short</p>"},
        ]}}


@pytest.mark.parametrize(("ab", "sine", "angle", "answer", "substitution"), [
    ("45", "0{,}6", False, "27", r"BC=45\cdot0{,}6=27"),
    ("8", "0{,}75", True, "6", r"BC=8\cdot0{,}75=6"),
])
def test_parent_and_real_child_render_adjacent_readable_sine_steps(ab, sine, angle, answer, substitution):
    plan = build_repair_plan(context(ab=ab, sine=sine, angle=angle), parent_condition_asset_id=ASSET)
    solution = next(item for item in plan.transformations if item["transformation_target_id"] == "section:solution")["value"]["html"]
    assert plan.answer == answer
    assert RULE in solution
    assert r"\sin A=\frac{BC}{AB}" in solution
    assert r"BC=AB\cdot\sin A" in solution
    assert substitution in solution


def test_missing_asset_is_added_and_foreign_or_unsupported_records_fail_closed():
    missing = build_repair_plan(context(ab="8", sine="0{,}75", angle=True, asset=None), parent_condition_asset_id=ASSET)
    assert any(item["transformation_target_id"] == "asset:image_1" for item in missing.transformations)
    with pytest.raises(RightTrianglePlanError):
        build_repair_plan(context(ab="8", sine="1", asset="foreign"), parent_condition_asset_id=ASSET)
