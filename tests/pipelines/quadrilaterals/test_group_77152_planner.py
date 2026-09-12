import pytest

from solution_runner.pipelines.quadrilaterals.trapezoid.group_77152_planner import (
    CONDITION_ASSET_ID,
    CONDITION_ASSET_KEY,
    build_repair_plan,
)
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.triangles.right.planner import RightTrianglePlanError


ASSET = "324c1800-e987-4e60-9cb7-f41cc3d0254c"
ASSET_SHA256 = "7a40fc7067bd9d2358cd717894f3eb0a62ecb4b3dd573278137f2f58c863236d"


def context(a, b, sine):
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [{"asset_key": "image_1", "asset_id": ASSET}], "sections": [
        {"key": "condition", "html": f"<p>Основания равнобедренной трапеции равны {a} и {b}. Синус острого угла трапеции равен {sine}. Найдите боковую сторону.</p>"},
        {"key": "solution", "html": "<p>old</p>", "asset_keys": ["image_1"]}, {"key": "answer", "html": "<p>wrong</p>"}
    ]}}


@pytest.mark.parametrize(("a", "b", "sine", "answer"), [(6, 12, "0,8", "5"), (4, 16, "0,6", "7,5")])
def test_parent_and_child_render_explicit_cosine_steps(a, b, sine, answer):
    plan = build_repair_plan(context(a, b, sine), parent_condition_asset_id=ASSET)
    solution = next(x for x in plan.transformations if x["transformation_target_id"] == "section:solution")["value"]
    condition_asset = next(x for x in plan.transformations if x["transformation_target_id"] == f"asset:{CONDITION_ASSET_KEY}")["value"]
    assert plan.answer == answer
    assert r"AH=\frac" in solution["html"] and r"\cos \angle BAD=\sqrt" in solution["html"] and r"AB=\frac{AH}" in solution["html"]
    assert solution["asset_keys"] == ["image_1"]
    assert condition_asset["parent_target_id"] == "section:condition:1"
    assert condition_asset["asset_id"] == CONDITION_ASSET_ID


def test_existing_solution_asset_is_not_moved_or_removed():
    current = context(6, 12, "0,8")
    solution = current["normalized_content"]["sections"][1]
    solution["html"] = (
        '<section data-content-kind="solution" data-content-rule="trapezoid-77152-isosceles-leg-from-sine" '
        'data-solution-title="Решение"><p>Проведём высоты трапеции. В равнобедренной трапеции отрезок у каждого края равен половине разности оснований:</p>'
        '<center><p><span data-inline-latex="AH=\\frac{|6-12|}{2}=\\frac{6}{2}"></span>.</p></center>'
        '<p>Из прямоугольного треугольника найдём косинус острого угла:</p>'
        '<center><p><span data-inline-latex="\\cos \\angle BAD=\\sqrt{1-\\sin^2 \\angle BAD}=\\sqrt{1-0{,}8^2}=0{,}6"></span>.</p></center>'
        '<p>Тогда боковая сторона равна:</p>'
        '<center><p><span data-inline-latex="AB=\\frac{AH}{\\cos \\angle BAD}=\\frac{6}{2\\cdot 0{,}6}=5"></span>.</p></center></section>'
        f'<img alt="" data-asset-id="{ASSET}" data-asset-key="image_1" data-transformation-target-id="asset:image_1" src="/assets/{ASSET}"/>'
    )
    plan = build_repair_plan(current, parent_condition_asset_id=ASSET)
    assert all(item["transformation_target_id"] != "section:solution" for item in plan.transformations)
    assert any(item["transformation_target_id"] == f"asset:{CONDITION_ASSET_KEY}" for item in plan.transformations)


def test_unsupported_sine_fails_closed():
    with pytest.raises(RightTrianglePlanError):
        build_repair_plan(context(6, 12, "0,7"), parent_condition_asset_id=ASSET)


def test_profile_pins_the_shared_trapezoid_asset():
    profile = get_group_profile("77152")
    assert profile.condition_asset_id == ASSET
    assert profile.condition_asset_sha256 == ASSET_SHA256
