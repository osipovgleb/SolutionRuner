"""Unit-circle cubic products, two square methods, and reciprocal sine sums."""

import gzip
import hashlib
import json
import math
import re
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import (
    analyze,
    select,
)
from solution_runner.pipelines.equations.exam_trigonometric_angle_product import (
    compile_product,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_inverse import (
    decode,
    ordered,
    turn,
)
from solution_runner.pipelines.equations.exam_trigonometric_prepared_circle import (
    recipe,
)
from solution_runner.pipelines.equations.exam_trigonometric_square_factor import square
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_sum_products.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
s, c = sp.sin(X), sp.cos(X)
SELECTED = {"637451":"3/2 7/4 2 11/4","638055":"1/3 1/2","648010":"-3/4 -1/4 1/6 1/4","655095":"-2 0 2 3 4","656658":"-2","660666":"4 14/3 5","660730":"-7/2 -8/3 -5/2","660749":"-7/2 -17/6 -5/2 -13/6","660750":"7/2 23/6 9/2","660676":"-3 -11/4 -2","667316":"-47/12 -15/4 -13/4 -37/12 -35/12 -11/4","669743":"-1/(9*pi) 1/(9*pi) 1/(6*pi)","670351":"1/12 1/6 1/4 5/12","671985":"-29/12 -7/4","672509":"0 1/20 3/20 1/5 1/4 7/20 2/5 9/20"}
RESIDUES = {"637451":"0 3/4 3/2 7/4","638055":"1/3 1/2 2/3","648010":"1/6 1/4 3/4 5/6 5/4 7/4","655095":"0 2 3 4","656658":"0","660666":"0 2/3 1 4/3","660730":"1/2 4/3 3/2 5/3","660749":"1/2 7/6 3/2 11/6","660750":"1/2 7/6 3/2 11/6","660676":"0 3/4 1 5/4","667316":"1/12 1/4 3/4 11/12 13/12 5/4 7/4 23/12","669743":"1/(9*pi) 1/(6*pi) 5/(9*pi)","670351":"1/12 1/6 1/4","671985":"1/4 11/12 19/12","672509":"0 1/20 3/20 1/5 1/4 7/20"}
PERIOD = {"655095":6, "669743":2/(3*sp.pi), "670351":sp.Rational(1,3), "672509":sp.Rational(2,5)}
ORIGINAL = {
"637451":s**3+c**3-sp.cos(2*X),
"638055":2*s**2-(2+sp.sqrt(3))*sp.cos(sp.pi/2-X)+sp.sqrt(3),
"648010":sp.sin(2*X-sp.pi/2)-sp.sin(3*X-sp.pi)-s,
"655095":sp.sin(2*X/3)**2+2*sp.sin(2*X/3)*sp.sin(X/3)+1-sp.cos(X/3)**2,
"656658":2*c**2+s**2-2*c**3,
"660666":sp.sin(2*X)-sp.sin(X-sp.pi),
"660730":sp.sin(2*X)-sp.sqrt(3)*sp.cos(sp.pi-X),
"660749":sp.sin(2*X)-sp.cos(sp.pi-X),
"660750":sp.sin(2*X)-sp.cos(X-sp.pi),
"660676":sp.cos(sp.pi/2+2*X)-sp.sqrt(2)*s,
"667316":sp.sqrt(3)*(sp.cos(4*X)+1)-2*sp.cos(2*X)*(2-sp.cos(4*X)),
"669743":sp.sin(6*sp.pi*X)-sp.cos(3*sp.pi*X)-sp.sqrt(2)*sp.cos(3*sp.pi*X-sp.pi/4)+1,
"670351":sp.sin(6*X)**2/2-sp.sin(3*sp.pi/2-3*X)**2,
"671985":1/s+1/c-2*sp.sqrt(2),
"672509":2*sp.sin(5*X)**2-sp.tan(5*X)**2}
IDENTITY = {
"637451":(s+c)*(1-c)*(1+s),
"638055":(2*s-sp.sqrt(3))*(s-1),
"648010":sp.cos(2*X)*(2*s-1),
"655095":sp.sin(X/3)**2*(2*sp.cos(X/3)+1)**2,
"656658":-(c-1)*(2*c*c+c+1),
"660666":s*(2*c+1),
"660730":c*(2*s+sp.sqrt(3)),
"660749":c*(2*s+1),"660750":c*(2*s+1),
"660676":-s*(2*c+sp.sqrt(2)),
"667316":2*sp.cos(2*X)*(2*sp.cos(2*X)**2+sp.sqrt(3)*sp.cos(2*X)-3),
"669743":(2*sp.cos(3*sp.pi*X)-1)*(sp.sin(3*sp.pi*X)-1),
"670351":sp.cos(3*X)**2*(2*sp.sin(3*X)**2-1),
"671985":sp.sqrt(2)*(sp.sin(X+sp.pi/4)-sp.sin(2*X))/(s*c),
"672509":sp.sin(5*X)**2*(2*sp.cos(5*X)**2-1)/sp.cos(5*X)**2}


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(c):
    return next(
        s["html"]
        for p in CASES
        if p["task"] == c["group"]
        for s in p["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(c):
    _, f, i, b = read(c["context"])
    return analyze(f, i, b, parent(c))


def plan(c, context=None):
    ctx = context or c["context"]
    handler = get_handler(get_group_profile(c["group"]).content_rule_key)
    generated = tuple(
        {
            **spec,
            "source_asset_id": "preview-" + spec["sha256"][:16],
            "url": "/assets/preview-" + spec["sha256"][:16],
        }
        for spec in handler.diagram_specs(ctx)
    )
    return handler.plan(
        PlanInput(
            ctx, parent_solution_html=parent(c), generated_solution_assets=generated
        )
    )


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_extends_one_shared_rule(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 6, g["order"], "14")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_algebra_and_complete_and_selected_roots_are_independent(c):
    task = c["task"]
    a = analysis(c)
    assert sp.simplify(sp.expand_trig(ORIGINAL[task] - IDENTITY[task])) == 0
    assert a.selected == tuple(map(sp.sympify, SELECTED[task].split()))
    series, factor = (tuple((sp.cancel(q*sp.pi), sp.cancel(p*sp.pi)) for q,p in a.series), sp.pi) if task == "669743" else (a.series,sp.S.One)
    roots = select(series, (0, sp.cancel(PERIOD.get(task,2)*factor), True, False))[0]
    assert roots == tuple(sp.cancel(sp.sympify(q)*factor) for q in RESIDUES[task].split())
    for q in a.selected:
        assert sp.simplify(ORIGINAL[task].subs(X, q * sp.pi)) == 0


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(c):
    original = deepcopy(c["context"])
    p = plan(c)
    assert c["context"] == original
    changed = deepcopy(original)
    for s in changed["normalized_content"]["sections"]:
        if s["key"] in ("answer", "solution"):
            s["html"] = "<p>не использовать</p>"
    assert (
        plan(c, changed).answer == p.answer
        and plan(c, changed).solution_html == p.solution_html
    )
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert not key.startswith("section:condition")
        items = changed["normalized_content"][
            "assets" if key.startswith("asset:") else "sections"
        ]
        item = next((s for s in items if s["transformation_target_id"] == key), None)
        if item is None:
            item = {"transformation_target_id": key}
            items.append(item)
        item.update(t["value"])
    assert plan(c, changed).transformations == ()
    assert (
        changed["normalized_content"]["assets"][
            : len(original["normalized_content"]["assets"])
        ]
        == original["normalized_content"]["assets"]
    )




@pytest.mark.parametrize("c", CASES, ids=lambda c:c["task"])
def test_exact_source_figures_are_reused_with_previously_reviewed_correction(c):
    a = analysis(c)
    handler = get_handler(get_group_profile(c["group"]).content_rule_key)
    assets = c["context"]["normalized_content"]["assets"]
    specs = handler.diagram_specs(c["context"])
    assert bool(specs) == (c["task"] == "660676")
    if not assets:
        assert recipe(c["context"]) is None
        return
    asset = assets[0]["asset_id"]
    e = CIRCLES[asset]
    assert hashlib.sha256(gzip.decompress((DIRECTORY/(asset+".svgz")).read_bytes())).hexdigest() == e["sha256"]
    validate(e,a)
    residues = select(a.series,(0,2,True,False))[0]
    if e.get("point_scope") == "selected":
        residues = ordered(turn(q) for q in a.selected)
    assert tuple(map(decode,e["residues"])) == residues
    if c["task"] == "660676":
        assert e["task"] == "526702"
        assert e["corrected_file"] == "factor-negative-cosine-quarter-corrected.svg"
        assert (DIRECTORY/e["corrected_file"]).read_text() == specs[0]["svg_text"]
    assert len(BeautifulSoup(plan(c).solution_html,"html.parser").find_all("img")) == 1


def test_unit_circle_cubic_has_three_branches_and_keeps_homogeneous_first():
    a = analysis(case("637451"))
    assert a.unit_factors is not None and len(a.branches) == 3
    assert a.branches[0].original == S+C
    html = plan(case("637451")).solution_html
    assert "суммы кубов" in html and "все три" in html
    assert html.index("линейный множитель") < html.index(r"(\cos x)=1")
    assert (sp.S.Zero,sp.Integer(2)) in a.series and (sp.Rational(3,2),sp.Integer(2)) in a.series


def test_two_square_methods_have_same_complete_six_pi_period_and_selected_roots():
    from solution_runner.pipelines.equations.exam_trigonometric_selection import (
        equivalent_series,
    )

    a = analysis(case("655095"))
    assert a.square_product == (S**2,4*C*C+4*C+1)
    assert a.alternative.sum_product is not None and a.alternative.square_product is None
    assert a.alternative.sum_product.squared
    assert equivalent_series(a.series,a.alternative.series)
    assert select(a.series,(0,6,True,False))[0] == (0,2,3,4)
    html = plan(case("655095")).solution_html
    assert html.index("В оставшейся скобке") < html.index("Приведём другое решение") < html.index("сумму или разность")
    assert r"\frac{x}{2}" in html and r"\frac{x}{6}" in html
    assert "D=" not in html and not BeautifulSoup(html,"html.parser").find("img")


def test_methods_that_only_agree_on_first_two_pi_are_not_equivalent():
    from solution_runner.pipelines.equations.exam_trigonometric_selection import (
        equivalent_series,
    )

    first=((sp.S.Zero,sp.Integer(6)),)
    second=((sp.S.Zero,sp.Integer(6)),(sp.Integer(3),sp.Integer(6)))
    assert select(first,(0,2,True,False))[0] == select(second,(0,2,True,False))[0]
    assert not equivalent_series(first,second)


def test_positive_quadratic_factor_has_no_real_branch():
    a = analysis(case("656658"))
    assert a.series == ((0,2),)
    html = plan(case("656658")).solution_html
    assert "положительный старший коэффициент" in html and "отрицательный дискриминант" in html
    assert sp.discriminant(2*C*C+C+1,C) == -7


def test_scaled_cosine_cubic_keeps_double_angle_and_excludes_out_of_range_root():
    a = analysis(case("667316"))
    assert a.angle_product is None and a.scale == 2
    assert a.rewritten is None
    assert any(-sp.sqrt(3) in b.candidates and -sp.sqrt(3) not in b.values for b in a.branches)
    html = plan(case("667316")).solution_html
    assert "не входит в отрезок" in html and r"\cos(6" not in html


def test_reciprocal_sine_sum_preserves_domain_sum_difference_and_included_series():
    a = analysis(case("671985"))
    data = a.sum_product
    assert len(data.poles) == 2 and not data.squared
    assert data.product.has(sp.sin) and data.product.has(sp.cos)
    assert a.series == ((sp.Rational(1,4),sp.Rational(2,3)),)
    for k in range(-9,10):
        q=sp.Rational(1,4)+sp.Rational(2,3)*k
        assert sp.sin(q*sp.pi) != 0 and sp.cos(q*sp.pi) != 0
        assert sp.simplify(ORIGINAL["671985"].subs(X,q*sp.pi)) == 0
    html = plan(case("671985")).solution_html
    assert html.index(r"\sin x\ne0") < html.index("умножим")
    assert "Включённую серию" in html and "D=" not in html


def test_scaled_tangent_square_keeps_original_cosine_denominator_and_both_signs():
    a = analysis(case("672509"))
    assert a.scale == 5 and a.poles == (C,) and a.cleared_denominator == C**2
    assert a.factored_source == a.raw
    assert {b.variable for b in a.branches} == {S,C}
    assert all(b.square_level or sp.degree(b.polynomial,b.variable) == 1 for b in a.branches)
    assert all(sp.cos(5*sp.pi*q) != 0 for q in a.selected)
    assert sp.Rational(1,2) not in a.selected
    html = plan(case("672509")).solution_html
    assert r"(\cos 5 x)\ne0" in html and "D=" not in html
    assert len(a.series) == 3


@pytest.mark.parametrize("formula", [r"\sin x+\sin2x=0",r"\sin^2x+3\sin x\sin2x+\sin^2 2x=0",r"\sin^2x+2\sin x\cos2x+\cos^2 2x=0",r"\frac{\sin x}{\cos x}=0"])
def test_wrong_square_and_original_denominator_fail_closed(formula):
    from solution_runner.pipelines.equations.exam_trigonometric_sum_product import (
        compile_square,
    )

    with pytest.raises(UnsupportedCondition):
        compile_square(formula)


@pytest.mark.parametrize("right",["1",r"\sqrt{2}"])
def test_reciprocal_sum_rejects_unreviewed_levels(right):
    from solution_runner.pipelines.equations.exam_trigonometric_sum_product import (
        compile_reciprocal,
    )

    with pytest.raises(UnsupportedCondition):
        compile_reciprocal(r"\frac{1}{\sin x}+\frac{1}{\cos x}="+right)


def test_identity_certificate_rejects_a_changed_sum_or_a_pole_on_a_root():
    from solution_runner.pipelines.equations.exam_trigonometric_sum_product import (
        branches,
        equation,
    )

    a=analysis(case("671985"))
    with pytest.raises(UnsupportedCondition):
        equation(replace(a.sum_product,root=a.sum_product.root+1))
    with pytest.raises(UnsupportedCondition):
        branches(replace(a,sum_product=replace(a.sum_product,poles=(sp.sin(X-sp.pi/4),))))


@pytest.mark.parametrize("raw",[S**3+C**3-2*C*C+S*S,S*S+C*C-1,S**3+S*C+1])
def test_unrelated_unit_circle_polynomial_cannot_use_three_affine_factors(raw):
    from solution_runner.pipelines.equations.exam_trigonometric_methods import Equation
    from solution_runner.pipelines.equations.exam_trigonometric_unit_factors import (
        prepare,
    )

    assert prepare(Equation(raw,(),sp.S.One)) is None


@pytest.mark.parametrize("multiple",[2,5])
def test_scaled_tangent_reciprocal_identity_scales_the_domain_and_each_root(multiple):
    from solution_runner.pipelines.equations.exam_trigonometric_proof_methods import (
        method_proof,
    )

    formula = rf"\tg^{{2}}{multiple}x+\frac{{1}}{{\cos^{{2}}{multiple}x}}=3"
    html = rf'<p>Решим уравнение с помощью неравенств.</p><span data-inline-latex="\tg{multiple}x=1"></span>'
    a=analyze(formula,r"[0;\frac{\pi}{2}]",(sp.S.Zero,sp.pi/2,True,True),html)
    assert a.scale == multiple
    for q in a.selected:
        assert sp.cos(multiple*sp.pi*q) != 0
        assert sp.simplify(sp.tan(multiple*sp.pi*q)**2+1/sp.cos(multiple*sp.pi*q)**2-3) == 0
    _,proof = method_proof(a)
    assert rf"\cos {multiple} x\ne0" in proof
    assert rf"(\tg {multiple} x)" in proof
    assert all(p == sp.Rational(1,2*multiple) for _,p in a.series)

    mixed = rf"\tg{multiple}x+\sin{multiple}x+\cos{multiple}x=-1"
    b = analyze(mixed,r"[0;\frac{\pi}{2}]",(sp.S.Zero,sp.pi/2,True,True),html)
    _, proof = method_proof(b)
    assert rf"\sin {multiple} x=\cos {multiple} x\cdot\tg {multiple} x" in proof
    for q in b.selected:
        theta = multiple*sp.pi*q
        assert sp.cos(theta) != 0
        assert sp.simplify(sp.tan(theta)+sp.sin(theta)+sp.cos(theta)+1) == 0
    from solution_runner.pipelines.equations.exam_trigonometric import Branch
    from solution_runner.pipelines.equations.exam_trigonometric_phase_domain import (
        proof as excluded,
    )

    branch = Branch(S,S,(sp.S.Zero,),(sp.S.Zero,),(),angle_shift=sp.Rational(1,2))
    text = excluded(branch,(C,),scale=sp.Integer(multiple))
    assert rf"\frac{{\pi}}{{{2*multiple}}}" in text
