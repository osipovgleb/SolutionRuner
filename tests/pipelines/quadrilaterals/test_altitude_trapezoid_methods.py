"""Check parent methods, exact answers, general angles and immutable replay."""

import math
import re
from copy import deepcopy

import pytest
import sympy as sp
from altitude_trapezoid_source_cases import CASES, GROUPS, arguments, plan, read
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.quadrilaterals.parallelogram.rectangle_proofs import (
    value,
)
from solution_runner.pipelines.quadrilaterals.trapezoid.altitude_model import (
    read_question,
)
from solution_runner.pipelines.quadrilaterals.trapezoid.altitude_proofs import render
from solution_runner.pipelines.quadrilaterals.trapezoid.quantity_parent import FAMILIES
from solution_runner.pipelines.quadrilaterals.trapezoid.quantity_sources import PARENTS


def test_shared_quantity_preparer_and_parent_registry_have_the_same_exact_keys():
    assert set(FAMILIES) == set(PARENTS)


def scalar(expr):
    expr = sp.sympify(expr)
    if expr.has(sp.asin, sp.atan):
        amount = float(expr)
        decimals = 8 - math.floor(math.log10(abs(amount)))
        return sp.latex(sp.Rational(str(round(amount, decimals))))
    return sp.latex(expr)


def verify(html, m):
    variables = {
        "AD": m.large,
        "BC": m.small,
        "S": m.area,
        r"S_{ABCD}": m.area,
        "AB": m.height if m.right else m.leg,
        "CD": m.leg
        if m.right
        else sp.sqrt(m.height**2 + (m.large - m.small - m.offset) ** 2),
        "CH": m.height,
        "BH": m.height,
        "h": m.height,
        "HD": m.projection,
        "AH": m.offset,
    }
    special = {
        r"\angle CDA": m.angle if m.right else 90,
        r"\angle CDH": m.angle if m.right else 90,
        r"\angle HCD": 90 - m.angle if m.right else 90,
        r"\angle BAD": 90 if m.right else m.angle,
        r"\sin\angle BAD": m.sine,
        r"\tg\angle CDA": m.tangent,
    }
    inverse = {
        r"\arctan\left(" + value(m.tangent) + r"\right)": sp.pi * m.angle / 180,
        r"\arcsin\left(" + value(m.sine) + r"\right)": sp.pi * m.angle / 180,
    }
    for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = tag["data-inline-latex"]
        if m.angle.has(sp.asin, sp.atan):
            formula = formula.replace(value(m.angle), "(" + scalar(m.angle) + ")")
        for label, amount in inverse.items():
            formula = formula.replace(label, "(" + scalar(amount) + ")")
        if m.mode == "right_area":
            label = r"\tg" + value(m.given[2]) + r"^{\circ}"
            formula = formula.replace(label, "(" + scalar(m.tangent) + ")")
        for label, amount in sorted(special.items(), key=lambda v: -len(v[0])):
            formula = formula.replace(label, "(" + scalar(amount) + ")")
        for label, amount in sorted(variables.items(), key=lambda v: -len(v[0])):
            formula = re.sub(
                r"(?<![A-Za-z_])" + re.escape(label) + r"(?![A-Za-z_])",
                lambda _, v=amount: "(" + scalar(v) + ")",
                formula,
            )
        formula = formula.replace(r"^{\circ}", "").replace(
            r"\pi", r"\frac{314159265}{100000000}"
        )
        numbers = [
            float(TrigonometricParser(v).parse().value) for v in formula.split("=")
        ]
        assert len(numbers) > 1, formula
        assert all(
            math.isclose(v, numbers[0], rel_tol=1e-8, abs_tol=2e-7) for v in numbers
        ), formula


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_answers_parent_methods_and_each_equality(case):
    model = read(case["context"])
    result = plan(case)
    saved = BeautifulSoup(
        section(case["context"], "answer")["html"], "html.parser"
    ).get_text(strip=True)
    assert float(result.answer.replace(",", ".")) == float(saved.replace(",", "."))
    html = solution_html(result)
    verify(html, model)
    soup = BeautifulSoup(html, "html.parser")
    assert [s["data-solution-title"] for s in soup.select("section")] == ["Решение"]
    assert len(soup.find_all("img")) == 1
    if model.mode == "right_angle":
        assert "равнобедренный" in soup.get_text()
    if model.mode == "side_angle":
        assert "половине гипотенузы" in soup.get_text()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_immutable_input_saved_answer_unused_and_empty_replay(case):
    context = deepcopy(case["context"])
    section(context, "answer")["html"] = "<p>999</p>"
    before = deepcopy(context)
    result = plan(case, context)
    assert context == before and result.answer == plan(case).answer
    replay(context, result.transformations)
    assert plan(case, context).transformations == ()
    assert section(context, "source") == section(before, "source")
    assert len(context["normalized_content"]["assets"]) == 2
    prose = []
    for ctx in (context, before):
        soup = BeautifulSoup(section(ctx, "condition")["html"], "html.parser")
        for image in soup.find_all("img"):
            image.decompose()
        prose.append(str(soup))
    assert prose[0] == prose[1]


@pytest.mark.parametrize("g", GROUPS.values(), ids=lambda g: g["key"])
@pytest.mark.parametrize("change", ["html", "source", "assets"])
def test_profiles_strict_frozen_runtime_and_complete_parent_pins(g, change):
    profile, handler = get_group_profile(g["key"]), get_handler(g["rule"])
    assert (
        profile.source_group_id == g["group_uuid"]
        and profile.existing_solution_policy == "rewrite"
    )
    assert (
        handler.parent_from_group_listing
        and handler.requires_frozen_manifest
        and handler.strict_frozen_input
        and handler.verify_content_readback
    )
    handler.validate()
    case = next(c for c in CASES if c["task"] == g["key"])
    override = (
        {
            "parent_solution_html": arguments(g["key"])["parent_solution_html"]
            + "<p>Иной метод.</p>"
        }
        if change == "html"
        else (
            {"parent_asset_id": "foreign"}
            if change == "source"
            else {"parent_solution_assets": ()}
        )
    )
    with pytest.raises(ContentPlanError):
        plan(case, **override)


@pytest.mark.parametrize(
    "html,expected",
    [
        (
            "Найдите площадь прямоугольной трапеции, основания которой равны 6 и 2, большая боковая сторона составляет с основанием угол 30°.",
            16 * sp.sqrt(3) / 3,
        ),
        (
            "Основания прямоугольной трапеции равны 2 и 6. Ее площадь равна 12. Найдите острый угол этой трапеции. Ответ дайте в градусах.",
            180 * sp.atan(sp.Rational(3, 4)) / sp.pi,
        ),
        (
            "Основания трапеции равны 1 и 4, боковая сторона равна 5. Площадь трапеции равна 7,5. Найдите острый угол трапеции, прилежащий к данной боковой стороне. Ответ дайте в градусах.",
            180 * sp.asin(sp.Rational(3, 5)) / sp.pi,
        ),
        (
            "Основания трапеции равны 6 и 12, боковая сторона равна 5. Площадь трапеции равна 36. Найдите острый угол трапеции, прилежащий к данной боковой стороне. Ответ дайте в градусах.",
            180 * sp.asin(sp.Rational(4, 5)) / sp.pi,
        ),
    ],
)
def test_other_exact_angles_follow_trigonometry_and_keep_the_note_truthful(
    html, expected
):
    model = read_question("<p>" + html + "</p>")
    assert sp.simplify(model.answer - expected) == 0
    rendered = render(model, {"height": ""})
    verify(rendered, model)
    if model.is_isosceles:
        assert "Данные допускают равнобедренную трапецию" in rendered


@pytest.mark.parametrize(
    "html",
    [
        "Найдите площадь прямоугольной трапеции, основания которой равны 6 и 6, большая боковая сторона составляет с основанием угол 45°.",
        "Найдите площадь прямоугольной трапеции, основания которой равны 6 и 2, большая боковая сторона составляет с основанием угол 90°.",
        "Основания прямоугольной трапеции равны 2 и 6. Ее площадь равна 0. Найдите острый угол этой трапеции. Ответ дайте в градусах.",
        "Основания трапеции равны 6 и 12, боковая сторона равна 4. Площадь трапеции равна 36. Найдите острый угол трапеции, прилежащий к данной боковой стороне. Ответ дайте в градусах.",
        "Основания трапеции равны 6 и 12, боковая сторона, равная 4, образует с одним из оснований трапеции угол 180°. Найдите площадь трапеции.",
        "Основания трапеции равны 6 и 12, боковая сторона, равная 4, образует с одним из оснований трапеции угол 150°. Найдите площадь трапеции. Округлите ответ.",
    ],
)
def test_impossible_angles_degeneracy_and_extra_instructions_fail_closed(html):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + html + "</p>")
