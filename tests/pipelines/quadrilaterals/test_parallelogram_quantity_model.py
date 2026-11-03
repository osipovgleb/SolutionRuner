"""Independent vector areas and heights check all seven native quantity families."""

import json
import math
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import section

from solution_runner.pipelines.core.content_runtime import _solution_assets
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.quadrilaterals.parallelogram.quantity_model import (
    read_question,
)
from solution_runner.pipelines.quadrilaterals.parallelogram.quantity_sources import (
    PARENTS,
    review_parent,
)

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_1_parallelogram_quantity_sources.json"
    ).read_text()
)
CASES = DATA["cases"]


def read(context):
    c = section(context, "condition")
    source = next(
        (
            a["asset_id"]
            for a in context["normalized_content"]["assets"]
            if a["asset_key"] in c["asset_keys"]
        ),
        None,
    )
    return read_question(c["html"], source)


def distance_to_line(point, start, end):
    u = end[0] - start[0], end[1] - start[1]
    v = point[0] - start[0], point[1] - start[1]
    return abs(u[0] * v[1] - u[1] * v[0]) / math.hypot(*u)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_answers_side_lengths_height_and_vector_area(case):
    before = deepcopy(case["context"])
    m = read(case["context"])
    assert case["context"] == before
    a, b, sine = map(float, (m.a, m.b, m.sine))
    u, v = (a * math.sqrt(1 - sine**2), a * sine), (b, 0)
    area = abs(u[0] * v[1] - u[1] * v[0])
    first = distance_to_line(v, (0, 0), u)
    second = distance_to_line(u, (0, 0), v)
    assert area == pytest.approx(float(m.area))
    assert first == pytest.approx(float(m.first_height))
    assert second == pytest.approx(float(m.second_height))
    if m.mode in {"sine", "height", "sixty_height", "ratio_height"}:
        expected = max(first, second)
    elif m.mode == "transfer":
        assert first == pytest.approx(float(m.given[2]))
        expected = second
    elif m.mode in {"thirty", "diagonals"}:
        expected = area
    elif m.mode == "sixty_diagonal":
        expected = math.dist((0, 0), (u[0] + v[0], u[1] + v[1]))
    elif m.mode == "other":
        expected = 2 * float(m.given[0]) / float(m.given[1])
    else:
        expected = math.sqrt(2 * float(m.given[0]) / float(m.given[1]))
    assert float(m.answer) == pytest.approx(expected)
    saved = BeautifulSoup(
        section(case["context"], "answer")["html"], "html.parser"
    ).get_text(strip=True)
    assert float(
        Fraction(case.get("expected_answer", saved).replace(",", "."))
    ) == pytest.approx(expected)
    if m.diagonals:
        first, second = map(float, m.diagonals)
        assert a == pytest.approx(b)
        assert math.hypot(first / 2, second / 2) == pytest.approx(a)
        assert first * second / 2 == pytest.approx(area)


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_complete_native_parent_methods_and_all_figure_keys_are_pinned(group):
    parent = next(c["context"] for c in CASES if c["task"] == group["key"])
    primary, _, _ = PARENTS[group["rule"]]
    html = section(parent, "solution")["html"]
    assets = _solution_assets(parent)
    review_parent(group["rule"], primary, html, assets)
    with pytest.raises(ContentPlanError):
        review_parent(group["rule"], primary, html + "<p>Другой способ.</p>", assets)
    with pytest.raises(ContentPlanError):
        review_parent(group["rule"], "foreign", html, assets)


@pytest.mark.parametrize(
    "html",
    [
        "<p>В параллелограмме ABCD AB=3, AD=5, \\sin A=2. Найдите большую высоту параллелограмма.</p>",
        "<p>В параллелограмме ABCD AB=0, AD=5, \\sin A=0,5. Найдите большую высоту параллелограмма.</p>",
        "<p>Стороны параллелограмма равны 3 и 5. Высота, опущенная на первую сторону, равна 6. Найдите высоту, опущенную на вторую сторону параллелограмма.</p>",
        "<p>Площадь параллелограмма равна 16, две его стороны равны 3 и 5. Найдите большую высоту этого параллелограмма.</p>",
        "<p>Площадь ромба равна 6. Одна из его диагоналей в 1 раз больше другой. Найдите меньшую диагональ.</p>",
        "<p>Найдите площадь ромба, если его высота равна 2, а острый угол 60°.</p>",
        "<p>Найдите площадь ромба, если его диагонали равны -4 и 5.</p>",
        "<p>Найдите площадь ромба, если его диагонали равны 4 и 5. Округлите ответ.</p>",
    ],
)
def test_impossible_data_unreviewed_methods_and_extra_instructions_fail_closed(html):
    with pytest.raises(ContentPlanError):
        read_question(html)


@pytest.mark.parametrize(
    "first,second,sine,frame,projection",
    [
        (3, 5, r"\frac{4}{5}", "ABCD", 3),
        (5, 3, r"\frac{4}{5}", "ADCB", 3),
        (3, 5, "1", "ABCD", 0),
    ],
)
def test_swapped_sides_vertex_foot_and_right_angle_are_exact(
    first, second, sine, frame, projection
):
    m = read_question(
        f"<p>В параллелограмме ABCD AB={first}, AD={second}, \\sin A={sine}. Найдите большую высоту параллелограмма.</p>"
    )
    assert m.frame == frame and m.projection == projection
    assert m.name("AB") == ("AB" if frame == "ABCD" else "AD")


def test_native_projection_really_changes_side_incidence_and_equal_side_case():
    models = {c["task"]: read(c["context"]) for c in CASES}
    assert models["27436"].projection > models["27436"].a
    assert models["44409"].projection < models["44409"].a
    assert models["44411"].a == models["44411"].b
    assert models["56155"].projection > models["56155"].a
    assert models["549315"].projection < models["549315"].a


@pytest.mark.parametrize(
    "r,s,perimeter", [(1, 1, 40), (1, 9, 164), (9, 1, 164), (4, 7, 65)]
)
def test_ratio_height_from_independent_area_and_perimeter(r, s, perimeter):
    m = read_question(
        f"<p>Диагонали ромба относятся как {r}:{s}. Периметр ромба равен {perimeter}. Найдите высоту ромба.</p>"
    )
    side = perimeter / 4
    short_half = side * r / math.hypot(r, s)
    long_half = side * s / math.hypot(r, s)
    assert float(m.answer) == pytest.approx(2 * short_half * long_half / side)
    assert 0 < float(m.answer) <= side


def test_native_50137_saved_answer_exceeds_side_and_is_corrected_locally():
    case = next(c for c in CASES if c["task"] == "50137")
    m = read(case["context"])
    assert m.a == Fraction(65, 4) and m.answer == 14
    assert (
        BeautifulSoup(
            section(case["context"], "answer")["html"], "html.parser"
        ).get_text(strip=True)
        == "28"
    )


@pytest.mark.parametrize(
    "html",
    [
        "Найдите высоту ромба, сторона которого равна 3, а острый угол равен 30°.",
        "Найдите большую диагональ ромба, сторона которого равна -3, а острый угол равен 60°.",
        "Диагонали ромба относятся как 0:4. Периметр ромба равен 40. Найдите высоту ромба.",
        "Диагонали ромба относятся как 3:4. Периметр ромба равен -40. Найдите высоту ромба.",
        "Диагонали ромба относятся как 3:4. Периметр ромба равен 40. Найдите высоту ромба. Округлите ответ.",
    ],
)
def test_new_rhombus_invalid_or_unreviewed_questions_fail_closed(html):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + html + "</p>")
