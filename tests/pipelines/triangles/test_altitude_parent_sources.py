"""Native altitude sources, independent coordinate geometry and parent fidelity."""

import gzip
import hashlib
import re
from copy import deepcopy
from functools import cache
from pathlib import Path

import pytest
import sympy as sp
from altitude_source_cases import (
    CASES,
    DATA,
    GROUPS,
    SUPPORTED,
    plan,
    section,
    solution_html,
)
from bs4 import BeautifulSoup
from right_triangle_geometry import coordinate_values, numeric_formula

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.right import altitude_parent
from solution_runner.pipelines.triangles.right.altitude_input import canonical_condition
from solution_runner.pipelines.triangles.right.altitude_solver import (
    AltitudeSolveError,
)


@cache
def coordinates(group, task):
    case = next(c for c in CASES if (c["group"], c["task"]) == (group, task))
    values = coordinate_values(
        case.get(
            "verified_condition_html", section(case["context"], "condition")["html"]
        ),
        source=GROUPS[group]["condition_asset_id"],
    )
    variable = {"27267": "BC", "27265": "AH", "27266": "BH"}.get(group)
    if variable:
        values["x"] = values[variable]
    return values


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
            r"\\Longrightarrow|\\iff|,\\quad", formula["data-inline-latex"]
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
        if target.startswith("section:condition"):
            assert case.get("verified_condition_html") == change["value"]["html"]
            assert change["value"]["asset_keys"] == ["image_1"]
        if target.startswith("asset:"):
            context["normalized_content"]["assets"].append(change["value"])
        else:
            next(
                s
                for s in context["normalized_content"]["sections"]
                if s["transformation_target_id"] == target
            ).update(change["value"])
    assert plan(case, context).transformations == ()


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
