"""Independent native answers and realizability boundaries for box measurements."""

import json
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.equations.power_arithmetic import ScalarParser
from solution_runner.pipelines.solids.box_model import read_question

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_3_box_measurement_sources.json"
    ).read_text()
)
GROUPS = {g["key"]: g for g in DATA["groups"]}


@pytest.mark.parametrize("case", DATA["cases"], ids=lambda c: c["task"])
def test_every_original_condition_matches_saved_answer(case):
    content = case["context"]["normalized_content"]
    fields = {s["key"]: s for s in content["sections"]}
    source = next(
        (
            a["asset_id"]
            for a in content["assets"]
            if a["asset_key"] in fields["condition"]["asset_keys"]
        ),
        None,
    )
    model = read_question(fields["condition"]["html"], source)
    soup = BeautifulSoup(fields["answer"]["html"], "html.parser")
    tag = soup.select_one("[data-inline-latex]")
    saved = tag["data-inline-latex"] if tag else soup.get_text(strip=True)
    assert model.mode == GROUPS[case["group"]]["mode"]
    assert (
        sp.simplify(
            model.answer - ScalarParser(case.get("expected_answer", saved)).parse()
        )
        == 0
    )


@pytest.mark.parametrize(
    "text",
    [
        "Два ребра прямоугольного параллелепипеда, выходящие из одной вершины, равны 3 и 4. Площадь поверхности этого параллелепипеда равна 24. Найдите третье ребро, выходящее из той же вершины.",
        "Два ребра прямоугольного параллелепипеда, выходящие из одной вершины, равны 3 и 4. Диагональ параллелепипеда равна 5. Найдите объем параллелепипеда.",
        "Площадь грани прямоугольного параллелепипеда равна 0. Ребро, перпендикулярное этой грани, равно 4. Найдите объем параллелепипеда.",
        "Ребра прямоугольного параллелепипеда, выходящие из одной вершины, равны 1,2,3. Найдите его площадь поверхности.",
        "Ребра прямоугольного параллелепипеда, выходящие из одной вершины, равны 1, 2, 3. Найдите его площадь поверхности. Округлите ответ.",
        "Ребра наклонного параллелепипеда, выходящие из одной вершины, равны 1, 2, 3. Найдите его площадь поверхности.",
    ],
)
def test_impossible_or_ambiguous_or_other_questions_fail_closed(text):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + text + "</p>")


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            "Три ребра прямоугольного параллелепипеда, выходящие из одной вершины, равны 1, 0,5 и 16. Найдите ребро равновеликого ему куба.",
            2,
        ),
        (
            "Три ребра прямоугольного параллелепипеда, выходящие из одной вершины, равны 1, 1 и 2. Найдите ребро равновеликого ему куба.",
            sp.real_root(2, 3),
        ),
        (
            "Два ребра прямоугольного параллелепипеда, выходящие из одной вершины, равны 1 и 2. Диагональ параллелепипеда равна 4. Найдите объем параллелепипеда.",
            2 * sp.sqrt(11),
        ),
    ],
)
def test_decimal_lists_and_nonperfect_positive_roots(text, expected):
    assert sp.simplify(read_question("<p>" + text + "</p>").answer - expected) == 0
