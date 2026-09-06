import pytest

from solution_runner.pipelines.quadrilaterals.trapezoid.group_77152_planner import build_repair_plan
from solution_runner.pipelines.triangles.right.planner import RightTrianglePlanError


ASSET = "324c1800-e987-4e60-9cb7-f41cc3d0254c"


def context(a, b, sine):
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [{"asset_key": "image_1", "asset_id": ASSET}], "sections": [
        {"key": "condition", "html": f"<p>Основания равнобедренной трапеции равны {a} и {b}. Синус острого угла трапеции равен {sine}. Найдите боковую сторону.</p>"},
        {"key": "solution", "html": "<p>old</p>", "asset_keys": ["image_1"]}, {"key": "answer", "html": "<p>wrong</p>"}
    ]}}


@pytest.mark.parametrize(("a", "b", "sine", "answer"), [(6, 12, "0,8", "5"), (4, 16, "0,6", "7,5")])
def test_parent_and_child_render_explicit_cosine_steps(a, b, sine, answer):
    plan = build_repair_plan(context(a, b, sine), parent_condition_asset_id=ASSET)
    html = next(x for x in plan.transformations if x["transformation_target_id"] == "section:solution")["value"]["html"]
    assert plan.answer == answer
    assert r"AH=\frac" in html and r"\cos \angle BAD=\sqrt" in html and r"AB=\frac{AH}" in html


def test_unsupported_sine_fails_closed():
    with pytest.raises(RightTrianglePlanError):
        build_repair_plan(context(6, 12, "0,7"), parent_condition_asset_id=ASSET)
