"""Check every parent equality, exact radius and physical-existence refusal."""

import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from incircle_source_cases import CASES, GROUPS, REJECTED_CASES, arguments, plan, read
from midpoint_source_cases import replay, section, solution_html

from solution_runner.pipelines.circles.incircle_model import read_question
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.power_arithmetic import ScalarParser
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser

TITLES = {
    "equilateral_height_radius": ["Решение", "Приведем другое решение"],
    "isosceles_right_radius": ["Решение", "Приведём другое решение"],
    "right_radius": ["Решение", "Альтернативное решение."],
    "isosceles_radius": ["Решение", "Альтернативное решение."],
}


def variables(m):
    a = m.given[0]
    if m.mode in {"polygon_area", "triangle_area"}:
        perimeter, radius = m.given if m.mode == "triangle_area" else m.given[::-1]
        return {
            "P": perimeter,
            "p": perimeter / 2,
            "r": radius,
            "S": perimeter * radius / 2,
        }
    if m.mode == "triangle_perimeter":
        area, radius = m.given
        return {"S": area, "r": radius, "p": area / radius, "P": 2 * area / radius}
    if m.mode.startswith("equilateral_"):
        radius = {
            "equilateral_radius_height": a / 3,
            "equilateral_height_radius": a,
            "equilateral_radius_side": a * sp.sqrt(3) / 6,
            "equilateral_side_radius": a,
        }[m.mode]
        side = 2 * sp.sqrt(3) * radius
        return {
            "r": radius,
            "h": 3 * radius,
            "a": side,
            r"S_{ABC}": side**2 * sp.sqrt(3) / 4,
            r"P_{ABC}": 3 * side,
            r"p_{ABC}": 3 * side / 2,
            r"\sin60^{\circ}": sp.sqrt(3) / 2,
        }
    if m.mode == "isosceles_right_radius":
        return {
            "a": a,
            "c": a * sp.sqrt(2),
            "r": a * (2 - sp.sqrt(2)) / 2,
            "S": a * a / 2,
            "P": a * (2 + sp.sqrt(2)),
        }
    if m.mode == "right_radius":
        b = m.given[1]
        hyp = sp.sqrt(a * a + b * b)
        radius = (a + b - hyp) / 2
        return {
            "AC": a,
            "BC": b,
            "AB": hyp,
            "r": radius,
            r"P_{ABC}": a + b + hyp,
            r"S_{ABC}": a * b / 2,
        }
    if m.mode == "isosceles_radius":
        b = m.given[1]
        height = sp.sqrt(a * a - b * b / 4)
        area = b * height / 2
        p = a + b / 2
        return {
            "AB": a,
            "BC": a,
            "AC": b,
            "h": height,
            "p": p,
            "S": area,
            "r": area / p,
        }
    lower = m.given[1]
    leg = a + lower
    return {
        "BK": a,
        "KC": lower,
        "HC": lower,
        "AH": lower,
        "AB": leg,
        "BC": leg,
        r"P_{ABC}": 2 * leg + 2 * lower,
    }


def verify(html, m):
    for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = (
            tag["data-inline-latex"]
            .replace("pr", r"p\cdot r")
            .replace("P_{ABC}r", r"P_{ABC}\cdot r")
        )
        for label, amount in sorted(variables(m).items(), key=lambda x: -len(x[0])):
            prefix = "" if label.startswith("\\") else r"(?<![A-Za-z_])"
            formula = re.sub(
                prefix + re.escape(label) + r"(?![A-Za-z_])",
                lambda _, v=amount: "(" + sp.latex(v) + ")",
                formula,
            )
        formula = formula.replace(r"^{\circ}", "")
        # The expression parser bounds integers; reduce exact integer roots first.
        formula = re.sub(
            r"\\sqrt\{(\d+)\}",
            lambda match: sp.latex(sp.sqrt(int(match[1]))),
            formula,
        )
        amounts = [TrigonometricParser(v).parse().value for v in formula.split("=")]
        assert len(amounts) > 1, formula
        assert all(sp.simplify(v - amounts[0]) == 0 for v in amounts), formula


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_feasible_native_answers_and_each_parent_equality(case):
    m, result = read(case["context"]), plan(case)
    soup = BeautifulSoup(section(case["context"], "answer")["html"], "html.parser")
    tag = soup.select_one("[data-inline-latex]")
    saved = tag["data-inline-latex"] if tag else soup.get_text(strip=True)
    expected = "18" if case["task"] == "56873" else saved
    assert (
        sp.simplify(
            ScalarParser(result.answer).parse() - ScalarParser(expected).parse()
        )
        == 0
    )
    html = solution_html(result)
    verify(html, m)
    soup = BeautifulSoup(html, "html.parser")
    assert [s["data-solution-title"] for s in soup.select("section")] == TITLES.get(
        m.mode, ["Решение"]
    )
    assert len(soup.find_all("img")) == (1 if m.mode == "tangent_perimeter" else 0)
    if m.mode == "isosceles_radius":
        assert "Герона" in soup.get_text() and r"S=\frac{AC\cdot h}{2}" in html
    if m.mode == "equilateral_radius_side":
        assert "Примечание." in soup.get_text()
    if m.mode == "tangent_perimeter":
        assert "общую гипотенузу OC" in soup.get_text()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_immutable_conditions_saved_answer_unused_and_empty_replay(case):
    context = deepcopy(case["context"])
    section(context, "answer")["html"] = "<p>999</p>"
    before = deepcopy(context)
    result = plan(case, context)
    assert context == before and result.answer == plan(case).answer
    replay(context, result.transformations)
    assert plan(case, context).transformations == ()
    for state in (context, before):
        assert read(state) == read(case["context"])
    old = BeautifulSoup(section(before, "condition")["html"], "html.parser")
    new = BeautifulSoup(section(context, "condition")["html"], "html.parser")
    assert new.get_text() == old.get_text()
    assert [t["data-inline-latex"] for t in new.select("[data-inline-latex]")] == [
        t["data-inline-latex"] for t in old.select("[data-inline-latex]")
    ]
    assert section(context, "source") == section(before, "source")


@pytest.mark.parametrize("case", REJECTED_CASES, ids=lambda c: c["task"])
def test_impossible_native_triangle_data_cannot_prepare_a_formal_answer(case):
    before = deepcopy(case["context"])
    with pytest.raises(ContentPlanError, match="nondegenerate figure"):
        plan(case)
    assert case["context"] == before
    condition = section(before, "condition")["html"]
    m = re.search(r"рав(?:ен|на)\s+([^<]+)", condition)
    assert m is not None


@pytest.mark.parametrize(
    "task,old,new,expected", [("56811", "38", "60", "150"), ("56857", "14", "30", "30")]
)
def test_source_id_does_not_control_existence_rejection(task, old, new, expected):
    case = next(c for c in REJECTED_CASES if c["task"] == task)
    context = deepcopy(case["context"])
    condition = section(context, "condition")
    condition["html"] = condition["html"].replace(old, new, 1)
    assert plan(case, context).answer == expected


@pytest.mark.parametrize("group", GROUPS.values(), ids=lambda g: g["key"])
@pytest.mark.parametrize("change", ["html", "primary", "assets"])
def test_profiles_and_full_parent_pins_are_explicit_and_strict(group, change):
    profile, handler = get_group_profile(group["key"]), get_handler(group["rule"])
    assert (
        profile.source_group_id == group["group_uuid"]
        and profile.existing_solution_policy == "rewrite"
    )
    assert (
        handler.parent_from_group_listing
        and handler.requires_frozen_manifest
        and handler.strict_frozen_input
        and handler.verify_content_readback
    )
    handler.validate()
    args = arguments(group["key"])
    override = (
        {"parent_solution_html": args["parent_solution_html"] + "<p>Иной метод</p>"}
        if change == "html"
        else {"parent_asset_id": "foreign"}
        if change == "primary"
        else {
            "parent_solution_assets": (
                {
                    "asset_key": "image_9",
                    "source_asset_id": "foreign",
                    "url": "/assets/foreign",
                },
            )
        }
    )
    case = next(c for c in CASES if c["task"] == group["key"])
    with pytest.raises(ContentPlanError):
        plan(case, **override)


@pytest.mark.parametrize(
    "html,expected",
    [
        (
            r'Периметр треугольника равен <span data-inline-latex="6\sqrt{3}"></span>, а радиус вписанной окружности равен 1. Найдите площадь этого треугольника.',
            3 * sp.sqrt(3),
        ),
        (
            r'Площадь треугольника равна <span data-inline-latex="3\sqrt{3}"></span>, а радиус вписанной окружности равен 1. Найдите периметр этого треугольника.',
            6 * sp.sqrt(3),
        ),
        (
            "Окружность, вписанная в равнобедренный треугольник, делит в точке касания одну из боковых сторон на два отрезка, длины которых равны 3 и 5, считая от вершины, противолежащей основанию. Найдите периметр треугольника.",
            26,
        ),
    ],
)
def test_exact_existence_boundary_and_ordered_tangent_parts(html, expected):
    assert sp.simplify(read_question("<p>" + html + "</p>").answer - expected) == 0


@pytest.mark.parametrize(
    "html",
    [
        "Периметр треугольника равен 10, а радиус вписанной окружности равен 1. Найдите площадь этого треугольника.",
        "Площадь треугольника равна 5, а радиус вписанной окружности равен 1. Найдите периметр этого треугольника.",
        "Около окружности, радиус которой равен 1, описан многоугольник, периметр которого равен 6. Найдите его площадь.",
        "Боковые стороны равнобедренного треугольника равны 3, основание равно 6. Найдите радиус вписанной окружности.",
        "В треугольнике ABC стороны AC = 4, BC = 3, угол C равен 60°. Найдите радиус вписанной окружности.",
        "Найдите радиус окружности, вписанной в правильный треугольник, высота которого равна 0.",
        "Катеты равнобедренного прямоугольного треугольника равны -2. Найдите радиус окружности, вписанной в этот треугольник.",
        "Найдите радиус окружности, вписанной в правильный треугольник, высота которого равна 6. Округлите ответ.",
    ],
)
def test_impossible_or_additional_conditions_fail_closed(html):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + html + "</p>")
