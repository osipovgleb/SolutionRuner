"""Read every original combination source and reject ambiguous or impossible givens."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from sphere_formula_oracle import PiParser

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.combined_reader import read

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_3_combined_sources.json").read_text()
)
CASES = DATA["cases"]


def question(case):
    n = case["context"]["normalized_content"]
    html = next(s["html"] for s in n["sections"] if s["key"] == "condition")
    soup = BeautifulSoup(html, "html.parser")
    image = soup.find("img")
    return html, image["data-asset-id"] if image else None


def expected(case):
    if "expected_answer" in case:
        return PiParser(case["expected_answer"]).parse().value
    sections = case["context"]["normalized_content"]["sections"]
    html = next(s["html"] for s in sections if s["key"] == "answer")
    soup = BeautifulSoup(html, "html.parser")
    formula = soup.select_one("[data-inline-latex]")
    return (
        PiParser(formula["data-inline-latex"] if formula else soup.get_text(strip=True))
        .parse()
        .value
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_native_question_uses_condition_and_independent_saved_answer(case):
    before = deepcopy(case)
    m = read(*question(case))
    assert sp.simplify(m.answer - expected(case)) == 0
    assert case == before
    assert m.answer.is_positive and m.answer.is_finite


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_unreviewed_additional_instruction_is_not_ignored(case):
    html, source = question(case)
    with pytest.raises(ContentPlanError):
        read(html + "<p>Найдите также площадь сечения.</p>", source)


@pytest.mark.parametrize(
    "html,answer",
    [
        (
            "Шар вписан в цилиндр. Площадь полной поверхности цилиндра равна 7,5. Найдите площадь поверхности шара.",
            "5",
        ),
        (
            "Шар вписан в цилиндр. Площадь поверхности шара равна 7. Найдите площадь полной поверхности цилиндра.",
            "10.5",
        ),
        (
            "Цилиндр описан около шара. Объем цилиндра равен 7,5. Найдите объем шара.",
            "5",
        ),
        (
            "Цилиндр описан около шара. Объем шара равен 7. Найдите объем цилиндра.",
            "10.5",
        ),
        (
            "Цилиндр и конус имеют общие основание и высоту. Объем конуса равен 0,5. Найдите объем цилиндра.",
            "1.5",
        ),
        (
            "Цилиндр и конус имеют общие основание и высоту. Объем цилиндра равен 1,5. Найдите объем конуса.",
            "0.5",
        ),
        (
            "Конус вписан в шар. Радиус основания конуса равен радиусу шара. Объем шара равен 1. Найдите объем конуса.",
            "0.25",
        ),
        (
            "Конус вписан в шар. Радиус основания конуса равен радиусу шара. Объем конуса равен 0,25. Найдите объем шара.",
            "1",
        ),
        (
            "Объем конуса, вписанного в правильную четырехугольную пирамиду, равен 7. Найдите объем конуса, описанного около этой пирамиды.",
            "14",
        ),
        (
            "Объем конуса, описанного около правильной четырехугольной пирамиды, равен 7. Найдите объем конуса, вписанного в эту пирамиду.",
            "3.5",
        ),
        ("В куб вписан шар радиуса 1,25. Найдите объем куба.", "15.625"),
        ("Куб вписан в шар радиуса 1,25\\sqrt{3}. Найдите объем куба.", "15.625"),
        (
            "Середина ребра куба со стороной 8 является центром шара радиуса 1,5. Найдите площадь S части поверхности шара, лежащей внутри куба. В ответе запишите S\\div \\pi.",
            "2.25",
        ),
        (
            "Из единичного куба вырезана правильная четырехугольная призма со стороной основания 0,25 и боковым ребром 1. Найдите площадь поверхности оставшейся части куба.",
            "6.875",
        ),
        (
            "Прямоугольный параллелепипед описан около цилиндра, радиус основания которого равен 2,5. Объем параллелепипеда равен 75. Найдите высоту цилиндра.",
            "3",
        ),
    ],
)
def test_unseen_values_and_opposite_directions_are_computed(html, answer):
    # The strict geometry reader expects formulas in explicit math spans.
    html = html.replace(
        r"1,25\sqrt{3}", '<span data-inline-latex="1,25\\sqrt{3}"></span>'
    ).replace(r"S\div \pi", '<span data-inline-latex="S\\div \\pi"></span>')
    assert read("<p>" + html + "</p>").answer == sp.Rational(answer)


@pytest.mark.parametrize(
    "html",
    [
        "Шар вписан в цилиндр. Площадь поверхности шара равна -1. Найдите площадь полной поверхности цилиндра.",
        "Куб вписан в шар радиуса 0. Найдите объем куба.",
        "Прямоугольный параллелепипед описан около цилиндра, радиус основания которого равен 0. Объем параллелепипеда равен 5. Найдите высоту цилиндра.",
        "Из единичного куба вырезана правильная четырехугольная призма со стороной основания 1 и боковым ребром 1. Найдите площадь поверхности оставшейся части куба.",
        "Из единичного куба вырезана правильная четырехугольная призма со стороной основания 0,5 и боковым ребром 0,5. Найдите площадь поверхности оставшейся части куба.",
        "Середина ребра куба со стороной 1 является центром шара радиуса 0,6. Найдите площадь S части поверхности шара, лежащей внутри куба. В ответе запишите S\\div \\pi.",
        "Объем тетраэдра равен 12. Найдите площадь поверхности многогранника, вершинами которого являются середины ребер данного тетраэдра.",
        "Объем конуса, вписанного в правильную четырехугольную пирамиду, равен 7. Найдите объем конуса, вписанного в эту пирамиду.",
        "Шар, объем которого равен 6, вписан в куб. Найдите объем куба.",
        "Конус вписан в шар. Объем шара равен 28. Найдите объем конуса.",
        "Цилиндр и конус имеют равные высоты. Объем конуса равен 25. Найдите объем цилиндра.",
    ],
)
def test_degenerate_ambiguous_or_different_geometry_fails_closed(html):
    html = html.replace(r"S\div \pi", '<span data-inline-latex="S\\div \\pi"></span>')
    with pytest.raises(ContentPlanError):
        read("<p>" + html + "</p>")


def test_source_gaps_and_manual_answer_corrections_are_explicit():
    groups = {g["key"]: g for g in DATA["groups"]}
    assert len(groups) == 36 and len(CASES) == 141
    assert all(g["size"] > 2 for g in groups.values())
    assert {c["task"] for c in CASES if "expected_answer" in c} == {
        "75319",
        "25965",
        "269315",
        "316873",
        "316875",
        "316975",
    }
    assert all(c["correction_reason"] for c in CASES if "expected_answer" in c)
    assert groups["27124"]["unavailable_source_tasks"]
    assert not any(c["task"] == "324343" for c in CASES)


def test_midpoint_hull_for_an_irregular_tetrahedron_from_coordinate_faces():
    from itertools import combinations

    points = [sp.Matrix(p) for p in [(0, 0, 0), (6, 0, 0), (1, 4, 0), (2, 1, 5)]]

    def area(vertices):
        a, b, c = vertices
        return sp.sqrt((b - a).cross(c - a).dot((b - a).cross(c - a))) / 2

    def volume(vertices):
        a, b, c, d = vertices
        return abs(sp.det(sp.Matrix.hstack(b - a, c - a, d - a))) / 6

    faces = [[points[i] for i in face] for face in combinations(range(4), 3)]
    surface = sp.simplify(sum(area(face) for face in faces))
    mid_faces = [[(a + b) / 2, (b + c) / 2, (a + c) / 2] for a, b, c in faces]
    cuts = [
        [points[i], *[(points[i] + p) / 2 for j, p in enumerate(points) if j != i]]
        for i in range(4)
    ]
    inner_surface = sp.simplify(
        sum(area(face) for face in mid_faces) + sum(area(cut[1:]) for cut in cuts)
    )
    inner_volume = volume(points) - sum(volume(cut) for cut in cuts)
    assert len({area(face) for face in faces}) > 1
    for measure, amount, answer, word in (
        ("Объем", volume(points), inner_volume, "равен"),
        ("Площадь поверхности", surface, inner_surface, "равна"),
    ):
        html = (
            f'<p>{measure} тетраэдра {word} <span data-inline-latex="{sp.latex(amount)}"></span>. '
            f"Найдите {measure.lower()} многогранника, вершинами которого являются середины ребер данного тетраэдра.</p>"
        )
        assert sp.simplify(read(html).answer - answer) == 0
