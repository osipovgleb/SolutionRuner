"""Verify every native cut-cone source, strict figure input and the shared angular fraction."""

from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from cone_cut_formula_oracle import verify
from cone_cut_source_cases import CASES, GROUPS, arguments, plan, read, saved_answer
from midpoint_source_cases import replay, section
from sphere_formula_oracle import PiParser

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.cone_cut import solve
from solution_runner.pipelines.solids.cylinder_cut import solve as cylinder
from solution_runner.pipelines.solids.measurements import sector_fraction


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answer_and_each_equality_preserve_all_inputs_and_assets(case):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    m = read(case)
    result = plan(case, ctx)
    assert (
        ctx == before
        and PiParser(result.answer).parse().value
        == PiParser(saved_answer(case)).parse().value
    )
    verify(result, m)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "condition") == section(before, "condition")
    assert section(ctx, "source") == section(before, "source")
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx) == ()


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("field", ["html", "primary", "assets"])
def test_full_parent_pins_and_profiles(group, field):
    c = next(c for c in CASES if c["task"] == group)
    args = arguments(group)
    override = (
        {"parent_solution_html": args["parent_solution_html"] + "<p>Другой метод.</p>"}
        if field == "html"
        else {"parent_asset_id": "foreign"}
        if field == "primary"
        else {"parent_solution_assets": ({"asset_key": "foreign"},)}
    )
    with pytest.raises(ContentPlanError):
        plan(c, **override)
    p = get_group_profile(group)
    handler = get_handler(GROUPS[group]["rule"])
    handler.validate()
    assert (
        p.source_group_id == GROUPS[group]["group_uuid"]
        and p.group_order_index == GROUPS[group]["order_index"]
    )
    assert (
        handler.requires_frozen_manifest
        and handler.strict_frozen_input
        and handler.verify_content_readback
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("change", ["missing", "instruction"])
def test_numbered_figure_is_required_and_unreviewed_statements_are_rejected(
    case, change
):
    ctx = deepcopy(case["context"])
    s = section(ctx, "condition")
    if change == "instruction":
        s["html"] += "<p>Радиус равен 999. Округлите ответ до сотых.</p>"
    else:
        soup = BeautifulSoup(s["html"], "html.parser")
        soup.img.decompose()
        s["html"] = str(soup)
        s["asset_keys"] = []
        ctx["normalized_content"]["assets"] = []
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("change", ["foreign", "url", "duplicate", "wrong_object"])
def test_changed_or_unreviewed_assets_fail_closed(group, change):
    c = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(c["context"])
    assets = ctx["normalized_content"]["assets"]
    a = assets[0]
    if change == "foreign":
        a["asset_id"] = "foreign"
    elif change == "url":
        a["url"] = "https://example.com/foreign.svg"
    elif change == "duplicate":
        assets.append(deepcopy(a))
    else:
        other = "c66e1981-92e4-42b7-9357-575a61145152"
        a["asset_id"] = other
        a["url"] = "/assets/" + other
        s = section(ctx, "condition")
        soup = BeautifulSoup(s["html"], "html.parser")
        soup.img["data-asset-id"] = other
        soup.img["src"] = "/assets/" + other
        s["html"] = str(soup)
    with pytest.raises(ContentPlanError):
        plan(c, ctx)


@pytest.mark.parametrize(
    "kind,values,expected",
    [
        ("kept", (3, 4, 120), 4),
        ("removed", (3, 4, 120), 8),
        ("kept", ("1.5", 8, 90), sp.Rational(3, 2)),
        ("removed", (4, 3, 60), sp.Rational(40, 3)),
    ],
)
def test_general_sector_fraction_applies_cone_factor_one_third(kind, values, expected):
    m = solve(kind, values)
    assert m.answer == expected
    assert sp.simplify(cylinder("sector", kind, values)[1] - 3 * m.answer) == 0


@pytest.mark.parametrize(
    "kind,values",
    [
        ("kept", (0, 3, 90)),
        ("kept", (-1, 3, 90)),
        ("kept", (2, 0, 90)),
        ("kept", (2, 3, 0)),
        ("kept", (2, 3, 360)),
        ("removed", (2, 3, 361)),
        ("unknown", (2, 3, 90)),
    ],
)
def test_nonphysical_sector_input_is_rejected(kind, values):
    with pytest.raises(ContentPlanError):
        solve(kind, values)


@pytest.mark.parametrize(
    "angle,kind,expected",
    [
        (90, "kept", sp.Rational(1, 4)),
        (90, "removed", sp.Rational(3, 4)),
        (60, "kept", sp.Rational(1, 6)),
        (60, "removed", sp.Rational(5, 6)),
    ],
)
def test_sector_labels_have_distinct_kept_and_removed_meanings(angle, kind, expected):
    assert sector_fraction(angle, kind) == expected
