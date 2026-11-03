"""Coordinate projections independently validate 30/60-degree source methods."""

import gzip
import hashlib
import re
from copy import deepcopy
from functools import cache
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from degree_source_cases import (
    CASES,
    DATA,
    GROUPS,
    parent_html,
    plan,
    section,
    solution_html,
)
from right_triangle_geometry import numeric_formula

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.right import degree_parent

PARAMETERS = {
    "27789": (30, 2 * sp.sqrt(3)),
    "4799": (60, 2 * sp.sqrt(3)),
    "48519": (30, 80 * sp.sqrt(3)),
    "48521": (30, 10 * sp.sqrt(3)),
    "27790": (30, 2),
    "48569": (30, 86),
    "48571": (30, 72),
    "48573": (30, 60),
    "27791": (30, 4),
    "4797": (30, 4),
    "4801": (60, 12),
    "48619": (30, 30),
}
REQUESTS = {"27789": "CH", "27790": "AH", "27791": "BH"}


@cache
def coordinate_values(angle, length):
    x, y = sp.symbols("x y", positive=True)
    roots = sp.solve(
        (x * x + y * y - length**2, y - sp.tan(sp.pi * angle / 180) * x),
        (x, y),
        dict=True,
    )
    assert len(roots) == 1
    a = sp.Matrix([0, 0])
    b = sp.Matrix([roots[0][x], roots[0][y]])
    c = sp.Matrix([roots[0][x], 0])
    h = sp.simplify(c.dot(b) / b.dot(b)) * b
    points = {"A": a, "B": b, "C": c, "H": h}
    values = {
        key: sp.simplify(
            sp.sqrt(
                (points[key[0]] - points[key[1]]).dot(points[key[0]] - points[key[1]])
            )
        )
        for key in ("AB", "AC", "BC", "AH", "BH", "CH")
    }
    values.update(
        sinA=values["BC"] / values["AB"],
        cosA=values["AC"] / values["AB"],
        tgA=values["BC"] / values["AC"],
    )
    return values


def check_equalities(html, values):
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        for statement in re.split(r"\\iff|\\Longrightarrow", node["data-inline-latex"]):
            parts = statement.split("=")
            assert len(parts) >= 2
            numbers = [
                TrigonometricParser(numeric_formula(part, values)).parse().value
                for part in parts
            ]
            assert all(sp.simplify(n - numbers[0]) == 0 for n in numbers), statement


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_existing_binding_preserves_parent_methods_and_rewrites_stale_solutions(group):
    p = get_group_profile(group["key"])
    assert p.source_group_id == group["group_uuid"] and group["group_size"] >= 3
    assert (
        p.existing_solution_policy == "rewrite" and p.content_rule_key == group["rule"]
    )
    assert ("parent_solution_html", "parent_solution_html") in get_handler(
        group["rule"]
    ).inputs


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answer_and_every_equation_follow_coordinate_projection(case):
    values = coordinate_values(*PARAMETERS[case["task"]])
    result = plan(case)
    assert (
        sp.Rational(result.answer.replace(",", ".")) == values[REQUESTS[case["group"]]]
    )
    saved = (
        BeautifulSoup(section(case["context"], "answer")["html"], "html.parser")
        .get_text("", strip=True)
        .removesuffix(".")
    )
    assert sp.Rational(saved.replace(",", ".")) == values[REQUESTS[case["group"]]]
    check_equalities(solution_html(result), values)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_original_question_is_immutable_old_answers_unused_and_replay_empty(case):
    ctx = deepcopy(case["context"])
    for key in ("answer", "solution"):
        section(ctx, key)["html"] = "<p>Не использовать 999.</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before and result.answer == plan(case).answer
    for t in result.transformations:
        target = t["transformation_target_id"]
        assert not target.startswith(("section:condition", "asset:"))
        next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s["transformation_target_id"] == target
        ).update(t["value"])
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_the_parent_method_count_titles_and_half_hypotenuse_argument_survive(case):
    html = solution_html(plan(case))
    methods = BeautifulSoup(html, "html.parser").select("section")
    assert [m["data-solution-title"] for m in methods] == (
        ["Решение"]
        if case["group"] == "27791"
        else ["Решение", "Приведем другое решение"]
    )
    assert "половине гипотенузы AB" in html and "30°" in html
    if PARAMETERS[case["task"]][0] == 60:
        assert "угол B равен 30°" in html and r"AC=\frac{AB}{2}" in html
        assert r"BC=\frac{AB}{2}" not in html


@pytest.mark.parametrize("task", ["4799", "4797", "4801"])
def test_joined_formula_boundaries_are_read_without_invented_numbers(task):
    case = next(c for c in CASES if c["task"] == task)
    g = GROUPS[case["group"]]
    angle, length = degree_parent.read_question(
        section(case["context"], "condition")["html"],
        g["parent_asset"],
        REQUESTS[case["group"]],
    )
    assert (
        angle == PARAMETERS[task][0] and sp.simplify(length - PARAMETERS[task][1]) == 0
    )


@pytest.mark.parametrize("group", ["27789", "27790", "27791"])
@pytest.mark.parametrize("change", ["missing", "extra_method"])
def test_missing_or_unreviewed_parent_methods_fail_closed(group, change):
    case = next(c for c in CASES if c["group"] == group)
    html = (
        ""
        if change == "missing"
        else parent_html(group) + '<span data-inline-latex="AB=999"></span>'
    )
    with pytest.raises(ContentPlanError):
        plan(case, parent=html)


@pytest.mark.parametrize("group", ["27789", "27790", "27791"])
def test_unknown_question_instructions_are_not_dropped(group):
    case = next(c for c in CASES if c["group"] == group)
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Удвойте ответ.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_nonclassical_angle_cannot_use_a_thirty_degree_argument():
    case = next(c for c in CASES if c["task"] == "27790")
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = (
        "<p>В треугольнике ABC угол C равен 90°, CH — высота, угол A равен 45°, AB=8. Найдите AH.</p>"
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_complementary_angle_supports_the_inverse_projection_without_a_new_rule():
    case = next(c for c in CASES if c["task"] == "27790")
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = (
        "<p>В треугольнике ABC угол C равен 90°, CH — высота, угол A равен 60°, AB=8. Найдите AH.</p>"
    )
    result = plan(case, ctx)
    assert result.answer == "2"
    check_equalities(solution_html(result), coordinate_values(60, 8))


def test_original_height_figure_has_unchanged_geometry_and_bytes():
    for source, digest in degree_parent._SOURCES.items():
        p = Path(degree_parent.__file__).with_name("assets") / (source + ".svgz")
        assert hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest() == digest


@pytest.mark.parametrize(
    "group,html,length",
    [
        (
            "27789",
            r'<p>В треугольнике <span data-inline-latex="ABC"></span> угол C равен <span data-inline-latex="90^{\circ}"></span>, угол A равен <span data-inline-latex="60^\circ,\quad AB=2\sqrt{3}"></span> Найдите высоту <span data-inline-latex="CH"></span>.</p>',
            2 * sp.sqrt(3),
        ),
        (
            "27791",
            r'<p>В треугольнике ABC угол C равен <span data-inline-latex="90^{\circ}"></span>, <span data-inline-latex="CH"></span> — высота, угол A равен <span data-inline-latex="60^\circ,\ AB="></span>12. Найдите <span data-inline-latex="BH"></span>.</p>',
            12,
        ),
    ],
)
def test_known_tex_spacing_and_implicit_sentence_boundary_preserve_all_values(
    group, html, length
):
    case = next(c for c in CASES if c["group"] == group)
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = html
    angle, parsed = degree_parent.read_question(
        html, GROUPS[group]["parent_asset"], REQUESTS[group]
    )
    assert angle == 60 and sp.simplify(parsed - length) == 0
    result = plan(case, ctx)
    values = coordinate_values(angle, length)
    assert sp.Rational(result.answer.replace(",", ".")) == values[REQUESTS[group]]
    check_equalities(solution_html(result), values)
