"""Every native answer and parent method is checked through exact equalities."""

import math
import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from iso_trapezoid_source_cases import CASES, GROUPS, arguments, plan, read
from midpoint_source_cases import replay, section, solution_html

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.quadrilaterals.trapezoid.isosceles_model import (
    read_question,
)


def verify(html, m):
    special = {
        r"\sin^2\angle CDA": m.sine**2,
        r"\sin\angle CDA": m.sine,
        r"\cos\angle CDA": m.cosine,
        r"\cos\angle BAD": m.cosine,
        r"\tg\angle CDA": m.tangent,
        r"\tg\angle BAD": m.tangent,
        r"\cos 60^{\circ}": sp.Rational(1, 2),
        r"\cos60^{\circ}": sp.Rational(1, 2),
        r"\tg45^{\circ}": 1,
        r"\angle ABH": 30,
    }
    variables = {
        "AD": m.large,
        "BC": m.small,
        "AB": m.leg,
        "CD": m.leg,
        "AH": m.projection,
        "ED": m.projection,
        "BH": m.height,
        "CE": m.height,
        "S": m.area,
        "P": m.perimeter,
    }
    for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = tag["data-inline-latex"]
        for label, value in special.items():
            formula = formula.replace(label, "(" + sp.latex(value) + ")")
        for label, value in sorted(variables.items(), key=lambda v: -len(v[0])):
            formula = re.sub(
                r"(?<![A-Za-z_])" + re.escape(label) + r"(?![A-Za-z_])",
                lambda _, v=value: "(" + sp.latex(v) + ")",
                formula,
            )
        formula = formula.replace(r"^{\circ}", "")
        for statement in re.split(r",\s*\\quad\s*", formula):
            numbers = [
                float(TrigonometricParser(part).parse().value)
                for part in statement.split("=")
            ]
            assert len(numbers) > 1, statement
            assert all(
                math.isclose(v, numbers[0], rel_tol=1e-9, abs_tol=1e-8) for v in numbers
            ), statement


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_exact_answers_methods_and_every_formula(case):
    m = read(case["context"])
    result = plan(case)
    saved = BeautifulSoup(
        section(case["context"], "answer")["html"], "html.parser"
    ).get_text(strip=True)
    expected = case.get("expected_answer", saved)
    assert float(result.answer.replace(",", ".")) == pytest.approx(
        float(expected.replace(",", "."))
    )
    html = solution_html(result)
    verify(html, m)
    assert [
        s["data-solution-title"]
        for s in BeautifulSoup(html, "html.parser").select("section")
    ] == (
        ["Решение", "Приведем другое решение"]
        if m.mode == "perimeter_sixty"
        else ["Решение"]
    )
    assert (
        5 <= len(BeautifulSoup(html, "html.parser").select("[data-inline-latex]")) <= 14
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_independent_polygon_area_perimeter_and_right_triangle(case):
    m = read(case["context"])
    a, b, h, q = map(float, (m.small, m.large, m.height, m.projection))
    points = [(0, 0), (q, h), (q + a, h), (b, 0)]
    area = (
        abs(
            sum(
                points[i][0] * points[(i + 1) % 4][1]
                - points[(i + 1) % 4][0] * points[i][1]
                for i in range(4)
            )
        )
        / 2
    )
    perimeter = sum(math.dist(points[i], points[(i + 1) % 4]) for i in range(4))
    leg = math.dist(points[0], points[1])
    assert float(m.area) == pytest.approx(area)
    assert float(m.perimeter) == pytest.approx(perimeter)
    assert math.dist(points[0], points[1]) == pytest.approx(
        math.dist(points[2], points[3])
    )
    assert float(m.sine) == pytest.approx(h / leg)
    assert float(m.cosine) == pytest.approx(q / leg)
    assert float(m.tangent) == pytest.approx(h / q)
    assert a > 0 and b > a and h > 0


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_immutable_inputs_unused_saved_answer_and_empty_replay(case):
    context = deepcopy(case["context"])
    section(context, "answer")["html"] = "<p>999</p>"
    before = deepcopy(context)
    result = plan(case, context)
    assert context == before and result.answer == plan(case).answer
    replay(context, result.transformations)
    assert plan(case, context).transformations == ()
    assert section(context, "source") == section(before, "source")
    conditions = []
    for ctx in (before, context):
        soup = BeautifulSoup(section(ctx, "condition")["html"], "html.parser")
        for image in soup.find_all("img"):
            image.decompose()
        conditions.append(str(soup))
    assert conditions[0] == conditions[1]


@pytest.mark.parametrize("group", GROUPS.values(), ids=lambda g: g["key"])
@pytest.mark.parametrize("change", ["html", "source", "assets"])
def test_bindings_and_complete_parent_pins(group, change):
    profile, handler = get_group_profile(group["key"]), get_handler(group["rule"])
    assert (
        profile.source_group_id == group["group_uuid"]
        and profile.existing_solution_policy == "rewrite"
    )
    assert (
        handler.parent_from_group_listing
        and handler.requires_frozen_manifest
        and handler.verify_content_readback
        and handler.strict_frozen_input
    )
    handler.validate()
    case = next(c for c in CASES if c["task"] == group["key"])
    overrides = (
        {
            "parent_solution_html": arguments(group["key"])["parent_solution_html"]
            + "<p>Другой метод.</p>"
        }
        if change == "html"
        else (
            {"parent_asset_id": "foreign"}
            if change == "source"
            else {"parent_solution_assets": ({"asset_key": "foreign"},)}
        )
    )
    with pytest.raises(ContentPlanError):
        plan(case, **overrides)


@pytest.mark.parametrize(
    "html",
    [
        "Основания равнобедренной трапеции равны 6 и 6. Боковые стороны равны 5. Найдите синус острого угла трапеции.",
        "Основания равнобедренной трапеции равны 6 и 12. Боковые стороны равны 3. Найдите синус острого угла трапеции.",
        "Основания равнобедренной трапеции равны 6 и 12. Косинус острого угла трапеции равен 1. Найдите боковую сторону.",
        "Большее основание равнобедренной трапеции равно 4. Боковая сторона равна 5. Синус острого угла равен 0,8. Найдите меньшее основание.",
        "Большее основание равнобедренной трапеции равно 12. Боковая сторона равна 5. Синус острого угла равен 1. Найдите меньшее основание.",
        "Основания равнобедренной трапеции равны 6 и 12. Тангенс острого угла равен -2. Найдите высоту трапеции.",
        "Основания равнобедренной трапеции равны 6 и 12, а ее периметр равен 20. Найдите площадь трапеции.",
        "Основания равнобедренной трапеции равны 6 и 12, а ее площадь равна 0. Найдите периметр трапеции.",
        "В равнобедренной трапеции основания равны 6 и 12, острый угол равен 30°. Найдите ее периметр.",
        "Основания равнобедренной трапеции равны 6 и 12, один из углов равен 60°. Найдите высоту трапеции.",
        "Основания равнобедренной трапеции равны 6 и 12. Высота трапеции равна 4. Найдите тангенс острого угла. Округлите ответ.",
    ],
)
def test_impossible_degenerate_and_unreviewed_questions_fail_closed(html):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + html + "</p>")


@pytest.mark.parametrize(
    "task,expected",
    [("44909", sp.Rational(4, 5)), ("61309", 54), ("61357", 64), ("50537", 14)],
)
def test_incorrect_source_answers_are_retained_in_fixture_and_corrected_by_geometry(
    task, expected
):
    case = next(c for c in CASES if c["task"] == task)
    saved = BeautifulSoup(
        section(case["context"], "answer")["html"], "html.parser"
    ).get_text(strip=True)
    assert float(saved.replace(",", ".")) != float(expected)
    assert read(case["context"]).answer == expected


@pytest.mark.parametrize("task", ["512349", "512391"])
def test_area_to_leg_parent_also_handles_children_requesting_perimeter(task):
    case = next(c for c in CASES if c["task"] == task)
    assert case["group"] == "27636" and read(case["context"]).requested == "perimeter"
    assert plan(case).answer in {"48", "26"}
