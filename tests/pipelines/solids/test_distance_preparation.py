"""Evaluate all published equalities using independent scaled vertex coordinates."""

import itertools
import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from distance_source_cases import CASES, GROUPS, arguments, plan, read, saved_answer
from midpoint_source_cases import replay, section, solution_html

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.logarithm_parser import LogarithmParser
from solution_runner.pipelines.equations.power_arithmetic import ScalarParser
from solution_runner.pipelines.solids.box_coordinates import VERTICES
from solution_runner.pipelines.solids.distance_figures import selection


def verify(html, m):
    values = {}
    for a, b in itertools.permutations(VERTICES, 2):
        p = sp.Matrix([x * sp.sqrt(v) for x, v in zip(VERTICES[a], m.squares)])
        q = sp.Matrix([x * sp.sqrt(v) for x, v in zip(VERTICES[b], m.squares)])
        values[a + b] = sp.sqrt((p - q).dot(p - q))
    for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = tag["data-inline-latex"]
        for name, amount in sorted(values.items(), key=lambda p: -len(p[0])):
            formula = re.sub(
                r"(?<![A-Za-z_])" + re.escape(name) + r"(?![A-Za-z_])",
                lambda _, v=amount: "(" + sp.latex(v) + ")",
                formula,
            )
        expr = [LogarithmParser(v).parse().value for v in formula.split("=")]
        assert len(expr) > 1 and all(sp.simplify(v - expr[0]) == 0 for v in expr), (
            formula
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_native_answer_and_every_formula(case):
    result = plan(case)
    assert (
        sp.simplify(
            ScalarParser(result.answer).parse()
            - ScalarParser(saved_answer(case)).parse()
        )
        == 0
    )
    verify(solution_html(result), read(case))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_original_immutable_answer_ignored_and_replay_empty(case):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before and result.answer == plan(case).answer
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "source") == section(before, "source")
    assert selection(ctx)[0] == read(case)


@pytest.mark.parametrize("group", GROUPS.values(), ids=lambda g: g["key"])
@pytest.mark.parametrize("field", ["html", "primary", "assets"])
def test_full_parent_pins_and_registered_strict_profiles(group, field):
    profile = get_group_profile(group["key"])
    handler = get_handler(group["rule"])
    handler.validate()
    assert (
        profile.source_group_id == group["group_uuid"]
        and profile.existing_solution_policy == "rewrite"
    )
    assert (
        handler.parent_from_group_listing
        and handler.requires_frozen_manifest
        and handler.strict_frozen_input
        and handler.verify_content_readback
    )
    case = next(c for c in CASES if c["task"] == group["key"])
    args = arguments(group["key"])
    override = (
        {"parent_solution_html": args["parent_solution_html"] + "<p>Другой метод</p>"}
        if field == "html"
        else {"parent_asset_id": "foreign"}
        if field == "primary"
        else {"parent_solution_assets": ({"asset_key": "image_9"},)}
    )
    with pytest.raises(ContentPlanError):
        plan(case, **override)


@pytest.mark.parametrize("pair", list(itertools.combinations(VERTICES, 2)))
@pytest.mark.parametrize("square", [False, True])
def test_same_parent_family_prepares_every_vertex_pair_with_checked_pythagoras(
    pair, square
):
    case = next(c for c in CASES if c["task"] == ("245359" if square else "245360"))
    ctx = deepcopy(case["context"])
    condition = section(ctx, "condition")
    image = BeautifulSoup(condition["html"], "html.parser").find("img")
    a, b = pair
    condition["html"] = (
        "<p>"
        + str(image)
        + f"Найдите {'квадрат расстояния' if square else 'расстояние'} между вершинами {a} и {b} прямоугольного параллелепипеда, для которого AB=2, AD=3, AA_1=4.</p>"
    )
    result = plan(case, ctx)
    model = selection(ctx)[0]
    verify(solution_html(result), model)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize(
    "group,text",
    [
        (
            "284357",
            r"В прямоугольном параллелепипеде ABCDA_1B_1C_1D_1 известно, что BD_1=\sqrt{29}, AB=2, AA_1=4. Найдите длину ребра BC.",
        ),
        (
            "245359",
            r"Найдите квадрат расстояния между вершинами C и A_1 прямоугольного параллелепипеда, для которого AB=\sqrt{2}, AD=3, AA_1=\frac{1}{2}.",
        ),
    ],
)
def test_missing_horizontal_axis_and_exact_radical_labels_are_supported(group, text):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    condition = section(ctx, "condition")
    image = BeautifulSoup(condition["html"], "html.parser").find("img")
    condition["html"] = "<p>" + str(image) + text + "</p>"
    result = plan(case, ctx)
    verify(solution_html(result), selection(ctx)[0])
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("group", GROUPS)
def test_different_complete_requested_quantity_cannot_replace_parent_method(group):
    case = next(c for c in CASES if c["task"] == group)
    other = next(c for c in CASES if c["task"] == c["group"] and c["group"] != group)
    with pytest.raises(ContentPlanError):
        plan(case, deepcopy(other["context"]))


def test_three_face_measurements_do_not_silently_replace_the_parents_edge_method():
    case = next(c for c in CASES if c["task"] == "284357")
    ctx = deepcopy(case["context"])
    condition = section(ctx, "condition")
    image = BeautifulSoup(condition["html"], "html.parser").find("img")
    condition["html"] = (
        "<p>"
        + str(image)
        + r"В прямоугольном параллелепипеде ABCDA_1B_1C_1D_1 известно, что AC=\sqrt{13}, AB_1=\sqrt{20}, AD_1=5. Найдите длину ребра AA_1.</p>"
    )
    with pytest.raises(ContentPlanError, match="parent method"):
        plan(case, ctx)
