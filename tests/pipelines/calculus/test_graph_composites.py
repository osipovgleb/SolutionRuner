"""Source compositions and independent differentiation/evaluation edge cases."""

import json
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from graph_samples import _apply_local, plan

from solution_runner.pipelines.calculus import graph_composites as graph
from solution_runner.pipelines.calculus import graph_input
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.numbers import parse_rational

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_9_composite.json").read_text()
)
CASES = DATA["cases"]


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_source_groups_share_the_appropriate_family(group):
    profile = get_group_profile(group["key"])
    assert profile.source_group_id == group["uuid"]
    assert profile.content_rule_key == group["rule"]
    assert profile.snapshot_theme_id == group["theme_uuid"]
    assert profile.group_order_index == group["order"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["group"] + "-" + c["task"])
def test_source_result_is_independent_preserves_assets_and_is_idempotent(case):
    context = deepcopy(case["context"])
    original = deepcopy(context)
    expected = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    result = plan(case, context)
    assert parse_rational(result.answer) == parse_rational(
        BeautifulSoup(expected, "html.parser").get_text(strip=True)
    )
    assert context == original
    assert all(
        t["transformation_target_id"].startswith(
            ("section:answer", "section:solution", "asset:")
        )
        for t in result.transformations
    )
    next(s for s in context["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>99999</p>"
    assert plan(case, context).answer == result.answer
    context = deepcopy(original)
    _apply_local(context, result.transformations)
    assert plan(case, context).transformations == ()
    html = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    if case["group"] not in ["40129", "541372"]:
        formulas = BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
        numerical = formulas[-2]["data-inline-latex"].split("=", 1)[1]
        assert graph.polynomial(numerical, graph.X) == parse_rational(result.answer)
    _, _, _, _, _, entry, _ = graph_input.read_graph(original)
    assert len(BeautifulSoup(html, "html.parser").find_all("img")) == int(
        bool(entry.get("solution_asset") or entry.get("origin_tangent_overlay"))
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["group"] + "-" + c["task"])
@pytest.mark.parametrize("leading", [True, False])
def test_extra_instructions_and_changed_graphs_are_refused(case, leading):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    extra = "<p>Удвойте ответ.</p>"
    condition["html"] = (
        extra + condition["html"] if leading else condition["html"] + extra
    )
    with pytest.raises(ValueError):
        plan(case, context)
    with pytest.raises(ValueError, match="downloaded diagram"):
        plan(case, case["context"], downloaded=b"changed graph")


@pytest.mark.parametrize(
    "text,expected",
    [
        ("3f(x)-2x+7", -sp.S.One),
        ("x^3+f(x)", sp.Rational(37, 3)),
        ("f(x)^2", sp.Rational(20, 9)),
        (r"-5f(x)-\frac{2}{11}x+\ln 3", -sp.Rational(61, 33)),
    ],
)
def test_chain_rule_uses_tangent_and_contact_not_a_stored_result(text, expected):
    entry = {"equation": r"\frac{1}{3}x+\frac{8}{3}", "contact": {"x": 2}}
    _, result = graph.calculate(graph.composition(text), True, entry)
    assert result == expected


def test_function_value_is_not_its_derivative_and_log_constant_is_not_dropped():
    entry = {"equation": "-2x+3", "contact": {"x": 1}}
    expression = graph.composition("f'(x)-f(x)+3")
    assert graph.calculate(expression, False, entry)[1] == 0
    with pytest.raises(ValueError, match="second derivative"):
        graph.calculate(expression, True, entry)
    expression = graph.composition(r"f(x)+\ln 3")
    assert graph.calculate(expression, False, entry)[1] == 1 + sp.log(3)
    assert graph.calculate(expression, True, entry)[1] == -2


@pytest.mark.parametrize(
    "text,derivative", [("x^2+f(x)", True), ("f(x)^2", True), ("f(x)", False)]
)
def test_unknown_contact_is_not_guessed(text, derivative):
    with pytest.raises(ValueError, match="does not determine"):
        graph.calculate(graph.composition(text), derivative, {"equation": "2x+1"})


@pytest.mark.parametrize(
    "text",
    [
        r"f(x)+\ln 0",
        r"f(x)+\ln -1",
        "f(x)+a",
        "f(x)+v",
        "f(x)+u",
        "f'(x)+z",
        "f(x)+sin(x)",
        "1/f(x)",
    ],
)
def test_undeclared_variables_or_unreviewed_functions_are_refused(text):
    with pytest.raises(ValueError):
        graph.composition(text)


def test_ordinate_and_tangent_determine_contact_and_marked_values_must_agree():
    assert graph_input.contact(
        {"equation": r"-\frac{1}{4}x+3", "contact": {"y": 2}}
    ) == {"x": 4, "y": 2}
    with pytest.raises(ValueError, match="not on"):
        graph_input.contact({"equation": "2x+1", "contact": {"x": 2, "y": 4}})
    with pytest.raises(ValueError, match="finite derivative"):
        graph_input.tangent({"line_points": [[1, 0], [1, 2]]})


@pytest.mark.parametrize(
    "task,replacement",
    [
        ("525689", ("x_0=2", "x_0=3")),
        ("40129", ("f'(8)", "f'(7)")),
        ("525690", ("Урав­не­ние ка­са­тель­ной по­ка­за­но на ри­сун­ке.", "")),
    ],
)
def test_condition_and_graph_transcription_cannot_disagree(task, replacement):
    case = next(c for c in CASES if c["task"] == task)
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    assert replacement[0] in condition["html"]
    condition["html"] = condition["html"].replace(*replacement)
    with pytest.raises(ValueError):
        plan(case, context)


def test_new_origin_tangent_preserves_all_source_elements_and_passes_through_contact():
    case = next(c for c in CASES if c["task"] == "54801")
    handler = get_handler(get_group_profile(case["group"]).content_rule_key)
    (spec,) = handler.diagram_specs(case["context"])
    *_, entry, source = graph_input.read_graph(case["context"])
    before, after = ET.fromstring(source), ET.fromstring(spec["svg_text"])
    assert before.attrib == after.attrib
    assert [ET.tostring(n) for n in before] == [
        ET.tostring(n) for n in list(after)[:-1]
    ]
    line = list(after)[-1][0]
    ox, oy = entry["svg_origin"]
    ux, uy = entry["svg_unit"]
    for suffix in ["1", "2"]:
        x = (float(line.attrib["x" + suffix]) - ox) / ux
        y = (oy - float(line.attrib["y" + suffix])) / uy
        assert y == pytest.approx(-0.6 * x)
    assert list(after)[-1][-1].text == "y = kx"
