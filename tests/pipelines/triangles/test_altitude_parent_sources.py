"""Native altitude sources, independent coordinate geometry and parent fidelity."""

import gzip
import hashlib
import json
import re
from copy import deepcopy
from functools import cache
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.right import altitude_parent
from solution_runner.pipelines.triangles.right.altitude_input import canonical_condition
from solution_runner.pipelines.triangles.right.altitude_solver import (
    AltitudeSolveError,
    _parse_positive_value,
)

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_1_altitude_sources.json").read_text()
)
GROUPS = {g["key"]: g for g in DATA["groups"]}
CASES = DATA["cases"]
SUPPORTED = [c for c in CASES if c["status"] == "supported"]
PARENTS = {c["group"]: c for c in CASES if c["group"] == c["task"]}
U, V = sp.symbols("u v", positive=True)


def section(context, key):
    return next(s for s in context["normalized_content"]["sections"] if s["key"] == key)


def plan(case, context=None, parent=None):
    group = GROUPS[case["group"]]
    return get_handler("right-triangle-altitude-universal").plan(
        PlanInput(
            context or case["context"],
            parent_asset_id=group["condition_asset_id"],
            parent_solution_html=parent
            if parent is not None
            else section(PARENTS[case["group"]]["context"], "solution")["html"],
        )
    )


def solution_html(result):
    return next(
        t["value"]["html"]
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )


@cache
def coordinates(group, task):
    case = next(c for c in CASES if (c["group"], c["task"]) == (group, task))
    html = canonical_condition(
        section(case["context"], "condition")["html"],
        source=GROUPS[group]["condition_asset_id"],
    )
    known = {}
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = node["data-inline-latex"]
        if "=" in formula:
            key, value = formula.split("=", 1)
            known[key.replace("\\", "").replace(" ", "")] = _parse_positive_value(value)
    squares = {
        "AB": (U + V) ** 2,
        "AH": U**2,
        "BH": V**2,
        "CH": U * V,
        "AC": U * (U + V),
        "BC": V * (U + V),
        "sinA": V / (U + V),
        "cosA": U / (U + V),
        "tgA": V / U,
        "sinB": U / (U + V),
        "cosB": V / (U + V),
        "tgB": U / V,
    }
    equations = [
        sp.together(squares[key] - number**2).as_numer_denom()[0]
        for key, number in known.items()
    ]
    roots = [
        root
        for root in sp.solve(equations, (U, V), dict=True)
        if root[U].is_positive and root[V].is_positive
    ]
    assert len(roots) == 1
    return {
        key: sp.simplify(sp.sqrt(value.subs(roots[0])))
        for key, value in squares.items()
    }


def numeric_formula(text, values):
    def trig(match):
        angle = match[3] or match[4]
        angle = (
            "A"
            if angle in {"HCB", "BCH"}
            else "B"
            if angle in {"HCA", "ACH"}
            else angle
        )
        value = "(" + sp.latex(values[match[1] + angle]) + ")"
        return value + ("^" + match[2] if match[2] else "")

    text = re.sub(
        r"\\(sin|cos|tg)(?:\^\{?(\d+)\}?)?\s*(?:\\angle\s*(HCB|BCH|HCA|ACH)|([AB]))",
        trig,
        text,
    )
    aliases = {"BA": "AB", "CA": "AC", "CB": "BC", "HA": "AH", "HB": "BH", "HC": "CH"}
    return re.sub(
        r"AB|BA|AC|CA|BC|CB|AH|HA|BH|HB|CH|HC",
        lambda m: "(" + sp.latex(values[aliases.get(m[0], m[0])]) + ")",
        text,
    )


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_existing_group_binding_requests_parent_method_and_rewrite(group):
    p = get_group_profile(group["key"])
    assert p.source_group_id == group["group_uuid"] and p.category_key == "1"
    assert group["group_size"] >= 3 and p.existing_solution_policy == "rewrite"
    assert p.content_rule_key == "right-triangle-altitude-universal"
    assert ("parent_solution_html", "parent_solution_html") in get_handler(
        p.content_rule_key
    ).inputs


@pytest.mark.parametrize("case", SUPPORTED, ids=lambda c: c["task"])
def test_native_answer_and_every_proof_equality_match_independent_coordinates(case):
    values = coordinates(case["group"], case["task"])
    result = plan(case)
    answer = sp.Rational(result.answer.replace(",", "."))
    source = (
        BeautifulSoup(section(case["context"], "answer")["html"], "html.parser")
        .get_text("", strip=True)
        .removesuffix(".")
    )
    assert answer == sp.Rational(source.replace(",", "."))
    formulas = BeautifulSoup(solution_html(result), "html.parser").select(
        "[data-inline-latex]"
    )
    for formula in formulas:
        for statement in re.split(
            r"\\Longrightarrow|,\\quad", formula["data-inline-latex"]
        ):
            parts = statement.split("=")
            assert len(parts) >= 2
            numbers = [
                TrigonometricParser(numeric_formula(part, values)).parse().value
                for part in parts
            ]
            assert all(sp.simplify(number - numbers[0]) == 0 for number in numbers), (
                case["task"],
                statement,
            )


@pytest.mark.parametrize("case", SUPPORTED, ids=lambda c: c["task"])
def test_child_saved_solutions_are_unused_conditions_immutable_and_replay_empty(case):
    context = deepcopy(case["context"])
    before = deepcopy(context)
    for key in ("answer", "solution"):
        section(context, key)["html"] = "<p>UNUSED 999</p>"
    result = plan(case, context)
    assert result.answer == plan(case).answer
    assert solution_html(result) == solution_html(plan(case))
    assert section(context, "condition") == section(before, "condition")
    for change in result.transformations:
        target = change["transformation_target_id"]
        assert not target.startswith("section:condition")
        if target.startswith("asset:"):
            context["normalized_content"]["assets"].append(change["value"])
        else:
            next(
                s
                for s in context["normalized_content"]["sections"]
                if s["transformation_target_id"] == target
            ).update(change["value"])
    assert plan(case, context).transformations == ()


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["status"] != "supported"], ids=lambda c: c["task"]
)
def test_unreviewed_parent_methods_and_corrupted_source_do_not_get_partial_output(case):
    before = deepcopy(case["context"])
    with pytest.raises(ContentPlanError):
        plan(case)
    assert case["context"] == before


def test_parent_definition_can_reflect_to_angle_b_and_keep_its_named_triangle():
    case = next(c for c in CASES if c["task"] == "19131")
    html = solution_html(plan(case))
    assert "B и HCA" in html and r"\cos B" in html and "CA^2=HA^2+CH^2" in html
    assert r"\cos A" not in html


def test_parent_extra_figure_stays_before_the_intro_and_reuses_exact_existing_asset():
    case = next(c for c in CASES if c["task"] == "34703")
    result = plan(case)
    html = solution_html(result)
    assert html.index("<img") < html.index("Углы A")
    changes = [
        t
        for t in result.transformations
        if t["transformation_target_id"].startswith("asset:")
    ]
    assert (
        len(changes) == 1
        and changes[0]["value"]["asset_id"] == altitude_parent._EQUALITY_FIGURE
    )


@pytest.mark.parametrize("source,digest", altitude_parent._SOURCES.items())
def test_original_qualitative_figures_remain_byte_identical(source, digest):
    path = Path(altitude_parent.__file__).with_name("assets") / (source + ".svgz")
    assert hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest() == digest


@pytest.mark.parametrize(
    "extra",
    [
        "<p>Удвойте ответ.</p>",
        '<span data-inline-latex="AC=99"></span>',
        "<script>answer=0</script>",
    ],
)
def test_unknown_additional_condition_statements_fail_closed(extra):
    case = SUPPORTED[0]
    context = deepcopy(case["context"])
    section(context, "condition")["html"] += extra
    with pytest.raises(ContentPlanError):
        plan(case, context)


def test_figure_gap_preserves_the_entire_radical_height_value():
    case = next(c for c in CASES if c["task"] == "34065")
    values = coordinates(case["group"], case["task"])
    assert values["CH"] == 9 * sp.sqrt(11)
    assert plan(case).answer == "0,1"
    invalid = (
        section(case["context"], "condition")["html"] + " Дополнительная величина."
    )
    with pytest.raises(AltitudeSolveError):
        canonical_condition(invalid, source=GROUPS[case["group"]]["condition_asset_id"])


@pytest.mark.parametrize("task", ["27357", "19899", "19901", "19903"])
def test_both_tangent_methods_keep_the_parent_order_and_titles(task):
    case = next(c for c in CASES if c["task"] == task)
    soup = BeautifulSoup(solution_html(plan(case)), "html.parser")
    methods = soup.select('section[data-content-kind="solution"]')
    assert [m["data-solution-title"] for m in methods] == [
        "Решение",
        "Приведем другое решение.",
    ]
    formulas = [
        [f["data-inline-latex"] for f in method.select("[data-inline-latex]")]
        for method in methods
    ]
    assert len(formulas[0]) == 1 and len(formulas[1]) == 4
    assert formulas[0][0].startswith(r"BH=CH\tg\angle HCB=CH\tg A=AH\tg^2 A=")
    assert formulas[1][0] == r"\tg A=\frac{CH}{AH}"
    assert formulas[1][2] == r"CH^2=AH\cdot HB"
    assert formulas[1][3].startswith(r"BH=\frac{CH^2}{AH}=")


@pytest.mark.parametrize("alteration", ["metric", "title", "extra_method"])
def test_changed_multiple_parent_methods_are_not_silently_simplified(alteration):
    case = next(c for c in CASES if c["task"] == "19899")
    original = section(PARENTS["27357"]["context"], "solution")["html"]
    if alteration == "metric":
        changed = original.replace(r"CH^{2}=AH\cdot HB", r"CH^{2}=AH+HB")
    elif alteration == "title":
        changed = original.replace("Приведем другое решение.", "Третий способ")
    else:
        changed = (
            original
            + '<section data-content-kind="solution"><p>Ещё способ.</p></section>'
        )
    assert changed != original
    with pytest.raises(ContentPlanError):
        plan(case, parent=changed)
