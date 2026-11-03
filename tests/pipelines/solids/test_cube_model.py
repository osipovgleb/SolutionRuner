"""Independent saved-answer checks and existence boundaries for cube quantities."""

import json
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.equations.power_arithmetic import ScalarParser
from solution_runner.pipelines.solids.cube_model import read_question

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_3_cube_sources.json").read_text()
)
GROUPS = {g["key"]: g for g in DATA["groups"]}
NUMERIC = DATA["cases"]


@pytest.mark.parametrize("case", NUMERIC, ids=lambda c: c["task"])
def test_all_original_cube_conditions_match_saved_answers(case):
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
    result = read_question(fields["condition"]["html"], source)
    soup = BeautifulSoup(fields["answer"]["html"], "html.parser")
    tag = soup.select_one("[data-inline-latex]")
    saved = tag["data-inline-latex"] if tag else soup.get_text(strip=True)
    assert result.mode == GROUPS[case["group"]]["mode"]
    assert sp.simplify(result.answer - ScalarParser(saved).parse()) == 0


@pytest.mark.parametrize(
    "html",
    [
        "Объем куба равен 0. Найдите площадь его поверхности.",
        "Если каждое ребро куба увеличить на 2, то его площадь поверхности увеличится на 24. Найдите ребро куба.",
        "Если каждое ребро куба увеличить на 2, то его объем увеличится на 8. Найдите ребро куба.",
        "Во сколько раз увеличится объем куба, если его ребра увеличить в один раз?",
        "Диагональ куба равна 2. Найдите его объем. Округлите ответ.",
    ],
)
def test_impossible_values_or_extra_instructions_fail_closed(html):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + html + "</p>")


def test_midpoint_section_really_has_three_equal_sides():
    from solution_runner.pipelines.solids.cube_section_model import VERTICES

    case = next(c for c in DATA["cases"] if c["task"] == "315130")
    content = case["context"]["normalized_content"]
    condition = next(s for s in content["sections"] if s["key"] == "condition")
    model = read_question(condition["html"], content["assets"][0]["asset_id"])
    points = [
        tuple(sp.Rational(x + y, 2) for x, y in zip(VERTICES[a], VERTICES[b]))
        for _, a, b in model.midpoints
    ]
    squares = [
        sum((x - y) ** 2 for x, y in zip(points[i], points[j]))
        for i, j in [(0, 1), (1, 2), (2, 0)]
    ]
    assert squares == [sp.Rational(1, 2)] * 3 and model.corner == "A_1"


@pytest.mark.parametrize(
    "change", [("AA_1", "AB_1"), ("A_1D_1", "BC"), ("A_1D_1", "AA_1"), ("MLK", "MMK")]
)
def test_invalid_midpoint_edge_graph_cannot_return_sixty(change):
    case = next(c for c in DATA["cases"] if c["task"] == "315130")
    content = case["context"]["normalized_content"]
    condition = next(s for s in content["sections"] if s["key"] == "condition")
    with pytest.raises(ContentPlanError):
        read_question(
            condition["html"].replace(*change), content["assets"][0]["asset_id"]
        )


@pytest.mark.parametrize(
    "html",
    [
        "<p>Объем куба равен раз. Найдите площадь его поверхности.</p>",
        '<p><img data-asset-key="image_1" src="/assets/unknown"/>Объем куба равен 8. Найдите площадь его поверхности.</p>',
        None,
    ],
)
def test_unknown_scalar_or_unreviewed_image_identity_is_a_validation_error(html):
    with pytest.raises(ContentPlanError):
        read_question(html)


def test_numeric_scale_factors_keep_the_shared_scalar_size_limit():
    with pytest.raises(ContentPlanError):
        read_question(
            "<p>Во сколько раз увеличится объем куба, если его ребра увеличить в 12345678901234567890 раз?</p>"
        )
