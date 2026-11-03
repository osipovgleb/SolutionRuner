"""Polynomial coordinate constraints independently verify all source proof rows."""

import math
import re
from copy import deepcopy
from functools import cache

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from isosceles_basic_cases import CASES, GROUPS, model, parent_html, section
from right_triangle_geometry import numeric_formula

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.isosceles.basic_model import read_question
from solution_runner.pipelines.triangles.isosceles.basic_proofs import (
    render,
    review_parent,
)

R = sp.Rational
PARAMETERS = {
    "27284": ("side", 5, "sin", R(7, 25)),
    "4829": ("side", 5, "sin", R(4, 5)),
    "19979": ("side", 4, "sin", 3 * sp.sqrt(11) / 10),
    "19981": ("side", 25, "sin", 3 * sp.sqrt(11) / 10),
    "27285": ("base", R(48, 5), "sin", R(7, 25)),
    "19929": ("base", 30, "sin", R(4, 5)),
    "19931": ("base", 6, "sin", R(4, 5)),
    "19933": ("base", 14, "sin", R(24, 25)),
    "27286": ("side", 8, "cos", R(1, 2)),
    "4827": ("side", 5, "cos", R(3, 5)),
    "31707": ("side", 5, "cos", R(1, 5)),
    "31709": ("side", 14, "cos", R(1, 2)),
    "27287": ("base", 8, "cos", R(1, 2)),
    "31749": ("base", 32, "cos", R(4, 5)),
    "31751": ("base", 6, "cos", R(1, 4)),
    "31753": ("base", 28, "cos", R(7, 10)),
    "27288": ("side", 7, "tg", sp.sqrt(33) / 4),
    "31793": ("side", R(41, 2), "tg", R(9, 40)),
    "31797": ("side", 16, "tg", sp.sqrt(7) / 3),
    "31795": ("side", R(3, 2), "tg", sp.sqrt(5) / 2),
    "27289": ("base", 8, "tg", sp.sqrt(33) / 4),
    "31891": ("base", 22, "tg", sp.sqrt(3)),
    "31893": ("base", 24, "tg", R(8, 15)),
    "31895": ("base", 12, "tg", sp.sqrt(5) / 2),
}


@cache
def coordinates(kind, length, function, value):
    x, y = sp.symbols("x y", positive=True)
    norm2 = x * x + y * y
    length_constraint = norm2 - length**2 if kind == "side" else 2 * x - length
    ratio_constraint = {
        "sin": y * y - value**2 * norm2,
        "cos": x * x - value**2 * norm2,
        "tg": y * y - value**2 * x * x,
    }[function]
    roots = sp.solve((length_constraint, ratio_constraint), (x, y), dict=True)
    roots = [v for v in roots if v[x].is_positive and v[y].is_positive]
    assert len(roots) == 1
    x, y = roots[0][x], roots[0][y]
    side = sp.simplify(sp.sqrt(x * x + y * y))
    values = {"AB": 2 * x, "AC": side, "BC": side, "AH": x, "BH": x, "CH": y}
    values.update(
        sinA=y / side, cosA=x / side, tgA=y / x, sinB=y / side, cosB=x / side, tgB=y / x
    )
    # Cross product of CA and CB divided by their lengths gives sin C.
    values["sinC"] = sp.simplify(2 * x * y / (x * x + y * y))
    alpha = math.degrees(math.atan2(float(y), float(x)))
    values["angleA"] = values["angleB"] = alpha
    values["angleC"] = math.degrees(math.acos(float((y * y - x * x) / (x * x + y * y))))
    return values


def verify_rows(html, values):
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        raw = node["data-inline-latex"]
        text = raw
        for label in [r"\sin(2A)", r"\sin(2B)", r"\sin C"]:
            text = text.replace(label, "(" + sp.latex(values["sinC"]) + ")")
        has_angles = r"\angle" in text
        for name in "ABC":
            text = text.replace(
                r"\angle " + name, "(" + f"{values['angle' + name]:.6f}" + ")"
            )
        text = text.replace(r"^{\circ}", "")
        text = numeric_formula(text, values)
        numbers = [TrigonometricParser(p).parse().value for p in text.split("=")]
        assert len(numbers) >= 2
        if has_angles:
            assert all(abs(float(n - numbers[0])) < 2e-6 for n in numbers), raw
        else:
            assert all(sp.simplify(n - numbers[0]) == 0 for n in numbers), raw


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_complete_native_conditions_and_every_proof_row_follow_coordinates(case):
    m = model(case)
    kind, length, function, value = PARAMETERS[case["task"]]
    assert (m.given_kind, m.given_length, m.function) == (kind, length, function)
    assert sp.simplify(m.function_value - value) == 0
    oracle = coordinates(kind, length, function, value)
    assert sp.simplify(m.answer - oracle[m.requested]) == 0
    answer = BeautifulSoup(
        section(case["context"], "answer")["html"], "html.parser"
    ).get_text(strip=True)
    assert sp.simplify(m.answer - sp.Rational(answer.replace(",", "."))) == 0
    review_parent(parent_html(case["group"]), GROUPS[case["group"]]["rule"])
    html = render(m)
    verify_rows(html, oracle)
    titles = [
        s["data-solution-title"]
        for s in BeautifulSoup(html, "html.parser").select("section")
    ]
    assert titles == (
        [
            "Решение",
            "Альтернативное решение." if kind == "side" else "Приведем другое решение",
        ]
        if function == "cos"
        else ["Решение"]
    )
    if function == "cos":
        assert ("является равносторонним" in html) == (value == R(1, 2))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_extra_instructions_fail_closed(case):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Удвойте ответ.</p>"
    with pytest.raises(ContentPlanError):
        model(case, ctx)


@pytest.mark.parametrize("group", list(GROUPS))
def test_parent_method_changes_require_review(group):
    with pytest.raises(ContentPlanError):
        review_parent(
            parent_html(group) + "<p>Еще один способ.</p>", GROUPS[group]["rule"]
        )


@pytest.mark.parametrize(
    "group", ["27284", "27285", "27286", "27287", "27288", "27289"]
)
def test_equal_base_angles_allow_b_without_renaming_the_request(group):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    condition = section(ctx, "condition")
    condition["html"] = re.sub(r"(\\(?:sin|cos|tg)) A", r"\1 B", condition["html"])
    m = model(case, ctx)
    assert m.angle == "B"
    verify_rows(render(m), coordinates(*PARAMETERS[case["task"]]))


@pytest.mark.parametrize(
    "function,value", [("sin", "0"), ("sin", "1"), ("cos", "1.1"), ("tg", "0")]
)
def test_nonacute_and_degenerate_inputs_are_rejected(function, value):
    with pytest.raises((ContentPlanError, ValueError)):
        read_question(
            f"<p>В треугольнике ABC AC=BC=5, \\{function} A={value}. Найдите AB.</p>",
            "",
        )


def test_model_preserves_nonterminating_exact_answers_without_float_rounding():
    m = read_question(
        r"<p>В треугольнике ABC AC=BC=1, \cos A=\frac{1}{3}. Найдите AB.</p>", ""
    )
    assert m.answer == R(2, 3)
