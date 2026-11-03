"""Verify exact answers, every proof equality, parent methods and invalid questions."""

import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from circle_angle_source_cases import CASES, GROUPS, arguments, plan, read
from midpoint_source_cases import replay, section, solution_html

from solution_runner.pipelines.circles.angle_model import read_question
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser


def variables(m):
    a = m.given[0]
    if m.mode == "central_difference":
        return {r"\alpha": a, r"\angle AOB": 2 * a, r"\angle ACB": a}
    if m.mode == "difference_equation":
        return {"x": a, r"\beta": 2 * a}
    if m.mode == "fraction":
        return {
            "f": a / 100 if m.percent else a,
            r"\alpha": m.answer,
            r"\angle ABC": m.answer,
        }
    if m.mode == "two_arcs":
        return {
            r"\overset{\frown}{AC}": a,
            r"\overset{\frown}{BC}": m.given[1],
            r"\overset{\frown}{AB}": 360 - sum(m.given),
            r"\angle ACB": m.answer,
        }
    if m.mode.startswith("diameters_"):
        central = m.answer if m.mode == "diameters_central" else a
        inscribed = a if m.mode == "diameters_central" else m.answer
        return {
            r"\angle ACB": inscribed,
            r"\angle AOD": central,
            r"\angle AOB": 2 * inscribed,
            r"\overset{\frown}{BAD}": 180,
            r"\overset{\frown}{AD}": central,
            r"\overset{\frown}{AB}": 2 * inscribed,
        }
    return {
        "x": m.answer,
        r"\overset{\frown}{DE}": 2 * m.answer,
        r"\overset{\frown}{AB}": m.given[1],
        r"\angle ACB": a,
    }


def verify(html, model):
    for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = tag["data-inline-latex"]
        formula = re.sub(r"(\d+)\\%", lambda m: r"\frac{" + m[1] + "}{100}", formula)
        for label, amount in sorted(variables(model).items(), key=lambda x: -len(x[0])):
            formula = re.sub(
                r"(?<![A-Za-z_])" + re.escape(label) + r"(?![A-Za-z_])",
                lambda _, v=amount: "(" + sp.latex(v) + ")",
                formula,
            )
        formula = formula.replace(r"^{\circ}", "")
        numbers = [
            TrigonometricParser(part).parse().value for part in formula.split("=")
        ]
        assert len(numbers) > 1, formula
        assert all(sp.simplify(v - numbers[0]) == 0 for v in numbers), formula


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_answers_and_each_equality_keep_parent_methods(case):
    model, result = read(case["context"]), plan(case)
    saved = BeautifulSoup(
        section(case["context"], "answer")["html"], "html.parser"
    ).get_text(strip=True)
    assert sp.Rational(result.answer.replace(",", ".")) == sp.Rational(
        saved.replace(",", ".")
    )
    html = solution_html(result)
    verify(html, model)
    soup = BeautifulSoup(html, "html.parser")
    titles = [s["data-solution-title"] for s in soup.select("section")]
    assert titles == (
        ["Решение", "Приведем другое решение"]
        if case["group"] == "27870"
        else ["Решение"]
    )
    assert len(soup.find_all("img")) == (1 if case["group"] == "245385" else 0)
    if model.mode == "central_difference":
        assert r"2\alpha-\alpha" in html
    if model.mode == "difference_equation":
        assert "2x-x" in html
    if model.mode == "secants":
        assert "полуразности" in soup.get_text()
    if case["task"] == "508309":
        assert model.central and result.answer == "72"
        assert "Требуется центральный угол" in soup.get_text()


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
    prose = []
    for ctx in (context, before):
        soup = BeautifulSoup(section(ctx, "condition")["html"], "html.parser")
        for image in soup.find_all("img"):
            image.decompose()
        prose.append(str(soup))
    assert prose[0] == prose[1]


@pytest.mark.parametrize("group", GROUPS.values(), ids=lambda g: g["key"])
@pytest.mark.parametrize("change", ["html", "primary", "assets"])
def test_profiles_strict_runtime_and_complete_parent_pins(group, change):
    profile, handler = get_group_profile(group["key"]), get_handler(group["rule"])
    assert profile.source_group_id == group["group_uuid"]
    assert profile.existing_solution_policy == "rewrite"
    assert handler.parent_from_group_listing and handler.requires_frozen_manifest
    assert handler.strict_frozen_input and handler.verify_content_readback
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
            "Найдите вписанный угол, опирающийся на дугу, которая составляет 15% окружности. Ответ дайте в градусах.",
            27,
        ),
        (
            "Найдите вписанный угол ABC, опирающийся на дугу AC, длина которой равна 0,25 длины окружности. Ответ дайте в градусах.",
            45,
        ),
        (
            "Центральный угол окружности на 12,5° больше вписанного угла, опирающегося на ту же дугу данной окружности. Найдите центральный угол. Ответ дайте в градусах.",
            25,
        ),
    ],
)
def test_percent_decimal_and_different_requested_angle_are_read_exactly(html, expected):
    assert read_question("<p>" + html + "</p>").answer == expected


@pytest.mark.parametrize(
    "html",
    [
        "Найдите центральный угол AOB, если он на 20%° больше вписанного угла ACB, опирающегося на ту же дугу. Ответ дайте в градусах.",
        "Дуга окружности AC, не содержащая точки B, составляет 200%°. А дуга окружности BC, не содержащая точки A, составляет 80°. Найдите вписанный угол ACB. Ответ дайте в градусах.",
        "Найдите центральный угол AOB, если он на 91° больше вписанного угла ACB, опирающегося на ту же дугу. Ответ дайте в градусах.",
        "Центральный угол на 90° больше острого вписанного угла, опирающегося на ту же дугу окружности. Найдите вписанный угол. Ответ дайте в градусах.",
        "Найдите вписанный угол, опирающийся на дугу, которая составляет 100% окружности. Ответ дайте в градусах.",
        "Найдите вписанный угол, опирающийся на дугу, которая составляет 0 окружности. Ответ дайте в градусах.",
        "Дуга окружности AC, не содержащая точки B, составляет 200°. А дуга окружности BC, не содержащая точки A, составляет 160°. Найдите вписанный угол ACB. Ответ дайте в градусах.",
        "В окружности с центром O отрезки AC и BD — диаметры. Вписанный угол ACB равен 90°. Найдите центральный угол AOD. Ответ дайте в градусах.",
        "В окружности с центром O отрезки AC и BD — диаметры. Центральный угол AOD равен 180°. Найдите вписанный угол ACB. Ответ дайте в градусах.",
        "Угол ACB равен 70°. Градусная мера дуги AB окружности, не содержащей точек D и E, равна 124°. Найдите угол DAE. Ответ дайте в градусах.",
        "Угол ACB равен 10°. Градусная мера дуги AB окружности, не содержащей точек D и E, равна 300°. Найдите угол DAE. Ответ дайте в градусах.",
        "Найдите вписанный угол, опирающийся на дугу, которая составляет 15% окружности. Ответ дайте в градусах. Округлите ответ.",
    ],
)
def test_impossible_and_unreviewed_questions_fail_closed(html):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + html + "</p>")
