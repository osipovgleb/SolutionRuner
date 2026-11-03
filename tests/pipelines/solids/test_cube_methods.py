"""Check every displayed equality against independent cube dimensions."""

import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from cube_source_cases import CASES, GROUPS, arguments, plan, read
from midpoint_source_cases import replay, section, solution_html

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.logarithm_parser import LogarithmParser
from solution_runner.pipelines.equations.power_arithmetic import ScalarParser


def variables(m):
    if m.mode == "midpoint_section_angle":
        return {
            "KM": sp.sqrt(2) / 2,
            "KL": sp.sqrt(2) / 2,
            "LM": sp.sqrt(2) / 2,
            r"\angle " + m.angle: sp.Integer(60),
        }
    v = m.given[0]
    if m.mode.endswith("_increase"):
        a, k = m.answer, v
        c = (k**2 - m.given[1] / k) / 3
        return {
            "a": a,
            "a_1": a,
            "a_2": -k - a,
            "D": k * k - 4 * c,
            "V_0": a**3,
            "V": (a + k) ** 3,
            "S_0": 6 * a * a,
            "S": 6 * (a + k) ** 2,
        }
    if m.mode == "volume_factor":
        return {"a": sp.Integer(1), "V": sp.Integer(1), "V_1": v**3}
    if m.mode == "surface_factor":
        return {"k": v, "S_0": sp.Integer(6), "S_1": 6 * v * v}
    if m.mode == "surface_factor_from_volume_factor":
        return {
            "k": v ** sp.Rational(1, 3),
            "V_1": v,
            "V_2": sp.Integer(1),
            "S_1": 6 * v ** sp.Rational(2, 3),
            "S_2": sp.Integer(6),
        }
    a = (
        v ** sp.Rational(1, 3)
        if m.mode in {"surface_from_volume", "diagonal_from_volume"}
        else sp.sqrt(v / 6)
        if m.mode == "volume_from_surface"
        else v / sp.sqrt(3)
    )
    return {"a": a, "V": a**3, "S": 6 * a * a, "d": a * sp.sqrt(3)}


def verify(html, m):
    for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = tag["data-inline-latex"]
        for label, amount in sorted(variables(m).items(), key=lambda p: -len(p[0])):
            formula = re.sub(
                r"(?<![A-Za-z_])" + re.escape(label) + r"(?![A-Za-z_])",
                lambda _, a=amount: "(" + sp.latex(a) + ")",
                formula,
            )
        values = [
            LogarithmParser(v.replace(r"^{\circ}", "")).parse().value
            for v in formula.split("=")
        ]
        assert len(values) > 1 and all(
            sp.simplify(v - values[0]) == 0 for v in values
        ), formula


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_saved_answers_and_every_formula(case):
    result = plan(case)
    soup = BeautifulSoup(section(case["context"], "answer")["html"], "html.parser")
    tag = soup.select_one("[data-inline-latex]")
    saved = tag["data-inline-latex"] if tag else soup.get_text(strip=True)
    assert (
        sp.simplify(ScalarParser(result.answer).parse() - ScalarParser(saved).parse())
        == 0
    )
    html = solution_html(result)
    verify(html, read(case))
    assert not BeautifulSoup(html, "html.parser").find("section")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_source_immutable_answer_unused_and_replay_empty(case):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before and result.answer == plan(case).answer
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "source") == section(before, "source")


@pytest.mark.parametrize("group", GROUPS.values(), ids=lambda g: g["key"])
@pytest.mark.parametrize("field", ["primary", "html", "assets"])
def test_parent_pins_and_profile_registration(group, field):
    handler = get_handler(group["rule"])
    handler.validate()
    profile = get_group_profile(group["key"])
    assert profile.source_group_id == group["group_uuid"]
    assert profile.existing_solution_policy == "rewrite"
    assert handler.strict_frozen_input and handler.requires_frozen_manifest
    assert handler.verify_content_readback and handler.parent_from_group_listing
    args = arguments(group["key"])
    override = (
        {"parent_asset_id": "foreign"}
        if field == "primary"
        else {
            "parent_solution_html": args["parent_solution_html"] + "<p>Другой метод</p>"
        }
        if field == "html"
        else {"parent_solution_assets": ({"asset_key": "image_9"},)}
    )
    case = next(c for c in CASES if c["task"] == group["key"])
    with pytest.raises(ContentPlanError):
        plan(case, **override)


@pytest.mark.parametrize(
    "group,text",
    [
        ("27056", "Объем куба равен 2. Найдите площадь его поверхности."),
        (
            "27061",
            "Если каждое ребро куба увеличить на 2, то его площадь поверхности увеличится на 54. Найдите ребро куба.",
        ),
        (
            "27081",
            "Во сколько раз увеличится объем куба, если его ребра увеличить в 1,5 раза?",
        ),
        ("27098", "Диагональ куба равна 2. Найдите его объем."),
        ("27099", "Объем куба равен 2. Найдите его диагональ."),
        (
            "27102",
            "Если каждое ребро куба увеличить на 2, то его объем увеличится на 19. Найдите ребро куба.",
        ),
        ("27139", "Диагональ куба равна 2. Найдите площадь его поверхности."),
        ("27141", "Площадь поверхности куба равна 2. Найдите его объем."),
    ],
)
def test_nonperfect_roots_and_fractional_edges_keep_exact_valid_proofs(group, text):
    from solution_runner.pipelines.solids.cube_figures import model

    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    condition = section(ctx, "condition")
    image = BeautifulSoup(condition["html"], "html.parser").find("img")
    condition["html"] = "<p>" + str(image) + text + "</p>"
    result = plan(case, ctx)
    verify(solution_html(result), model(ctx))


@pytest.mark.parametrize("group", GROUPS)
def test_condition_from_another_method_cannot_use_this_parent(group):
    case = next(c for c in CASES if c["task"] == group)
    other = next(c for c in CASES if c["task"] == c["group"] and c["group"] != group)
    with pytest.raises(ContentPlanError, match="differs from its parent method"):
        plan(case, deepcopy(other["context"]))
