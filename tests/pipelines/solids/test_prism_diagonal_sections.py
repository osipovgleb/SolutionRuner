"""All native equations, actual section boundaries and unsupported claims."""

import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from prism_diagonal_geometry_oracle import verify
from prism_diagonal_source_cases import CASES, plan

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.distance_figures import selection
from solution_runner.pipelines.solids.spatial_distance_model import condition_text

EXPECTED = {
    "501710": 144 * sp.sqrt(2),
    "502294": 63 * sp.sqrt(2),
    "511377": 252 * sp.sqrt(2),
    "642779": 33 * sp.sqrt(6) / 10,
    "643676": 12 * sp.sqrt(21) / 5,
    "643716": 7 * sp.sqrt(10) / 6,
    "673601": 24 * sp.sqrt(30) / 7,
    "642886": 5 * sp.sqrt(37) / 6,
    "672871": 4 * sp.sqrt(5),
    "672900": 7 * sp.sqrt(65) / 8,
    "656575": 3 * sp.sqrt(2),
    "660953": 2 * sp.sqrt(2),
    "661140": 3 * sp.sqrt(10) / 2,
}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_every_equation_and_unique_figure_ownership(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    m = selection(ctx)[0]
    assert sp.simplify(m.answer - EXPECTED[case["task"]]) == 0
    assert sp.simplify(verify(solution_html(result), m) - m.answer) == 0
    assert ctx == case["context"]
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations
    for key in ("condition", "source", "criteria"):
        assert section(ctx, key) == section(case["context"], key)
    assert section(ctx, "answer")["asset_keys"] == []
    assert not BeautifulSoup(section(ctx, "answer")["html"], "html.parser").find("img")
    if case["task"] not in {"673601", "643676", "643716"}:
        assert (
            ctx["normalized_content"]["assets"]
            == case["context"]["normalized_content"]["assets"]
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_extra_request_and_parent_drift_refuse_any_plan(case):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Найдите также объём.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_html="changed")


def scaled(raw, m, factor):
    g = dict(m.given)
    val = lambda key, power=1: sp.latex(g[key] * factor**power)
    if m.mode == "square_prism_ratio_area":
        return re.sub(
            r"сторона основания равна .+?, а боковое ребро AA_1\s*=\s*.+?\.",
            lambda _: (
                "сторона основания равна "
                + val("a")
                + ", а боковое ребро AA_1="
                + val("height")
                + "."
            ),
            raw,
            count=1,
        )
    if m.mode == "trapezoid_prism_pentagon_area":
        return re.sub(
            r"AD\s*=\s*.+?(?: и|,) BC\s*=\s*.+?\.",
            lambda _: "AD=" + val("a") + " и BC=" + val("b") + ".",
            raw,
            count=1,
        )
    if m.mode == "parallelogram_prism_trapezoid_area":
        raw = re.sub(
            r"с основаниями .+? и .+?\.",
            lambda _: "с основаниями " + val("small") + " и " + val("large") + ".",
            raw,
            count=1,
        )
        raw = re.sub(
            r"(объем призмы(?: ABCDA_1B_1C_1D_1)? равен ).+?,",
            lambda a: a[1] + val("volume", 3) + ",",
            raw,
            count=1,
        )
        return re.sub(
            r"(высота равна ).+?\.$", lambda a: a[1] + val("height") + ".", raw
        )
    raw = re.sub(
        r"(площадь (?:ее )?основания(?: ABCD)? равна ).+?(?=,|\.)",
        lambda a: a[1] + val("base", 2),
        raw,
    )
    if m.mode.endswith("height"):
        return re.sub(
            r"(площадь (?:сечения|ромба MB_1KD) равна ).+?\.$",
            lambda a: a[1] + val("area", 2) + ".",
            raw,
        )
    return re.sub(
        r"(объем призмы ABCDA_1B_1C_1D_1 равен ).+?,",
        lambda a: a[1] + val("volume", 3) + ",",
        raw,
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("factor", (sp.Rational(3, 2), 3))
def test_new_dimensions_scale_and_every_step_remains_geometric(case, factor):
    ctx = deepcopy(case["context"])
    m = selection(ctx)[0]
    raw = condition_text(section(ctx, "condition")["html"], None)
    changed = scaled(raw, m, factor)
    assert changed != raw
    section(ctx, "condition")["html"] = "<p>" + changed + "</p>"
    result = plan(case, ctx)
    new = selection(ctx)[0]
    assert sp.simplify(verify(solution_html(result), new) - new.answer) == 0
    exponent = 1 if new.mode.endswith("height") else 2
    assert sp.simplify(new.answer - factor**exponent * m.answer) == 0


@pytest.mark.parametrize(
    "task,old,new",
    (
        ("501710", "считая от вершины D_1", "считая от вершины A_1"),
        ("502294", "точки B, D и K", "точки A, D и K"),
        ("501710", "сторона основания равна 20", "сторона основания равна 0"),
        ("642779", r"=1\colon 4", r"=2\colon 4"),
        ("643676", "MKC=90°", "MKC=60°"),
        ("673601", "GFC делит ребро", "GKC делит ребро"),
        ("642886", r"=1\colon 2", r"=1\colon 3"),
        ("672871", "с основаниями 1 и 3", "с основаниями 3 и 1"),
        ("656575", "площадь сечения равна 6", "площадь сечения равна 3"),
        ("660953", r"равна 4\sqrt{2}", "равна 1"),
        ("661140", "Известно, что M — середина AA_1", "Известно, что M — середина AB"),
    ),
)
def test_false_midpoints_degenerate_prisms_and_wrong_requests_are_refused(
    task, old, new
):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    assert old in raw
    section(ctx, "condition")["html"] = "<p>" + raw.replace(old, new) + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_reverse_rhombus_proof_uses_the_given_midpoint_and_two_legs():
    case = next(c for c in CASES if c["task"] == "661140")
    html = solution_html(plan(case))
    assert "по двум катетам" in html and "по катету и гипотенузе" not in html
    assert (
        html.index("по двум катетам")
        < html.index("то есть ромб")
        < html.index("S_{MB_1KD}")
    )
