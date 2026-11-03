"""Native linear methods, each formula, ambiguity, and source ownership."""

import math
import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from linear_source_cases import CASES, GROUPS, arguments, plan
from midpoint_source_cases import replay, section, solution_html
from test_parallelogram_quantity_model import read

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.quadrilaterals.parallelogram.quantity_model import (
    read_question,
)


def verify(html, m):
    vals = {
        r"\angle A": m.first,
        r"\angle B": m.second,
        r"\angle D": m.second,
        "AB": m.first,
        "AD": m.second,
    }
    if m.mode == "angle_split":
        vals.update({r"\angle BAC": m.given[0], r"\angle CAD": m.given[1]})
    if m.mode == "angle_sum":
        vals.update(x=m.first, y=m.second)
    if m.mode.startswith("side_"):
        vals["P"] = m.given[2] if m.mode == "side_ratio" else m.given[0]
        if m.mode == "side_ratio":
            vals["x"] = vals["P"] / (2 * sum(m.given[:2]))
    for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = tag["data-inline-latex"].replace(
            r"\max(\angle A,\angle B)", sp.latex(m.answer)
        )
        for label, val in sorted(vals.items(), key=lambda v: -len(v[0])):
            if label.startswith("\\angle"):
                formula = formula.replace(label, "(" + sp.latex(val) + ")")
                continue
            formula = re.sub(
                r"(?<![A-Za-z_])" + re.escape(label) + r"(?![A-Za-z_])",
                lambda _, v=val: "(" + sp.latex(v) + ")",
                formula,
            )
        formula = formula.replace(r"^{\circ}", "")
        for statement in re.split(r",\s*\\quad\s*", formula):
            values = [
                float(TrigonometricParser(part).parse().value)
                for part in statement.split("=")
            ]
            assert len(values) >= 2, statement
            assert all(
                math.isclose(v, values[0], rel_tol=1e-10, abs_tol=1e-9) for v in values
            ), statement


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answer_every_method_and_formula_and_empty_replay(case):
    context = deepcopy(case["context"])
    model = read(context)
    old_answer = BeautifulSoup(
        section(context, "answer")["html"], "html.parser"
    ).get_text(strip=True)
    before = deepcopy(context)
    result = plan(case, context)
    assert context == before and float(result.answer.replace(",", ".")) == float(
        old_answer.replace(",", ".")
    )
    html = solution_html(result)
    verify(html, model)
    assert [
        s["data-solution-title"]
        for s in BeautifulSoup(html, "html.parser").select("section")
    ] == (
        ["Решение", "Альтернативное решение."]
        if model.mode == "side_ratio"
        else ["Решение"]
    )
    handler = get_handler(GROUPS[case["group"]]["rule"])
    assert handler.diagram_specs(context) == ()
    assert not any(
        t["transformation_target_id"].startswith("asset:")
        for t in result.transformations
    )
    replay(context, result.transformations)
    assert plan(case, context).transformations == ()
    assert section(context, "condition") == section(before, "condition")
    assert (
        context["normalized_content"]["assets"]
        == before["normalized_content"]["assets"]
    )
    section(context, "answer")["html"] = "<p>999</p>"
    assert plan(case, context).answer == result.answer


@pytest.mark.parametrize("g", GROUPS.values(), ids=lambda g: g["key"])
def test_bindings_and_complete_parent_pins(g):
    profile, handler = get_group_profile(g["key"]), get_handler(g["rule"])
    assert (
        profile.source_group_id == g["group_uuid"]
        and profile.existing_solution_policy == "rewrite"
    )
    assert (
        handler.parent_from_group_listing
        and handler.requires_frozen_manifest
        and handler.verify_content_readback
    )
    handler.validate()
    case = next(c for c in CASES if c["task"] == g["key"])
    for change in (
        {
            "parent_solution_html": arguments(g["key"])["parent_solution_html"]
            + "<p>Иной метод.</p>"
        },
        {"parent_asset_id": "foreign"},
        {"parent_solution_assets": ({"asset_key": "image_2"},)},
    ):
        with pytest.raises(ContentPlanError):
            plan(case, **change)


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["task"] == c["group"]], ids=lambda c: c["task"]
)
@pytest.mark.parametrize(
    "change", ["foreign", "extra", "url", "orphan", "instruction", "cross_rule"]
)
def test_unknown_sources_instructions_and_method_crossover_fail_closed(case, change):
    context = deepcopy(case["context"])
    content = context["normalized_content"]
    if change == "foreign":
        content["assets"][0]["asset_id"] = "foreign"
    elif change == "extra":
        content["assets"].append(deepcopy(content["assets"][0]))
    elif change == "url":
        content["assets"][0]["url"] += "?foreign"
    elif change == "orphan":
        section(context, "condition")["html"] = "<p>Нет рисунка.</p>"
    elif change == "instruction":
        section(context, "condition")["html"] += "<p>Округлите ответ.</p>"
    else:
        other = next(c for c in CASES if c["group"] != case["group"])
        context = deepcopy(other["context"])
    with pytest.raises(ContentPlanError):
        plan(case, context)


@pytest.mark.parametrize(
    "html",
    [
        "Сумма двух углов параллелограмма равна 180°. Найдите один из оставшихся углов. Ответ дайте в градусах.",
        "Сумма двух углов параллелограмма равна 360°. Найдите один из оставшихся углов. Ответ дайте в градусах.",
        "Один угол параллелограмма больше другого на 180°. Найдите больший угол. Ответ дайте в градусах.",
        "Диагональ параллелограмма образует с двумя его сторонами углы 100° и 80°. Найдите больший угол параллелограмма. Ответ дайте в градусах.",
        "Найдите больший угол параллелограмма, если два его угла относятся как 1:1. Ответ дайте в градусах.",
        "Периметр параллелограмма равен 40. Одна сторона параллелограмма на 20 больше другой. Найдите меньшую сторону параллелограмма.",
        "Периметр параллелограмма равен 40. Меньшая сторона равна 11. Найдите большую сторону параллелограмма.",
        "Две стороны параллелограмма относятся как 1:1, а периметр его равен 40. Найдите большую сторону параллелограмма.",
        "Две стороны параллелограмма относятся как 0:3, а периметр его равен 40. Найдите большую сторону параллелограмма.",
    ],
)
def test_ambiguous_degenerate_and_impossible_data_fail_closed(html):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + html + "</p>")


@pytest.mark.parametrize(
    "html,expected",
    [
        (
            "Сумма двух углов параллелограмма равна 260°. Найдите один из оставшихся углов. Ответ дайте в градусах.",
            50,
        ),
        (
            "Диагональ параллелограмма образует с двумя его сторонами углы 70° и 50°. Найдите больший угол параллелограмма. Ответ дайте в градусах.",
            120,
        ),
        (
            "Диагональ параллелограмма образует с двумя его сторонами углы 40° и 50°. Найдите больший угол параллелограмма. Ответ дайте в градусах.",
            90,
        ),
        (
            "Найдите больший угол параллелограмма, если два его угла относятся как 7:3. Ответ дайте в градусах.",
            126,
        ),
        (
            "Две стороны параллелограмма относятся как 4:1, а периметр его равен 30. Найдите большую сторону параллелограмма.",
            12,
        ),
    ],
)
def test_reversed_ratios_obtuse_given_angles_and_rectangle_boundary(html, expected):
    model = read_question("<p>" + html + "</p>")
    assert model.answer == expected
    from solution_runner.pipelines.quadrilaterals.parallelogram.linear_proofs import (
        render,
    )

    verify(render(model), model)


def test_native_504250_is_known_side_variant_of_the_perimeter_rule():
    case = next(c for c in CASES if c["task"] == "504250")
    model = read(case["context"])
    assert model.mode == "side_known" and model.first == 16 and model.second == 19
    assert "Одна сторона" not in section(case["context"], "condition")["html"]
    assert plan(case).answer == "19"
