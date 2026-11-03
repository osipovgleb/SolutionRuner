"""Check native answers and independently constructed supplementary-angle geometry."""

import itertools
import json
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.triangles.isosceles.obtuse_model import (
    RULES,
    read_question,
)

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_1_isosceles_obtuse_sources.json"
    ).read_text()
)
CASES = DATA["cases"]
GROUPS = {g["key"]: g for g in DATA["groups"]}


def condition(case):
    content = case["context"]["normalized_content"]
    html = next(s["html"] for s in content["sections"] if s["key"] == "condition")
    source = next(
        a["asset_id"] for a in content["assets"] if a["asset_key"] == "image_1"
    )
    return html, source


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_complete_question_matches_independent_recorded_answer(case):
    model = read_question(*condition(case)).require_rule(GROUPS[case["group"]]["rule"])
    content = case["context"]["normalized_content"]
    answer = next(s["html"] for s in content["sections"] if s["key"] == "answer")
    expected = sp.Rational(
        BeautifulSoup(answer, "html.parser").get_text().replace(",", ".")
    )
    assert model.answer == expected
    assert sp.simplify(model.height**2 + model.projection**2 - model.side**2) == 0
    assert (
        model.side.is_positive
        and model.height.is_positive
        and model.projection.is_positive
    )
    for rule in RULES:
        if rule != GROUPS[case["group"]]["rule"]:
            with pytest.raises(ContentPlanError):
                model.require_rule(rule)


@pytest.mark.parametrize("vertices", list(itertools.permutations("ABC")))
@pytest.mark.parametrize(
    "kind", ["side_height", "side_projection", "height_projection"]
)
@pytest.mark.parametrize("function", ["sin", "cos", "tg"])
def test_all_vertex_frames_against_vector_geometry(vertices, kind, function):
    p, r, q = vertices
    # Apex R=(0,0), H=(-3,0), P=(-3,4), Q=(5,0): RP=RQ=5.
    givens = {
        "side_height": f"{p + r}={q + r}=5, высота {p}H равна 4",
        "side_projection": f"{p + r}={q + r}=5, {p}H — высота, {r}H=3",
        "height_projection": f"{p + r}={q + r}, высота {p}H равна 4, {r}H=3",
    }[kind]
    html = f'<p>В тупоугольном треугольнике ABC {givens}. Найдите <span data-inline-latex="\\{function} {p + r + q}"></span>.</p>'
    model = read_question(html, "")
    u, v = sp.Matrix([-3, 4]), sp.Matrix([5, 0])
    cosine = u.dot(v) / (u.norm() * v.norm())
    sine = abs(sp.det(sp.Matrix.hstack(u, v))) / (u.norm() * v.norm())
    assert model.answer == {"sin": sine, "cos": cosine, "tg": sine / cosine}[function]
    assert (model.vertex, model.apex, model.other_base_vertex) == vertices
    assert model.requested == p + r + q
    assert model.given_kind == kind


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("extra", ["Площадь равна 9.", "AB=1.", "Найдите AB."])
def test_reject_unreviewed_condition_statements(case, extra):
    html, source = condition(case)
    with pytest.raises(ContentPlanError):
        read_question(html + "<p>" + extra + "</p>", source)


@pytest.mark.parametrize(
    "given",
    [
        "AC=BC=5, высота AH равна 5",
        "AC=BC=5, высота AH равна 6",
        "AC=BC=5, AH — высота, CH=5",
        "AC=BC=5, AH — высота, CH=6",
        "AC=BC=5, высота CH равна 4",
        "AC=BC=5, AH — высота, AB=3",
        "AC=BC=5, высота AH равна 4, AH=4",
        "AC=BC=5, высота AH равна 4, BC=5",
        "AC=BC=5, высота AH равна 0",
        "AC=BC=5, высота AH равна -4",
    ],
)
def test_reject_degenerate_wrong_or_duplicate_givens(given):
    with pytest.raises(ContentPlanError):
        read_question(
            f"<p>В тупоугольном треугольнике ABC {given}. Найдите синус угла ACB.</p>",
            "",
        )


@pytest.mark.parametrize(
    "question",
    ["синус угла ABC", "синус угла ACA", "синус угла C", "AC", "тангенс угла ACB и AB"],
)
def test_reject_incomplete_or_wrong_vertex_request(question):
    with pytest.raises(ContentPlanError):
        read_question(
            f"<p>В тупоугольном треугольнике ABC AC=BC=5, высота AH равна 4. Найдите {question}.</p>",
            "",
        )


def test_requires_explicit_obtuse_assumption():
    with pytest.raises(ContentPlanError):
        read_question(
            "<p>В треугольнике ABC AC=BC=5, высота AH равна 4. Найдите синус угла ACB.</p>",
            "",
        )
