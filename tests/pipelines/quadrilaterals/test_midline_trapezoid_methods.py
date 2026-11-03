"""Check answers, every equality, parent methods and unsupported scalar inputs."""

import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midline_trapezoid_source_cases import CASES, GROUPS, arguments, plan, read
from midpoint_source_cases import replay, section, solution_html

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.quadrilaterals.trapezoid.midline_model import (
    read_question,
)


def variables(m):
    a = m.given[0]
    b = m.given[1] if len(m.given) == 2 else None
    if m.mode == "angle_difference":
        return {r"\angle C": (180 + a) / 2, r"\angle A": (180 - a) / 2}
    if m.mode == "large_base":
        return {"m": a, "a": b, "x": 2 * a - b}
    if m.mode == "cut_perimeter":
        side = b / 3
        return {
            "AB": side,
            "BC": a,
            "CD": side,
            "AD": side + a,
            "BE": side,
            "AE": side,
            "ED": a,
            r"P_{ABCD}": b + 2 * a,
            r"P_{ABE}": b,
        }
    if m.mode == "perimeter_midline":
        gap = min(a - b, b) / 2
        return {
            "AD": (a - b + gap) / 2,
            "BC": (a - b - gap) / 2,
            "AB": b / 2,
            "CD": b / 2,
            "EF": (a - b) / 2,
            r"P_{ABCD}": a,
        }
    if m.mode == "perpendicular":
        return {
            "AD": 3 * a / 2,
            "BC": a / 2,
            "OE": 3 * a / 4,
            "OF": a / 4,
            "EF": a,
            "h": a,
            "m": a,
        }
    small, large = sorted((a, b))
    if m.mode == "base_parts":
        return {
            "AE": large,
            "ED": small,
            "AD": large + small,
            "BC": large - small,
            "m": large,
        }
    return {
        "AD": large,
        "BC": small,
        "EO": large / 2,
        "OF": small / 2,
        "EK": small / 2,
        "FM": small / 2,
        "KM": (large + small) / 2,
        "EF": (large - small) / 2,
    }


def verify_equalities(html, model):
    for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = tag["data-inline-latex"]
        for label, amount in sorted(variables(model).items(), key=lambda x: -len(x[0])):
            formula = re.sub(
                r"(?<![A-Za-z_])" + re.escape(label) + r"(?![A-Za-z_])",
                lambda _, v=amount: "(" + sp.latex(v) + ")",
                formula,
            )
        formula = formula.replace(r"\begin{cases}", "").replace(r"\end{cases}", "")
        formula = formula.replace(r"^{\circ}", "")
        for row in formula.split(r"\\"):
            amounts = [
                TrigonometricParser(expr).parse().value for expr in row.split("=")
            ]
            assert len(amounts) > 1, formula
            assert all(sp.simplify(v - amounts[0]) == 0 for v in amounts), formula


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_answers_equalities_and_parent_methods(case):
    result = plan(case)
    saved = BeautifulSoup(
        section(case["context"], "answer")["html"], "html.parser"
    ).get_text(strip=True)
    expected = "55" if case["task"] == "49803" else saved
    assert sp.Rational(result.answer.replace(",", ".")) == sp.Rational(
        expected.replace(",", ".")
    )
    model = read(case["context"])
    html = solution_html(result)
    verify_equalities(html, model)
    soup = BeautifulSoup(html, "html.parser")
    assert [s["data-solution-title"] for s in soup.select("section")] == (
        ["Решение", "Приведём другое решение"]
        if case["group"] == "27843"
        else ["Решение"]
    )
    assert len(soup.find_all("img")) == (1 if case["group"] == "27843" else 0)
    if model.mode == "angle_difference":
        assert r"\begin{cases}" in html
    if model.mode == "diagonal_piece":
        assert "ABD" in soup.get_text() and r"EO=\frac{AD}{2}" in html
    if model.mode == "perpendicular":
        assert "медианы" in soup.get_text() and "оси симметрии" in soup.get_text()
    assert not soup.find("a") and "Открытом банке" not in soup.get_text()
    assert "---" not in soup.get_text()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_sources_unchanged_saved_answer_unused_and_replay_empty(case):
    context = deepcopy(case["context"])
    section(context, "answer")["html"] = "<p>999</p>"
    before = deepcopy(context)
    result = plan(case, context)
    assert context == before and result.answer == plan(case).answer
    replay(context, result.transformations)
    assert plan(case, context).transformations == ()
    assert section(context, "condition") == section(before, "condition")
    assert section(context, "source") == section(before, "source")
    assert (
        context["normalized_content"]["assets"]
        == before["normalized_content"]["assets"]
    )


@pytest.mark.parametrize("group", GROUPS.values(), ids=lambda g: g["key"])
@pytest.mark.parametrize("change", ["html", "primary", "assets"])
def test_exact_parent_pins_and_strict_profile_bindings(group, change):
    profile, handler = get_group_profile(group["key"]), get_handler(group["rule"])
    assert profile.source_group_id == group["group_uuid"]
    assert profile.existing_solution_policy == "rewrite"
    assert handler.parent_from_group_listing and handler.requires_frozen_manifest
    assert handler.strict_frozen_input and handler.verify_content_readback
    handler.validate()
    args = arguments(group["key"])
    override = (
        {"parent_solution_html": args["parent_solution_html"] + "<p>Другой метод</p>"}
        if change == "html"
        else {"parent_asset_id": "foreign"}
        if change == "primary"
        else {
            "parent_solution_assets": (
                {
                    "asset_key": "image_9",
                    "asset_id": "foreign",
                    "url": "/assets/foreign",
                },
            )
        }
    )
    case = next(c for c in CASES if c["task"] == group["key"])
    with pytest.raises(ContentPlanError):
        plan(case, **override)


@pytest.mark.parametrize(
    "html,answer",
    [
        (
            "Средняя линия трапеции равна 3,5, а меньшее основание равно 2. Найдите большее основание трапеции.",
            5,
        ),
        (
            "Основания трапеции равны 8 и 2. Найдите отрезок, соединяющий середины диагоналей трапеции.",
            3,
        ),
        (
            "Перпендикуляр, опущенный из вершины тупого угла на большее основание равнобедренной трапеции, делит его на части, имеющие длины 4 и 10. Найдите среднюю линию этой трапеции.",
            10,
        ),
        (
            "В равнобедренной трапеции диагонали перпендикулярны. Высота трапеции равна 1,5. Найдите её среднюю линию.",
            sp.Rational(3, 2),
        ),
    ],
)
def test_decimal_inputs_reverse_order_and_yo_are_exact(html, answer):
    assert read_question("<p>" + html + "</p>").answer == answer


@pytest.mark.parametrize(
    "html",
    [
        "Чему равен больший угол равнобедренной трапеции, если известно, что разность противолежащих углов равна 180°? Ответ дайте в градусах.",
        "Средняя линия трапеции равна 2, а меньшее основание равно 3. Найдите большее основание трапеции.",
        "Средняя линия трапеции равна 2, а меньшее основание равно 2. Найдите большее основание трапеции.",
        "Основания трапеции равны 3 и 3. Найдите больший из отрезков, на которые делит среднюю линию этой трапеции одна из ее диагоналей.",
        "Основания трапеции равны 3 и 3. Найдите отрезок, соединяющий середины диагоналей трапеции.",
        "Перпендикуляр, опущенный из вершины тупого угла на большее основание равнобедренной трапеции, делит его на части, имеющие длины 4 и 4. Найдите среднюю линию этой трапеции.",
        "Периметр трапеции равен 20, а сумма непараллельных сторон равна 20. Найдите среднюю линию трапеции.",
        "В равнобедренной трапеции диагонали перпендикулярны. Высота трапеции равна 0. Найдите ее среднюю линию.",
        "Средняя линия трапеции равна 5, а меньшее основание равно 3. Найдите большее основание трапеции. Округлите ответ.",
    ],
)
def test_impossible_and_unreviewed_questions_fail_closed(html):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + html + "</p>")
