"""Independently evaluate every equality, including the parent's algebraic note."""

import re
from copy import deepcopy

import pytest
import sympy as sp
from box_source_cases import CASES, GROUPS, arguments, plan, read, saved_answer
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.logarithm_parser import LogarithmParser
from solution_runner.pipelines.equations.power_arithmetic import ScalarParser
from solution_runner.pipelines.solids.box_figures import selection


def variables(m):
    if not m.edges:
        p, q = m.given
        s, h = (
            (p, q)
            if m.mode == "volume_from_face"
            else (p / q, q)
            if m.mode == "face_from_volume"
            else (q, p / q)
        )
        return {"V": s * h, "S": s, "h": h, "Sh": s * h}
    a, b, c = m.edges
    v = a * b * c
    return {
        "a_1a_2a_3": v,
        "a_1a_2x": v,
        "a_1a_2": a * b,
        "a_1a_3": a * c,
        "a_2a_3": b * c,
        "a_1x": a * c,
        "a_2x": b * c,
        "a_1": a,
        "a_2": b,
        "a_3": c,
        "x": c,
        "a": v ** sp.Rational(1, 3),
        "S": 2 * (a * b + a * c + b * c),
        "V": v,
        "d": sp.sqrt(a * a + b * b + c * c),
    }


def verify(html, m):
    for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = tag["data-inline-latex"]
        for label, amount in sorted(variables(m).items(), key=lambda x: -len(x[0])):
            formula = re.sub(
                r"(?<![A-Za-z_])" + re.escape(label) + r"(?![A-Za-z_])",
                lambda _, a=amount: "(" + sp.latex(a) + ")",
                formula,
            )
        values = [LogarithmParser(x).parse().value for x in formula.split("=")]
        assert len(values) > 1 and all(
            sp.simplify(x - values[0]) == 0 for x in values
        ), formula


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_each_native_answer_and_every_displayed_equality(case):
    result = plan(case)
    assert (
        sp.simplify(
            ScalarParser(result.answer).parse()
            - ScalarParser(saved_answer(case)).parse()
        )
        == 0
    )
    html = solution_html(result)
    verify(html, read(case))
    soup = BeautifulSoup(html, "html.parser")
    assert not soup.find("section") and not soup.find("img")
    bold = [b.get_text() for b in soup.find_all("b")]
    assert bold == (
        ["Примечание о том, как не надо решать эту задачу."]
        if case["group"] == "27060"
        else []
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_source_immutable_saved_answer_unused_and_empty_replay(case):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before and result.answer == plan(case).answer
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    for context in (ctx, before):
        soup = BeautifulSoup(section(context, "condition")["html"], "html.parser")
        for image in soup.find_all("img"):
            image.decompose()
        section(context, "condition")["html"] = str(soup)
    assert section(ctx, "condition")["html"] == section(before, "condition")["html"]
    assert section(ctx, "source") == section(before, "source")


@pytest.mark.parametrize("group", GROUPS.values(), ids=lambda g: g["key"])
@pytest.mark.parametrize("change", ["html", "asset", "figures"])
def test_parent_pins_and_registered_frozen_profiles(group, change):
    handler = get_handler(group["rule"])
    handler.validate()
    profile = get_group_profile(group["key"])
    assert (
        profile.source_group_id == group["group_uuid"]
        and profile.existing_solution_policy == "rewrite"
    )
    assert (
        handler.strict_frozen_input
        and handler.requires_frozen_manifest
        and handler.verify_content_readback
        and handler.parent_from_group_listing
    )
    args = arguments(group["key"])
    override = (
        {"parent_solution_html": args["parent_solution_html"] + "<p>Другой метод</p>"}
        if change == "html"
        else {"parent_asset_id": "foreign"}
        if change == "asset"
        else {"parent_solution_assets": ({"asset_key": "image_9"},)}
    )
    case = next(c for c in CASES if c["task"] == group["key"])
    with pytest.raises(ContentPlanError):
        plan(case, **override)


@pytest.mark.parametrize("group", GROUPS)
def test_a_different_complete_question_cannot_replace_the_parent_method(group):
    case = next(c for c in CASES if c["task"] == group)
    other = next(c for c in CASES if c["task"] == c["group"] and c["group"] != group)
    with pytest.raises(ContentPlanError, match="differs from its parent method"):
        plan(case, deepcopy(other["context"]))


@pytest.mark.parametrize(
    "group,text",
    [
        (
            "27054",
            "Два ребра прямоугольного параллелепипеда, выходящие из одной вершины, равны 1 и 2. Площадь поверхности этого параллелепипеда равна 5. Найдите третье ребро, выходящее из той же вершины.",
        ),
        (
            "27060",
            "Два ребра прямоугольного параллелепипеда, выходящие из одной вершины, равны 1 и 2. Площадь поверхности параллелепипеда равна 5. Найдите его диагональ.",
        ),
        (
            "27080",
            "Три ребра прямоугольного параллелепипеда, выходящие из одной вершины, равны 1, 1 и 2. Найдите ребро равновеликого ему куба.",
        ),
        (
            "27100",
            "Два ребра прямоугольного параллелепипеда, выходящие из одной вершины, равны 1 и 2. Диагональ параллелепипеда равна 4. Найдите объем параллелепипеда.",
        ),
        (
            "27101",
            "Два ребра прямоугольного параллелепипеда, выходящие из одной вершины, равны 1 и 2. Объем параллелепипеда равен 3. Найдите его диагональ.",
        ),
    ],
)
def test_noninteger_edges_and_nonperfect_roots_have_valid_complete_proofs(group, text):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    condition = section(ctx, "condition")
    image = BeautifulSoup(condition["html"], "html.parser").find("img")
    condition["html"] = "<p>" + str(image) + text + "</p>"
    verify(solution_html(plan(case, ctx)), selection(ctx)[0])


def test_wrong_saved_answer_is_not_used_as_a_surface_formula():
    case = next(c for c in CASES if c["task"] == "75337")
    m = read(case)
    assert m.edges == (2, 3, 7) and m.answer == 82
    assert sp.prod(m.edges) == 42 and saved_answer(case) == "82"
