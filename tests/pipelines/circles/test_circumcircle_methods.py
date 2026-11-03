"""Exact regular-triangle circumradii and each equality in every parent method."""

import re
from copy import deepcopy

import circumcircle_quantity_cases
import pytest
import sympy as sp
from bs4 import BeautifulSoup
from circumcircle_source_cases import CASES, GROUPS, arguments, plan, read
from midpoint_source_cases import replay, section, solution_html

from solution_runner.pipelines.circles.circumcircle_model import read_question
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.power_arithmetic import ScalarParser
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser

TITLES = {
    "radius_side": ["Решение", "Приведем другое решение."],
    "side_radius": ["Решение"],
    "radius_height": ["Решение", "Приведём другое решение."],
    "height_radius": ["Решение", "Приведем другое решение."],
}


def variables(m):
    if m.mode in circumcircle_quantity_cases.MODES:
        return circumcircle_quantity_cases.variables(m)
    v = m.given[0]
    radius = {
        "radius_side": v / sp.sqrt(3),
        "side_radius": v,
        "radius_height": 2 * v / 3,
        "height_radius": v,
    }[m.mode]
    side, height = sp.sqrt(3) * radius, 3 * radius / 2
    return {
        "R": radius,
        "a": side,
        "h": height,
        "AC": side,
        "CB": side,
        "CH": height,
        "CO": radius,
        "OC": radius,
        "OH": radius / 2,
        r"\sin A": sp.sqrt(3) / 2,
        r"\sin B": sp.sqrt(3) / 2,
        r"\sin60^{\circ}": sp.sqrt(3) / 2,
        r"\sin^2 60^{\circ}": sp.Rational(3, 4),
    }


def verify(html, m):
    for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = tag["data-inline-latex"]
        for label, amount in sorted(
            variables(m).items(), key=lambda pair: -len(pair[0])
        ):
            prefix = "" if label.startswith("\\") else r"(?<![A-Za-z_])"
            formula = re.sub(
                prefix + re.escape(label) + r"(?![A-Za-z_])",
                lambda _, a=amount: "(" + sp.latex(a) + ")",
                formula,
            )
        formula = formula.replace(r"^{\circ}", "")
        values = [TrigonometricParser(v).parse().value for v in formula.split("=")]
        assert len(values) > 1 and all(
            sp.simplify(v - values[0]) == 0 for v in values
        ), formula


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_native_answer_and_each_equality_keep_all_parent_methods(case):
    result = plan(case)
    model = read(case["context"])
    soup = BeautifulSoup(section(case["context"], "answer")["html"], "html.parser")
    tag = soup.select_one("[data-inline-latex]")
    saved = tag["data-inline-latex"] if tag else soup.get_text(strip=True)
    assert (
        sp.simplify(ScalarParser(result.answer).parse() - ScalarParser(saved).parse())
        == 0
    )
    html = solution_html(result)
    verify(html, model)
    soup = BeautifulSoup(html, "html.parser")
    assert [s["data-solution-title"] for s in soup.select("section")] == TITLES.get(
        model.mode, ["Решение"]
    )
    assert len(soup.find_all("img")) == (1 if model.mode == "hexagon_side" else 0)
    if model.mode == "radius_side":
        assert (
            soup.select("section")[1].find("b").get_text()
            == "Приведем еще одно решение."
        )
    if model.mode == "height_radius":
        assert (
            "серединных перпендикуляров" in soup.get_text()
            and "Медианы" in soup.get_text()
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_source_immutability_saved_answer_unused_and_empty_replay(case):
    context = deepcopy(case["context"])
    section(context, "answer")["html"] = "<p>999</p>"
    before = deepcopy(context)
    result = plan(case, context)
    assert context == before and result.answer == plan(case).answer
    replay(context, result.transformations)
    assert plan(case, context).transformations == ()
    for ctx in (context, before):
        soup = BeautifulSoup(section(ctx, "condition")["html"], "html.parser")
        for image in soup.find_all("img"):
            image.decompose()
        section(ctx, "condition")["html"] = str(soup)
    assert section(context, "condition")["html"] == section(before, "condition")["html"]
    assert section(context, "source") == section(before, "source")


@pytest.mark.parametrize("group", GROUPS.values(), ids=lambda g: g["key"])
@pytest.mark.parametrize("change", ["html", "primary", "assets"])
def test_complete_parent_pins_and_strict_profiles(group, change):
    profile = get_group_profile(group["key"])
    handler = get_handler(group["rule"])
    handler.validate()
    assert (
        profile.source_group_id == group["group_uuid"]
        and profile.existing_solution_policy == "rewrite"
    )
    assert handler.parent_from_group_listing and handler.requires_frozen_manifest
    assert handler.strict_frozen_input and handler.verify_content_readback
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
    "html",
    [
        "Сторона правильного треугольника равна 0. Найдите радиус окружности, описанной около этого треугольника.",
        "Высота правильного треугольника равна -3. Найдите радиус окружности, описанной около этого треугольника.",
        "Радиус окружности, описанной около правильного треугольника, равен 0. Найдите сторону этого треугольника.",
        "Радиус окружности, описанной около правильного треугольника, равен -2. Найдите высоту этого треугольника.",
        "Высота правильного треугольника равна 3. Найдите радиус окружности, описанной около этого треугольника. Округлите ответ.",
        "Сторона треугольника равна 3. Найдите радиус окружности, описанной около этого треугольника.",
        "Радиус окружности, вписанной в правильный треугольник, равен 3. Найдите высоту этого треугольника.",
    ],
)
def test_degenerate_extra_or_different_conditions_fail_closed(html):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + html + "</p>")


@pytest.mark.parametrize(
    "html,expected",
    [
        (
            r'Сторона правильного треугольника равна <span data-inline-latex="2+\sqrt{2}"></span>. Найдите радиус окружности, описанной около этого треугольника.',
            (2 + sp.sqrt(2)) / sp.sqrt(3),
        ),
        (
            r'Радиус окружности, описанной около правильного треугольника, равен <span data-inline-latex="2+\sqrt{2}"></span>. Найдите сторону этого треугольника.',
            (2 + sp.sqrt(2)) * sp.sqrt(3),
        ),
        (
            r'Высота правильного треугольника равна <span data-inline-latex="2+\sqrt{2}"></span>. Найдите радиус окружности, описанной около этого треугольника.',
            2 * (2 + sp.sqrt(2)) / 3,
        ),
        (
            r'Радиус окружности, описанной около правильного треугольника, равен <span data-inline-latex="2+\sqrt{2}"></span>. Найдите высоту этого треугольника.',
            3 * (2 + sp.sqrt(2)) / 2,
        ),
    ],
)
def test_exact_composite_positive_lengths(html, expected):
    assert sp.simplify(read_question("<p>" + html + "</p>").answer - expected) == 0


@pytest.mark.parametrize("group", GROUPS)
def test_parent_method_cannot_be_replaced_with_a_different_requested_quantity(group):
    case = next(c for c in CASES if c["task"] == group)
    other = next(c for c in CASES if c["task"] == c["group"] and c["group"] != group)
    with pytest.raises(ContentPlanError, match="differs from its parent method"):
        plan(case, deepcopy(other["context"]))
