"""Joint marginals, exhaustive admission outcomes and figure consistency."""

from fractions import Fraction as F
from itertools import product
from xml.etree import ElementTree as ET

import pytest
from test_complex_source_samples import CASES, _plan

from solution_runner.pipelines.probability import admission, joint_events, retirement


@pytest.mark.parametrize(
    "cells",
    [
        (F(7, 10), F(1, 10), F(1, 10), F(1, 10)),
        (F(0), F(1, 3), F(2, 3), F(0)),
        (F(0), F(0), F(0), F(1)),
    ],
)
def test_supplied_joint_marginals_recover_each_cell(cells):
    neither, only_b, only_a, both = cells
    actual = joint_events.joint_distribution(only_a + both, only_b + both, both)
    assert actual == cells
    assert sum(actual) == 1
    assert actual[0] == neither


@pytest.mark.parametrize(
    "a,b,j",
    [(F(1, 5), F(1, 5), F(3, 10)), (F(4, 5), F(4, 5), F(1, 10)), (F(-1), F(0), F(0))],
)
def test_inconsistent_joint_data_fail_closed(a, b, j):
    with pytest.raises(ValueError):
        joint_events.joint_distribution(a, b, j)


@pytest.mark.parametrize(
    "probabilities", list(product((F(0), F(2, 5), F(1)), repeat=4))
)
def test_admission_matches_all_sixteen_exam_outcomes(probabilities):
    expected = F(0)
    for outcome in product((False, True), repeat=4):
        m, r, f, s = outcome
        if m and r and (f or s):
            weight = F(1)
            for passed, p in zip(outcome, probabilities, strict=True):
                weight *= p if passed else 1 - p
            expected += weight
    assert admission.admission_probability(*probabilities) == expected


def test_retirement_recovers_a_known_population():
    case = next(c for c in CASES if c["task"] == "509303")
    from copy import deepcopy

    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = (
        "<p>В городе 50% взрослого населения — мужчины. Пенсионеры составляют 25% взрослого населения, причем доля пенсионеров среди женщин равна 10%. Для социологического опроса выбран случайным образом мужчина, проживающий в этом городе. Найдите вероятность события «выбранный мужчина является пенсионером».</p>"
    )
    # 50 women include 5 retirees; the remaining 20 retirees are among 50 men.
    assert _plan(case, context).answer == "0,4"
    condition["html"] = condition["html"].replace("25%", "2%")
    with pytest.raises(ValueError):
        _plan(case, context)


@pytest.mark.parametrize(
    "svg",
    [
        joint_events.render_svg(F(1, 5), F(1, 10)),
        retirement.render_svg(F(1, 2), F(1, 10)),
        admission.render_svg((F(3, 5), F(4, 5), F(3, 5), F(7, 10))),
    ],
)
def test_local_svg_colors_and_probability_text_are_valid(svg):
    tree = ET.fromstring(svg)
    for node in tree.iter():
        if "fill" in node.attrib:
            assert node.attrib["fill"] in ("none", "white") or node.attrib[
                "fill"
            ].startswith("#")
    assert "0,1" in svg or "0,1344" in svg
