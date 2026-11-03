"""Check native angle methods against independent linear constraints and ambiguity."""

import itertools
import json
import re
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.isosceles.angle_model import (
    RULES,
    read_question,
)
from solution_runner.pipelines.triangles.isosceles.angle_proofs import (
    render,
    review_parent,
)

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_1_isosceles_angle_sources.json"
    ).read_text()
)
CASES = DATA["cases"]
GROUPS = {g["key"]: g for g in DATA["groups"]}
PARENTS = {c["group"]: c for c in CASES if c["task"] == c["group"]}


def section(case, key):
    return next(
        s["html"]
        for s in case["context"]["normalized_content"]["sections"]
        if s["key"] == key
    )


def model(case):
    source = case["context"]["normalized_content"]["assets"][0]["asset_id"]
    return read_question(section(case, "condition"), source).require_rule(
        GROUPS[case["group"]]["rule"]
    )


def linear_angles(m):
    values = dict(zip("ABC", sp.symbols("A B C")))
    p, q = m.base_vertices
    equations = [values[p] - values[q], sum(values.values()) - 180]
    if m.given_kind == "difference":
        equations.append(values[m.apex] - values[p] - m.given_value)
    else:
        given = values[m.given_vertex]
        if m.given_kind.startswith("external_"):
            given = 180 - given
        equations.append(given - m.given_value)
    solved = sp.solve(equations, list(values.values()))
    return {k: solved[v] for k, v in values.items()}


def check_rows(html, m):
    values = linear_angles(m)
    for row in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        raw = row["data-inline-latex"]

        def angle(match):
            name = match[1]
            value = values[name] if len(name) == 1 else 180 - values[name[1]]
            return "(" + sp.latex(value) + ")"

        text = re.sub(r"\\angle\s*([ABC]{1,2}D|[ABC])", angle, raw).replace(
            r"^{\circ}", ""
        )
        text = re.sub(r"(?<![A-Za-z\\])x(?![A-Za-z])", "(" + sp.latex(m.answer) + ")", text)
        terms = [TrigonometricParser(part).parse().value for part in text.split("=")]
        assert len(terms) > 1 and all(sp.simplify(v - terms[0]) == 0 for v in terms), (
            raw
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_native_answer_constraint_and_preserved_parent_equation(case):
    m = model(case)
    expected = sp.Rational(
        BeautifulSoup(section(case, "answer"), "html.parser")
        .get_text()
        .replace(",", ".")
    )
    assert m.answer == expected
    independent = linear_angles(m)
    assert independent[m.apex] == m.apex_angle
    assert all(independent[v] == m.base_angle for v in m.base_vertices)
    rule = GROUPS[case["group"]]["rule"]
    review_parent(section(PARENTS[case["group"]], "solution"), rule)
    check_rows(render(m, rule), m)
    for other in RULES:
        if other != rule:
            with pytest.raises(ContentPlanError):
                m.require_rule(other)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "extra", ["Удвойте ответ.", "Угол A равен 10°.", "Найдите периметр."]
)
def test_extra_statements_are_never_discarded(case, extra):
    source = case["context"]["normalized_content"]["assets"][0]["asset_id"]
    with pytest.raises(ContentPlanError):
        read_question(section(case, "condition") + "<p>" + extra + "</p>", source)


@pytest.mark.parametrize("frame", list(itertools.permutations("ABC")))
@pytest.mark.parametrize(
    "kind", ["base", "vertex", "external_base", "external_vertex", "requested_external"]
)
def test_all_named_vertex_frames_follow_the_same_linear_geometry(frame, kind):
    p, q, r = frame
    equal = p + r + "=" + q + r
    given = {
        "base": f"угол {p} равен 38°, {equal}",
        "vertex": f"{equal}, угол {r} равен 118°",
        "external_base": f"{equal}. Внешний угол при вершине {q} равен 122°",
        "external_vertex": f"{equal}. Внешний угол при вершине {r} равен 138°",
        "requested_external": f"{equal}, угол {r} равен 52°",
    }[kind]
    target = (
        ("внешний угол " + r + q + "D")
        if kind == "requested_external"
        else "угол " + (r if kind in {"base", "external_base"} else p)
    )
    html = (
        f"<p>В треугольнике ABC {given}. Найдите {target}. Ответ дайте в градусах.</p>"
    )
    m = read_question(html, "")
    assert m.apex == r
    expected = {
        "base": 104,
        "vertex": 31,
        "external_base": 64,
        "external_vertex": 69,
        "requested_external": 116,
    }[kind]
    assert m.answer == expected
    check_rows(
        render(
            m,
            next(
                rule
                for rule, roles in RULES.items()
                if roles == (m.given_kind, m.requested_kind)
            ),
        ),
        m,
    )


@pytest.mark.parametrize("larger", [61, 70, 89])
def test_acute_larger_angle_has_two_valid_triangles_and_must_fail_closed(larger):
    candidates = [
        (larger, (180 - larger) / 2, (180 - larger) / 2),
        (180 - 2 * larger, larger, larger),
    ]
    assert all(min(t) > 0 and sum(t) == 180 and max(t) == larger for t in candidates)
    assert min(candidates[0]) != min(candidates[1])
    with pytest.raises(ContentPlanError, match="two distinct"):
        read_question(
            f"<p>Больший угол равнобедренного треугольника равен {larger}°. Найдите меньший угол. Ответ дайте в градусах.</p>",
            "",
        )


@pytest.mark.parametrize("difference", [1, 30, 60, 89])
def test_small_difference_has_two_valid_triangles_and_must_fail_closed(difference):
    d = sp.Rational(difference)
    x = (180 - d) / 3
    y = (180 - 2 * d) / 3
    candidates = [(x, x, x + d), (y, y + d, y + d)]
    assert all(
        min(t) > 0 and sum(t) == 180 and max(t) - min(t) == d for t in candidates
    )
    assert min(candidates[0]) != min(candidates[1])
    with pytest.raises(ContentPlanError, match="two distinct"):
        read_question(
            f"<p>Один угол равнобедренного треугольника на {difference}° больше другого. Найдите меньший угол. Ответ дайте в градусах.</p>",
            "",
        )


@pytest.mark.parametrize(
    "text,answer",
    [
        ("Больший угол равнобедренного треугольника равен 90°", 45),
        ("Один угол равнобедренного треугольника на 90° больше другого", 30),
    ],
)
def test_nonambiguous_boundary_is_supported(text, answer):
    m = read_question(
        f"<p>{text}. Найдите меньший угол. Ответ дайте в градусах.</p>", ""
    )
    assert m.answer == answer


@pytest.mark.parametrize("value", [0, 60, 180, 181])
def test_impossible_larger_angles_are_rejected(value):
    with pytest.raises(ContentPlanError):
        read_question(
            f"<p>Больший угол равнобедренного треугольника равен {value}°. Найдите меньший угол. Ответ дайте в градусах.</p>",
            "",
        )


@pytest.mark.parametrize("group", list(GROUPS))
def test_parent_method_changes_require_review(group):
    original = section(PARENTS[group], "solution")
    rule = GROUPS[group]["rule"]
    for changed in (None, "", original + "<p>Другой способ.</p>"):
        with pytest.raises(ContentPlanError):
            review_parent(changed, rule)
