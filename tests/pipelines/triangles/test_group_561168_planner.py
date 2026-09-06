"""Parent/child fixtures for the frozen 561168 included-angle grammar."""

import pytest

from solution_runner.pipelines.triangles.general.group_561168_planner import build_repair_plan
from solution_runner.pipelines.triangles.right.planner import RightTrianglePlanError

ASSET = "9d51c5c1-515e-42a1-aeee-9c7f22e06543"


def context(*, ab: int, bc: int, area: str, answer: str = "wrong") -> dict:
    area_html = area.replace("{,}", ",") if "\\" not in area else f'<span data-inline-latex="{area}"></span>'
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3,
        "assets": [{"asset_key": "image_1", "asset_id": ASSET, "kind": "ordinary_image"}],
        "sections": [
            {"key": "condition", "html": f'<p>В треугольнике ABC угол B — тупой, AB = {ab}, BC = {bc}. Найдите величину угла, противолежащего стороне AC, если площадь треугольника равна {area_html}. Ответ дайте в градусах.</p>'},
            {"key": "answer", "html": f'<p><span data-effect="spaced">{answer}</span></p>'},
            {"key": "solution", "html": "<p>compressed</p>"},
        ]}}


@pytest.mark.parametrize(("ab", "bc", "area", "answer", "sine", "angle"), [
    (5, 6, "7{,}5", "150", r"\frac{1}{2}", r"150^{\circ}"),
    (7, 8, r"14\sqrt{3}", "120", r"\frac{\sqrt{3}}{2}", r"120^{\circ}"),
])
def test_parent_and_child_keep_area_method_but_expand_adjacent_steps(ab, bc, area, answer, sine, angle):
    plan = build_repair_plan(context(ab=ab, bc=bc, area=area), parent_condition_asset_id=ASSET)
    html = next(x for x in plan.transformations if x["transformation_target_id"] == "section:solution")["value"]["html"]
    assert plan.answer == answer
    assert r"S=\frac{1}{2}\cdot AB\cdot BC\cdot\sin \angle B" in html
    assert r"\sin \angle B=\frac{2S}{AB\cdot BC}" in html
    assert sine in html and angle in html


def test_unregistered_sine_value_fails_before_any_transformations():
    with pytest.raises(RightTrianglePlanError):
        build_repair_plan(context(ab=4, bc=5, area="4"), parent_condition_asset_id=ASSET)
