"""Native proofs, explicit ratios, scaling and genuine non-rhombus sections."""

import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from prism_oblique_geometry_oracle import verify
from prism_oblique_source_cases import CASES, plan

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.distance_figures import selection
from solution_runner.pipelines.solids.spatial_distance_model import condition_text

EXPECTED = {
    "676903": 2 * sp.sqrt(11),
    "677087": 2 * sp.sqrt(23),
    "681580": 2 * sp.sqrt(11),
    "681165": 6 * sp.sqrt(30),
    "681166": 250 * sp.sqrt(3) / 3,
    "681296": 4,
    "694819": 125 * sp.sqrt(267) / 2,
    "501752": sp.sqrt(4209),
    "501885": sp.sqrt(133),
    "503147": sp.sqrt(133),
    "502314": sp.sqrt(1281),
    "634951": sp.Rational(9, 16),
    "647136": sp.Rational(25, 144),
    "647156": sp.Rational(64, 225),
}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_equations_answers_and_idempotency_without_input_mutation(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    m = selection(ctx)[0]
    assert sp.simplify(m.answer - EXPECTED[case["task"]]) == 0
    assert sp.simplify(verify(solution_html(result), m) - m.answer) == 0
    plain = BeautifulSoup(solution_html(result), "html.parser").get_text()
    assert all(token not in plain for token in (r"\frac", r"\sqrt", "{,}"))
    assert ctx == case["context"]
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations
    for key in ("condition", "criteria", "source"):
        assert section(ctx, key) == section(case["context"], key)
    assert section(ctx, "answer")["asset_keys"] == []
    if m.mode == "box_diagonal_bisector_ratio":
        p, q = m.answer.as_numer_denom()
        assert result.answer == str(p) + ":" + str(q) + r"\text{, считая от }A_1"
        assert r"\frac{B_1T}{TA_1}" in solution_html(result)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_unknown_requirements_and_parent_pin_drift_refuse(case):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Найдите также объём.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_html="changed")


def scaled(raw, m, factor):
    g = dict(m.given)

    def val(key, power=1):
        return sp.latex(g[key] * factor**power)

    if m.mode == "triangle_prism_oblique_height":
        if "сторона AB основания равна" in raw:
            raw = re.sub(
                r"(сторона AB основания равна ).+?,",
                lambda a: a[1] + val("a") + ",",
                raw,
                count=1,
            )
        else:
            raw = re.sub(
                r"AB\s*=\s*.+?\.", lambda _: "AB=" + val("a") + ".", raw, count=1
            )
        return re.sub(
            r"(площадь сечения(?: плоскостью α)? равна ).+?\.$",
            lambda a: a[1] + val("area", 2) + ".",
            raw,
        )
    if m.mode == "triangle_prism_perpendicular_area":
        return re.sub(
            r"(все ребра призмы равны ).+?\.$", lambda a: a[1] + val("a") + ".", raw
        )
    if m.mode == "triangle_prism_perpendicular_height":
        return re.sub(
            r"(площадь сечения призмы ABCA_1B_1C_1 плоскостью α равна ).+?\.$",
            lambda a: a[1] + val("area", 2) + ".",
            raw,
        )
    for label, key in (
        ("AB", "a"),
        ("BC" if m.mode == "box_diagonal_bisector_ratio" else "AD", "b"),
        ("AA_1", "height"),
    ):
        raw = re.sub(
            r"\b" + label + r"\s*=\s*.+?(?=,| и |\.)",
            lambda _, l=label, k=key: l + "=" + val(k),
            raw,
            count=1,
        )
    return raw


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("factor", (sp.Rational(3, 2), 3))
def test_changed_measurements_scale_and_every_proof_step_is_geometric(case, factor):
    ctx = deepcopy(case["context"])
    m = selection(ctx)[0]
    raw = condition_text(section(ctx, "condition")["html"], None)
    changed = scaled(raw, m, factor)
    assert changed != raw
    section(ctx, "condition")["html"] = "<p>" + changed + "</p>"
    result = plan(case, ctx)
    new = selection(ctx)[0]
    assert sp.simplify(verify(solution_html(result), new) - new.answer) == 0
    plain = BeautifulSoup(solution_html(result), "html.parser").get_text()
    assert all(token not in plain for token in (r"\frac", r"\sqrt", "{,}"))
    exponent = (
        0
        if new.mode == "box_diagonal_bisector_ratio"
        else 1
        if new.mode.endswith("height")
        else 2
    )
    assert sp.simplify(new.answer - factor**exponent * m.answer) == 0


@pytest.mark.parametrize(
    "task,old,new",
    (
        ("676903", "середина ребра CC_1", "середина ребра BC"),
        ("676903", "площадь сечения равна 6", r"площадь сечения равна \sqrt{3}"),
        ("681165", "AM = 5 MA_1", "AM = 5 AM"),
        ("681165", "перпендикулярно плоскости ABB_1", "параллельно плоскости ABB_1"),
        ("681296", "делит ребро A_1B_1 пополам", "делит ребро A_1C_1 пополам"),
        ("501885", "AB = 3", "AB = 4"),
        ("501752", "считая от вершины D", "считая от вершины A"),
        ("501752", "1: 4", "0: 4"),
        ("634951", "AB = 5", "AB = 6"),
        ("647136", "середину M диагонали AC_1", "середину M диагонали BD_1"),
    ),
)
def test_false_claims_degenerate_sections_and_changed_incidence_refuse(task, old, new):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    assert old in raw
    section(ctx, "condition")["html"] = "<p>" + raw.replace(old, new) + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "task,old,new", (("501752", "AB = 8", "AB = 9"), ("503147", "AB = 3", "AB = 4"))
)
def test_valid_non_rhombus_parallelograms_have_general_diagonal_area(task, old, new):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    assert old in raw
    section(ctx, "condition")["html"] = "<p>" + raw.replace(old, new) + "</p>"
    m = selection(ctx)[0]
    assert not m.q["rhombus"]
    result = plan(case, ctx)
    html = solution_html(result)
    assert sp.simplify(verify(html, m) - m.answer) == 0
    assert r"\cos\varphi" in html and "является ромбом" not in html
    replay(ctx, result.transformations)
    assert (
        len(ctx["normalized_content"]["assets"]) == 1
        and not plan(case, ctx).transformations
    )


def test_reverse_midpoint_is_proved_before_using_it_and_parent_methods_remain():
    case = next(c for c in CASES if c["task"] == "681296")
    html = solution_html(plan(case))
    assert (
        html.index("Обозначим середину")
        < html.index("K принадлежит")
        < html.index("Обозначим общее ребро")
    )
    assert "Метод координат" in html and "Начало координат выберем в A" in html


def test_coordinate_inverse_uses_a_candidate_plane_and_geometry_justifies_right_angle():
    reverse = next(c for c in CASES if c["task"] == "681296")
    html = solution_html(plan(reverse))
    assert html.index("вспомогательную плоскость β") < html.index("β совпадает с α")
    assert r"\vec n_{\beta}" in html
    normal = next(c for c in CASES if c["task"] == "634951")
    html = solution_html(plan(normal))
    assert (
        html.index("проекция катета A₁D₁")
        < html.index("угол A₁KD₁ прямой")
        < html.index("KD_1=\\sqrt")
    )
