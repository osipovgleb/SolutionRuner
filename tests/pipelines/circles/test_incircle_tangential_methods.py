"""Verify mixed targets, ambiguity refusal and strict trapezoid existence bounds."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from incircle_source_cases import CASES, plan
from midpoint_source_cases import section, solution_html
from test_incircle_lifecycle import apply_offline, prepared
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.circles.incircle_model import RULES, read_question
from solution_runner.pipelines.core.errors import ContentPlanError

QUADS = ("27939", "27940", "27941", "627979")
QUERIES = (
    (
        "В четырехугольник ABCD вписана окружность, AB = 41, CD = 46. Найдите периметр четырехугольника ABCD.",
        "174",
        "perimeter",
    ),
    (
        "В четырехугольник ABCD вписана окружность, AB = 10, BC = 11 и CD = 15. Найдите четвертую сторону четырехугольника.",
        "14",
        "fourth_side",
    ),
    (
        "В четырехугольник ABCD, периметр которого равен 48, вписана окружность, AB = 15. Найдите CD.",
        "9",
        "opposite_side",
    ),
    (
        "Периметр четырехугольника, описанного около окружности, равен 24, две его стороны равны 5 и 6. Найдите большую из оставшихся сторон.",
        "7",
        "larger_side",
    ),
)


def replace_question(case, html):
    context = deepcopy(case["context"])
    condition = section(context, "condition")
    image = BeautifulSoup(condition["html"], "html.parser").find("img")
    condition["html"] = "<p>" + str(image) + html + "</p>"
    return context


@pytest.mark.parametrize("group", QUADS)
@pytest.mark.parametrize("html,expected,target", QUERIES, ids=lambda v: v)
def test_all_four_parent_pins_use_one_relation_and_the_child_question(
    group, html, expected, target
):
    case = next(c for c in CASES if c["task"] == group)
    context = replace_question(case, html)
    assert plan(case, context).answer == expected
    model = read_question("<p>" + html + "</p>")
    assert model.mode == "tangential_quad" and model.target == target
    assert {v for k, v in RULES.items() if "quadrilateral" in k} == {"tangential_quad"}


BAD = (
    (
        "27940",
        "Периметр четырехугольника, описанного около окружности, равен 24, две его стороны равны 5 и 7. Найдите большую из оставшихся сторон.",
        "undetermined",
    ),
    (
        "27940",
        "Периметр четырехугольника, описанного около окружности, равен 24, две его стороны равны 6 и 6. Найдите большую из оставшихся сторон.",
        "undetermined",
    ),
    (
        "27940",
        "Периметр четырехугольника, описанного около окружности, равен 24, две его стороны равны 12 и 3. Найдите большую из оставшихся сторон.",
        "positive",
    ),
    (
        "27941",
        "В четырехугольник ABCD вписана окружность, AB = 3, BC = 7 и CD = 4. Найдите четвертую сторону четырехугольника.",
        "positive",
    ),
    (
        "627979",
        "В четырехугольник ABCD, периметр которого равен 20, вписана окружность, AB = 11. Найдите длину стороны CD.",
        "positive",
    ),
    (
        "27938",
        "Периметр прямоугольной трапеции, описанной около окружности, равен 20, ее большая боковая сторона равна 5. Найдите радиус окружности.",
        "nondegenerate",
    ),
    (
        "27938",
        "Периметр прямоугольной трапеции, описанной около окружности, равен 20, ее большая боковая сторона равна 10. Найдите радиус окружности.",
        "nondegenerate",
    ),
    (
        "27938",
        "Периметр прямоугольной трапеции, описанной около окружности, равен 20, ее большая боковая сторона равна 11. Найдите радиус окружности.",
        "nondegenerate",
    ),
    (
        "27943",
        "К окружности, вписанной в треугольник ABC, проведены три касательные. Периметры отсеченных треугольников равны 6,8,10. Найдите периметр данного треугольника.",
        "reviewed incircle question",
    ),
    (
        "27943",
        "К окружности, вписанной в треугольник ABC, проведены три касательные. Периметры отсеченных треугольников равны 6, 8, 10. Найдите периметр данного треугольника. Округлите ответ.",
        "reviewed incircle question",
    ),
)


@pytest.mark.parametrize("group,html,message", BAD)
def test_ambiguous_or_impossible_data_block_before_any_local_write(
    group, html, message
):
    case = next(c for c in CASES if c["task"] == group)
    context = replace_question(case, html)
    with pytest.raises(ContentPlanError, match=message):
        plan(case, context)
    gateway = OfflineGateway({**case, "context": context})
    assert prepared(case, gateway)["status"] == "blocked"
    assert not gateway.uploads and not gateway.writes


@pytest.mark.parametrize("slant,answer", [("5,0001", "2,49995"), ("9,9999", "0,00005")])
def test_right_trapezoid_strict_bounds_use_exact_decimals(slant, answer):
    html = (
        "Периметр прямоугольной трапеции, описанной около окружности, равен 20, ее большая боковая сторона равна "
        + slant
        + ". Найдите радиус окружности."
    )
    case = next(c for c in CASES if c["task"] == "27938")
    assert plan(case, replace_question(case, html)).answer == answer


def test_tangent_cut_perimeters_are_not_original_triangle_side_lengths():
    html = "К окружности, вписанной в треугольник ABC, проведены три касательные. Периметры отсеченных треугольников равны 2, 4, 100. Найдите периметр данного треугольника."
    case = next(c for c in CASES if c["task"] == "27943")
    result = plan(case, replace_question(case, html))
    assert result.answer == "106"
    solution = solution_html(result)
    soup = BeautifulSoup(solution, "html.parser")
    assert soup.find("img")["data-asset-key"] == "image_2"
    assert len(soup.find_all("br")) == 2
    assert "K, H, O, F, N, M" in soup.get_text() and "цветами" in soup.get_text()


@pytest.mark.parametrize("drift", ["condition", "answer", "assets"])
def test_wrong_source_answer_00_is_corrected_but_frozen_input_drift_blocks(drift):
    case = next(c for c in CASES if c["task"] == "54649")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["expected_answer"] == "66" and record["status"] == "prepared"
    if drift == "assets":
        gateway.context["normalized_content"]["assets"][0]["asset_id"] = "foreign"
    else:
        section(gateway.context, drift)["html"] += "<p>Иные данные</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads and not gateway.writes
