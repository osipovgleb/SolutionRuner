"""Native answers, complete proof methods, exact figures and strict requests."""

from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from ratio_prism_geometry_oracle import verify
from ratio_prism_source_cases import CASES, plan

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.distance_figures import selection
from solution_runner.pipelines.solids.spatial_distance_model import condition_text

EXPECTED = {
    "660732": sp.Rational(1, 4),
    "660889": sp.Rational(3, 2),
    "660898": 3,
    "660905": sp.Rational(3, 2),
    "681196": 8,
    "681272": 7,
    "681300": 3,
    "507887": 19,
    "507910": 6 * sp.sqrt(21),
    "510460": 19,
    "500962": 9 * sp.sqrt(91) / 4,
    "500968": 30,
    "501124": 9 * sp.sqrt(91) / 4,
}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_geometry_each_equation_exact_assets_and_idempotency(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    m = selection(ctx)[0]
    assert sp.simplify(m.answer - EXPECTED[case["task"]]) == 0
    assert sp.simplify(verify(solution_html(result), m) - m.answer) == 0
    assert ctx == case["context"]
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations
    assert (
        ctx["normalized_content"]["assets"]
        == case["context"]["normalized_content"]["assets"]
    )
    for key in ("condition", "source", "criteria"):
        assert section(ctx, key) == section(case["context"], key)
    assert not BeautifulSoup(section(ctx, "answer")["html"], "html.parser").find("img")
    assert section(ctx, "answer")["asset_keys"] == []


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_extra_requirement_and_parent_drift_are_refused(case):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Найдите также объём.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_html="changed")


@pytest.mark.parametrize(
    "task,old,new",
    (
        ("660732", "LA = 4 SL", "LA = 1 SL"),
        ("660889", "2 BL = 3 LC", "3 BL = 2 LC"),
        ("660898", "середины ребер AB и SC", "середины ребер AC и SB"),
        ("681196", r"\frac{\sqrt{2}}{3} ?", "1 ?"),
        ("681272", r"2\sqrt{14} ?", "0 ?"),
        ("507887", "N — середина ребра A_1C_1", "N — середина ребра A_1B_1"),
        ("500968", "A_1B_1", "A_1C_1"),
        ("501124", "A'C'", "A'B'"),
    ),
)
def test_false_incidence_ratio_or_changed_construction_is_refused(task, old, new):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    assert old in raw
    section(ctx, "condition")["html"] = "<p>" + raw.replace(old, new) + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("task,new", (("660732", "2"), ("660898", "5")))
def test_menelaus_ratio_is_calculated_in_the_requested_direction(task, new):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    old = "LA = 4 SL" if task == "660732" else "AN = 3 NS"
    replacement = "LA = " + new + " SL" if task == "660732" else "AN = " + new + " NS"
    section(ctx, "condition")["html"] = "<p>" + raw.replace(old, replacement) + "</p>"
    result = plan(case, ctx)
    m = selection(ctx)[0]
    assert sp.simplify(verify(solution_html(result), m) - m.answer) == 0
    assert m.answer == (sp.Rational(1, 2) if task == "660732" else 5)


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["group"] != "660732"], ids=lambda c: c["task"]
)
@pytest.mark.parametrize("factor", (sp.Rational(3, 2), 3))
def test_metric_sections_scale_without_changing_the_reviewed_symbols(case, factor):
    import re

    ctx = deepcopy(case["context"])
    m = selection(ctx)[0]
    raw = condition_text(section(ctx, "condition")["html"], None)
    values = {
        key: sp.latex(v * factor ** (2 if key == "area" else 1)) for key, v in m.given
    }
    if m.mode == "square_perpendicular_section_ratio":
        raw = re.sub(
            r"AB\s*=\s*.+?\.", lambda _: "AB = " + values["a"] + ".", raw, count=1
        )
        raw = re.sub(
            r"(площадь сечения равна ).+?(\s*\?|\.)$",
            lambda x: x[1] + values["area"] + x[2],
            raw,
        )
    else:
        a, h = (dict(m.given)[k] for k in ("a", "height"))
        if m.names[0] == "construct":
            raw = raw.replace(
                "со стороной " + sp.latex(a) + ".", "со стороной " + values["a"] + "."
            ).replace(
                "Высота призмы равна " + sp.latex(h) + ".",
                "Высота призмы равна " + values["height"] + ".",
            )
        else:
            raw = raw.replace(
                "стороны основания равны "
                + sp.latex(a)
                + ", боковые ребра равны "
                + sp.latex(h)
                + ".",
                "стороны основания равны "
                + values["a"]
                + ", боковые ребра равны "
                + values["height"]
                + ".",
            )
    section(ctx, "condition")["html"] = "<p>" + raw + "</p>"
    result = plan(case, ctx)
    new = selection(ctx)[0]
    verify(solution_html(result), new)
    exponent = (
        0
        if m.mode == "square_perpendicular_section_ratio"
        else 2
        if m.mode.endswith("area")
        else 1
    )
    assert sp.simplify(new.answer - factor**exponent * m.answer) == 0
