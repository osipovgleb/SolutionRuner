"""Every parent's method, numerical equality and projection branch is checked."""

import math
import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from quantity_source_cases import CASES, GROUPS, arguments, plan
from test_parallelogram_quantity_model import read

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser


def verify(html, m):
    vals = {"S": m.area}
    if m.mode == "sine":
        vals.update(
            {
                m.name("AD"): m.b,
                m.name("AB"): m.a,
                m.name("DH"): m.first_height,
                m.name("AH"): m.projection,
                "a": m.a,
                "b": m.b,
                "h": m.answer,
            }
        )
    elif m.mode == "transfer":
        vals.update(
            a=m.a,
            b=m.b,
            h=m.first_height,
            x=m.second_height,
            CB=m.b,
            BG=m.first_height,
            CG=m.projection,
            CD=m.a,
        )
    elif m.mode == "height":
        vals.update(a=m.first_height, b=m.second_height, h=m.answer)
    elif m.mode == "thirty":
        vals.update(a=m.a, h=m.given[0], AB=m.a, AD=m.a, BH=m.given[0])
    elif m.mode == "diagonals":
        vals.update(d_1=m.diagonals[0], d_2=m.diagonals[1])
    elif m.mode == "other":
        vals.update(a=m.diagonals[1], d=m.diagonals[0])
    else:
        vals.update(a=m.diagonals[0], k=m.given[1])
    special = {
        r"\sin A": m.sine,
        r"\sin 30^{\circ}": sp.Rational(1, 2),
        r"\angle A": 30,
        r"S_{ABCD}": m.area,
        r"\max(a,b)": m.answer,
    }
    for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = tag["data-inline-latex"]
        for label, val in special.items():
            formula = formula.replace(label, "(" + sp.latex(val) + ")")
        formula = formula.replace(r"^{\circ}", "").replace("d_1d_2", "d_1 d_2")
        formula = re.sub(
            r"(?<![A-Za-z\\])(ab|ah|ad|ka|bx)(?![A-Za-z])",
            lambda v: " ".join(v[0]),
            formula,
        )
        for label, val in sorted(vals.items(), key=lambda v: -len(v[0])):
            literal = "(" + sp.latex(val) + ")"
            formula = re.sub(
                r"(?<![A-Za-z_])" + re.escape(label) + r"(?![A-Za-z_])",
                lambda _, text=literal: text,
                formula,
            )
        formula = formula.replace(r"\sqrt{0}", "0")
        for statement in formula.split(r",\quad "):
            parts = re.split(r"(\\gt|\\lt|=)", statement)
            values = [float(TrigonometricParser(p).parse().value) for p in parts[::2]]
            assert len(values) > 1, statement
            for left, op, right in zip(values, parts[1::2], values[1:]):
                assert (
                    math.isclose(left, right, abs_tol=1e-8, rel_tol=1e-9)
                    if op == "="
                    else left > right
                    if op == r"\gt"
                    else left < right
                ), statement


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_methods_formulas_figures_and_source_answers(case):
    m = read(case["context"])
    result = plan(case)
    old = BeautifulSoup(
        section(case["context"], "answer")["html"], "html.parser"
    ).get_text(strip=True)
    assert float(result.answer.replace(",", ".")) == float(old.replace(",", "."))
    html = solution_html(result)
    verify(html, m)
    soup = BeautifulSoup(html, "html.parser")
    methods = soup.select("section")
    assert [s["data-solution-title"] for s in methods] == (
        ["Решение", "Альтернативное решение."]
        if m.mode in {"sine", "thirty"}
        else ["Решение"]
    )
    assert len(soup.find_all("img")) == (2 if m.mode == "transfer" else 0)
    if m.mode == "sine":
        assert "Дмитрия Д." in soup.get_text()
        assert "допустимая конфигурация" in soup.get_text()
        assert ("внутри стороны" in soup.get_text()) == (m.projection < m.a)
    if m.mode == "transfer":
        assert (
            "Исходная схема" in soup.get_text()
            and "уточнённой схеме" in soup.get_text()
        )
        assert ("для этих данных неверно" in soup.get_text()) == (m.projection > m.a)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_immutable_input_answers_unused_figures_replayed_without_duplicates(case):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before and result.answer == plan(case).answer
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "source") == section(before, "source")
    old, new = [
        BeautifulSoup(section(c, "condition")["html"], "html.parser")
        for c in [before, ctx]
    ]
    for soup in (old, new):
        for image in soup.find_all("img"):
            image.decompose()
    assert str(old) == str(new)
    assert len(ctx["normalized_content"]["assets"]) == (
        2 if case["group"] == "27611" else 1
    )


@pytest.mark.parametrize("g", GROUPS.values(), ids=lambda g: g["key"])
def test_bindings_require_actual_parent_frozen_manifest_and_readback(g):
    profile, handler = get_group_profile(g["key"]), get_handler(g["rule"])
    assert (
        profile.source_group_id == g["group_uuid"]
        and profile.existing_solution_policy == "rewrite"
    )
    assert (
        handler.parent_from_group_listing
        and handler.requires_frozen_manifest
        and handler.verify_content_readback
    )
    assert handler.diagram_builder and g["size"] >= 3
    handler.validate()


@pytest.mark.parametrize("g", GROUPS)
@pytest.mark.parametrize("change", ["method", "missing", "figure", "solution_figures"])
def test_unreviewed_parent_or_figures_block_preparation(g, change):
    case = next(c for c in CASES if c["task"] == g)
    args = {}
    if change == "method":
        args["parent_solution_html"] = (
            arguments(g)["parent_solution_html"] + "<p>Другой способ.</p>"
        )
    elif change == "missing":
        args["parent_solution_html"] = ""
    elif change == "figure":
        args["parent_asset_id"] = "foreign"
    else:
        args["parent_solution_assets"] = (
            () if g == "27611" else ({"asset_key": "image_2"},)
        )
    with pytest.raises(ContentPlanError):
        plan(case, **args)
