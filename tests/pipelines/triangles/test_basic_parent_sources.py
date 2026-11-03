"""Native basic-triangle answers and every generated proof step use exact geometry."""

import gzip
import hashlib
import re
from copy import deepcopy
from functools import cache
from pathlib import Path

import pytest
import sympy as sp
from basic_source_cases import (
    CASES,
    DATA,
    GROUPS,
    parent_html,
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
from solution_runner.pipelines.triangles.right import basic_parent
from solution_runner.pipelines.triangles.right.altitude_input import canonical_condition


@cache
def geometry(group, task):
    case = next(c for c in CASES if (c["group"], c["task"]) == (group, task))
    source = GROUPS[group]["parent_asset"]
    html = canonical_condition(
        section(case["context"], "condition")["html"], source=source
    )
    values = coordinate_values(html, source=source)
    requested = (
        BeautifulSoup(html, "html.parser")
        .select("[data-inline-latex]")[-1]["data-inline-latex"]
        .replace(" ", "")
        .replace("\\", "")
    )
    values["x"] = values[requested]
    return values, requested


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_existing_binding_rewrites_solutions_and_reads_the_complete_parent(group):
    profile = get_group_profile(group["key"])
    assert (
        profile.content_rule_key == group["rule"]
        and profile.source_group_id == group["group_uuid"]
    )
    assert group["group_size"] >= 3 and profile.existing_solution_policy == "rewrite"
    assert ("parent_solution_html", "parent_solution_html") in get_handler(
        group["rule"]
    ).inputs


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answer_and_each_equality_match_independent_geometry(case):
    values, requested = geometry(case["group"], case["task"])
    result = plan(case)
    assert sp.Rational(result.answer.replace(",", ".")) == values[requested]
    source_answer = (
        BeautifulSoup(section(case["context"], "answer")["html"], "html.parser")
        .get_text("", strip=True)
        .removesuffix(".")
    )
    assert sp.Rational(result.answer.replace(",", ".")) == sp.Rational(
        source_answer.replace(",", ".")
    )
    for formula in BeautifulSoup(solution_html(result), "html.parser").select(
        "[data-inline-latex]"
    ):
        for statement in re.split(
            r"\\iff|\\Longrightarrow|,\\quad", formula["data-inline-latex"]
        ):
            parts = statement.split("=")
            assert len(parts) >= 2
            numbers = [
                TrigonometricParser(numeric_formula(p, values)).parse().value
                for p in parts
            ]
            assert all(sp.simplify(number - numbers[0]) == 0 for number in numbers), (
                case["task"],
                statement,
            )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_stale_solutions_and_answers_are_unused_conditions_immutable_and_replay_empty(
    case,
):
    context = deepcopy(case["context"])
    for key in ("answer", "solution"):
        section(context, key)["html"] = "<p>Не использовать 999.</p>"
    original = deepcopy(context)
    result = plan(case, context)
    assert context == original
    assert result.answer == plan(case).answer and solution_html(
        result
    ) == solution_html(plan(case))
    for change in result.transformations:
        target = change["transformation_target_id"]
        assert not target.startswith(("section:condition", "asset:"))
        next(
            s
            for s in context["normalized_content"]["sections"]
            if s["transformation_target_id"] == target
        ).update(change["value"])
    assert plan(case, context).transformations == ()


@pytest.mark.parametrize("source,digest", basic_parent._SOURCES.items())
def test_original_unlabelled_length_figures_are_byte_identical(source, digest):
    path = Path(basic_parent.__file__).with_name("assets") / (source + ".svgz")
    assert hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest() == digest


@pytest.mark.parametrize(
    "extra",
    [
        "<p>Удвойте ответ.</p>",
        '<span data-inline-latex="AB=99"></span>',
        "<script>answer=0</script>",
    ],
)
def test_unknown_condition_statements_fail_closed(extra):
    case = CASES[0]
    context = deepcopy(case["context"])
    section(context, "condition")["html"] += extra
    with pytest.raises(ContentPlanError):
        plan(case, context)


@pytest.mark.parametrize("group", ["27238", "27239"])
def test_both_parent_methods_and_the_sine_hypotenuse_note_are_preserved(group):
    for case in [c for c in CASES if c["group"] == group]:
        soup = BeautifulSoup(solution_html(plan(case)), "html.parser")
        assert [s["data-solution-title"] for s in soup.select("section")] == (
            ["Решение", "Приведём другое решение"]
            if group == "27238"
            else ["Решение", "Альтернативное решение."]
        )
        assert (
            ("Примечание" in soup.get_text())
            if group == "27238"
            else (r"BC=AC\tg A=" in str(soup))
        )
        assert "Пифагора" in soup.get_text()


@pytest.mark.parametrize("group", ["27238", "27239"])
@pytest.mark.parametrize("change", ["omit", "reorder", "formula"])
def test_incomplete_or_changed_parent_methods_are_rejected(group, change):
    case = next(c for c in CASES if c["group"] == group)
    soup = BeautifulSoup(parent_html(group), "html.parser")
    methods = soup.select("section")
    if change == "omit":
        methods[-1].decompose()
    elif change == "reorder":
        methods[0].insert_before(methods[-1].extract())
    else:
        methods[-1].select("[data-inline-latex]")[-1]["data-inline-latex"] = "AB=AC+BC"
    with pytest.raises(ContentPlanError):
        plan(case, parent=str(soup))


@pytest.mark.parametrize("task", ["635853", "530665", "513676"])
def test_inverse_questions_use_a_positive_unknown_and_the_parent_method(task):
    case = next(c for c in CASES if c["task"] == task)
    html = solution_html(plan(case))
    assert "x &gt; 0" in html and "Пифагора" in html
    assert "AC=x" in html
