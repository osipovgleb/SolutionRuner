"""Orthogonal projection independently validates every side-altitude source case."""

from copy import deepcopy
from functools import cache

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from isosceles_altitude_cases import CASES, GROUPS, model, section
from test_isosceles_basic_model import coordinates

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.triangles.isosceles.side_altitude_model import (
    RULES,
    read_question,
)

R = sp.Rational
PARAMETERS = {
    "27320": ("base", 8, "sin", R(1, 2)),
    "4833": ("base", 6, "sin", R(4, 5)),
    "4837": ("base", 6, "sin", R(3, 5)),
    "33199": ("base", 20, "sin", R(4, 5)),
    "27321": ("base", 5, "sin", R(7, 25)),
    "4835": ("base", 6, "sin", R(4, 5)),
    "33243": ("base", 12, "sin", sp.sqrt(51) / 10),
    "33245": ("base", 8, "sin", sp.sqrt(7) / 4),
    "27322": ("base", 5, "cos", R(7, 25)),
    "4839": ("base", 5, "cos", R(4, 5)),
    "33291": ("base", 25, "cos", R(3, 5)),
    "33293": ("base", 20, "cos", R(7, 25)),
    "27323": ("base", 8, "cos", R(1, 2)),
    "33341": ("base", 5, "cos", R(1, 5)),
    "33343": ("base", 14, "cos", R(1, 2)),
    "33345": ("base", 4, "cos", R(1, 2)),
    "27324": ("base", 7, "tg", 4 / sp.sqrt(33)),
    "33383": ("base", 22, "tg", sp.sqrt(3) / 3),
    "33385": ("base", R(68, 5), "tg", R(15, 8)),
    "33387": ("base", 9, "tg", sp.sqrt(20) / 5),
    "27325": ("base", 7, "tg", sp.sqrt(33) / 4),
    "33483": ("base", R(41, 2), "tg", R(9, 40)),
    "33485": ("base", R(3, 2), "tg", sp.sqrt(5) / 2),
    "33487": ("base", 16, "tg", sp.sqrt(7) / 3),
    "27326": ("side", 4 * sp.sqrt(15), "sin", R(1, 4)),
    "517192": ("side", 16 * sp.sqrt(15), "sin", R(1, 4)),
    "517230": ("side", 16 * sp.sqrt(7), "sin", R(3, 4)),
    "33581": ("side", 8 * sp.sqrt(7), "sin", R(3, 4)),
    "27327": ("side", 27, "sin", R(2, 3)),
    "33633": ("side", 12, "sin", R(1, 2)),
    "33635": ("side", 18, "sin", R(2, 3)),
    "33637": ("side", 72, "sin", R(1, 6)),
    "27328": ("side", 4 * sp.sqrt(15), "cos", R(1, 4)),
    "33661": ("side", 8 * sp.sqrt(7), "cos", R(3, 4)),
    "33663": ("side", 16 * sp.sqrt(15), "cos", R(1, 4)),
    "33665": ("side", 8 * sp.sqrt(15), "cos", R(1, 4)),
    "27329": ("side", 27, "cos", R(2, 3)),
    "33713": ("side", 30, "cos", R(2, 5)),
    "33715": ("side", 25, "cos", R(3, 5)),
    "33717": ("side", 10, "cos", R(4, 5)),
    "27330": ("base_height", 8, None, 4),
    "19307": ("base_height", 16, None, 4),
    "19309": ("base_height", 10, None, 8),
    "19311": ("base_height", 8, None, 6),
    "27331": ("base_height", 25, None, 20),
    "19351": ("base_height", 25, None, 24),
    "19353": ("base_height", 15, None, 9),
    "19355": ("base_height", 5, None, sp.sqrt(21)),
}


@cache
def projection_geometry(kind, length, function, value):
    if kind == "base_height":
        y = sp.symbols("y", positive=True)
        roots = sp.solve(
            length**2 * y * y - value**2 * (sp.Rational(length) ** 2 / 4 + y * y), y
        )
        roots = [r for r in roots if r.is_positive]
        assert len(roots) == 1
        x, y = sp.Rational(length, 2), roots[0]
    else:
        values = coordinates(kind, length, function, value)
        x, y = values["AH"], values["CH"]
    p, q, r = sp.Matrix([-x, 0]), sp.Matrix([x, 0]), sp.Matrix([0, y])
    v = r - q
    t = sp.simplify((p - q).dot(v) / v.dot(v))
    h = sp.simplify(q + t * v)
    height = sp.simplify(sp.sqrt((p - h).dot(p - h)))
    projection = sp.simplify(sp.sqrt((q - h).dot(q - h)))
    side = sp.simplify(sp.sqrt((r - p).dot(r - p)))
    return {
        "height": height,
        "projection": projection,
        "sin": sp.simplify(y / side),
        "cos": sp.simplify(x / side),
        "side": side,
        "foot_parameter": t,
    }


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_native_answer_and_foot_position_follow_orthogonal_projection(case):
    m = model(case)
    parameters = PARAMETERS[case["task"]]
    assert (
        m.given_kind == parameters[0]
        and sp.simplify(m.triangle.given_length - parameters[1]) == 0
    )
    if parameters[0] != "base_height":
        assert (
            m.triangle.function == parameters[2]
            and sp.simplify(m.triangle.function_value - parameters[3]) == 0
        )
    oracle = projection_geometry(*parameters)
    assert sp.simplify(m.answer - oracle[m.requested_kind]) == 0
    t = oracle["foot_parameter"]
    topology = 0 if t == 1 else 1 if (t - 1).is_positive else -1
    assert m.topology == topology
    saved = BeautifulSoup(
        section(case["context"], "answer")["html"], "html.parser"
    ).get_text(strip=True)
    assert sp.simplify(m.answer - sp.Rational(saved.replace(",", "."))) == 0
    assert GROUPS[case["group"]]["group_size"] >= 3


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_unreviewed_tail_is_not_ignored(case):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Удвойте ответ.</p>"
    with pytest.raises(ContentPlanError):
        model(case, ctx)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_old_answers_and_solutions_never_supply_missing_givens(case):
    ctx = deepcopy(case["context"])
    for key in ["solution", "answer"]:
        section(ctx, key)["html"] = "<p>Не использовать: 999.</p>"
    before = deepcopy(ctx)
    m = model(case, ctx)
    assert ctx == before and sp.simplify(m.answer - model(case).answer) == 0


@pytest.mark.parametrize("task", ["4837", "4839"])
def test_rotated_source_keeps_actual_ch_and_base_ac(task):
    m = model(next(c for c in CASES if c["task"] == task))
    assert (
        m.vertex,
        m.other_base_vertex,
        m.apex,
        m.height_segment,
        m.base_segment,
        m.given_angle,
    ) == ("C", "A", "B", "CH", "AC", "ACB")


@pytest.mark.parametrize("rule", list(RULES)[:10])
def test_coincident_height_foot_is_recognized_exactly(rule):
    kind, function, request = RULES[rule]
    value = r"\frac{\sqrt{2}}{2}" if function in {"sin", "cos"} else "1"
    given = "AC=BC=5" if kind == "side" else "AC=BC, AB=5"
    question = "высоту AH" if request == "height" else "BH"
    html = (
        "<p>В треугольнике ABC "
        + given
        + ", AH — высота, \\"
        + function
        + " BAC="
        + value
        + ". Найдите "
        + question
        + ".</p>"
    )
    m = read_question(html, "").require_rule(rule)
    assert (
        m.topology == 0
        and sp.simplify(m.height - m.triangle.side) == 0
        and sp.simplify(m.projection - m.triangle.side) == 0
    )


@pytest.mark.parametrize(
    "html",
    [
        r"<p>В треугольнике ABC AC=BC, AB=8, \sin ACB=0{,}5. Найдите высоту AH.</p>",
        r"<p>В треугольнике ABC AC=BC, AH — высота, AB=8, \sin BAC=0{,}5. Найдите CH.</p>",
        r"<p>В треугольнике ABC AC=BC, AB=8, \sin BAC=0{,}5. Найдите высоту CH.</p>",
        r"<p>В треугольнике ABC AC=BC, AB=8, высота AH равна 8. Найдите синус угла BAC.</p>",
        r"<p>В треугольнике ABC AC=BC, AB=8, высота AH равна 9. Найдите синус угла BAC.</p>",
        r"<p>В треугольнике ABC AC=BC, AB=8, \sin BAC=1. Найдите высоту AH.</p>",
    ],
)
def test_wrong_angle_wrong_altitude_and_degeneracy_fail_closed(html):
    with pytest.raises(ContentPlanError):
        read_question(html, "")
