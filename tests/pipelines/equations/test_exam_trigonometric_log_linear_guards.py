"""Bounded affine log combinations and physical-angle domain filtering."""

import json
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.equations.exam_trigonometric import (
    Branch,
    analyze,
    select,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import read
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_log_linear import (
    compile_linear,
)
from solution_runner.pipelines.equations.exam_trigonometric_log_product import failed
from solution_runner.pipelines.equations.exam_trigonometric_selection import (
    restricted_series,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_log_linear.json"
    ).read_text()
)
R = sp.Rational


def case(key):
    return next(c for c in DATA["cases"] if c["task"] == key)


def parent(key):
    return section(case(key)["context"]["normalized_content"], "solution")["html"]


def analysis(formula, key="542039", prototype=None):
    _, _, i, b = read(case(key)["context"])
    return analyze(formula, i, b, parent(key) if prototype is None else prototype)


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_2(\sin x)+2\log_2(\cos x)=-1",
        r"13\log_2(\sin x)+13\log_2(\cos x)=-1",
        r"\log_2(\sin x)+\log_3(\cos x)=-1",
        r"\log_2(\sin x)+\log_2(\cos x)=21",
        r"\log_2(\sin x)+\log_2(\cos x)=\frac{1}{13}",
        r"\log_{(\sin x)}(\cos x)+\log_2(\sin x)=-1",
        r"\log_1(\sin x)+\log_2(\cos x)=-1",
        r"\log_{-2}(\sin x)+\log_2(\cos x)=-1",
        r"\log_2(\sin x)+\log_2(\cos x)=x",
        r"\log_2(\sin x)+\log_2(\cos x)=\sin x",
        r"\log_2(\sin^2 x)+\log_2(\cos^2 x)=-1",
        r"\log_2(\sin x+1)-\log_2(\cos x+1)=1",
        r"\log_2(\sin(\frac{x}{2}))+\log_2(\cos x)=-1",
        r"\log_2(\sin(13x))+\log_2(\cos x)=-1",
        r"\log_2(\sin x)+\log_2(\cos x)+\log_2(\sin 2x)=-1",
        r"\log_2(\sin^2 x+\cos^2 x)+\log_2(\sin^2 x+\cos^2 x)=-1",
    ],
)
def test_unreviewed_bases_weights_levels_degrees_and_periods_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        analysis(formula)


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_2(\sin x)\log_2(\cos x)=0",
        r"\log_2(\sin x)+2\log_2(\sin x)=0",
        r"\log_2(\sin2x)=\log_2(\sqrt{2}\cos x)",
    ],
)
def test_other_existing_log_families_are_left_to_their_original_compilers(formula):
    assert compile_linear(formula, parent("542039")) is None


@pytest.mark.parametrize(
    "scale,values,retained,expected",
    [
        (2, (R(1, 2),), (R(1, 12), R(5, 12)), ((R(1, 12), 2), (R(5, 12), 2))),
        (
            2,
            (R(1, 2),),
            (R(1, 12), R(5, 12), R(13, 12), R(17, 12)),
            ((R(1, 12), 1), (R(5, 12), 1)),
        ),
        (2, (R(1, 2),), (), ()),
        (3, (sp.S.Zero,), (sp.S.Zero, sp.S.One), ((sp.S.Zero, 1),)),
    ],
)
def test_physical_angle_series_keep_exactly_the_domain_filtered_orbits(
    scale, values, retained, expected
):
    b = Branch(
        S, S - values[0], values, values, retained, angle_scale=sp.Integer(scale)
    )
    actual = restricted_series(b)
    assert actual == expected
    assert select(actual, (0, 2, True, False))[0] == retained


@pytest.mark.parametrize("scale", [0, -1, 13, R(1, 2)])
def test_unsupported_physical_angle_scales_do_not_gain_a_fallback(scale):
    b = Branch(S, S, (0,), (0,), (0,), angle_scale=sp.sympify(scale))
    with pytest.raises(UnsupportedCondition):
        restricted_series(b)


def test_zero_cosine_at_a_cancelled_original_pole_is_still_excluded():
    f = r"\log_2(\sin(x+\frac{5\pi}{12})\cos x/\cos x)+\log_2(\sin(x+\frac{\pi}{12}))=-2"
    a = analysis(f)
    assert C in a.poles and a.scale == 1
    assert (
        a.residues == (sp.S.Zero,)
        and a.series == ((sp.S.Zero, 2),)
        and a.selected == (sp.S.Zero,)
    )
    assert failed(a, R(1, 2)) is not None


@pytest.mark.parametrize(
    "coefficient,level", [(r"\frac{1}{2}", r"-\frac{1}{2}"), ("-1", "1")]
)
def test_common_nonzero_rational_log_weight_is_divided_exactly(coefficient, level):
    f = (
        coefficient
        + r"\log_2\sin(x+\frac{5\pi}{12})+"
        + coefficient
        + r"\log_2\sin(x+\frac{\pi}{12})="
        + level
    )
    a = analysis(f)
    assert a.residues == (R(1, 12), R(5, 12)) and a.series == (
        (R(1, 12), 2),
        (R(5, 12), 2),
    )
    assert a.log_product.equality.linear.common == sp.Rational(
        coefficient.replace(r"\frac{1}{2}", "1/2")
    )


def test_a_different_square_base_pair_and_phase_use_the_same_proven_method():
    _, f, _, _ = read(case("673035")["context"])
    a = analysis(f.replace("2025", "9"), "673035")
    assert a.log_product.equality.linear.bases == (9, 3) and a.series == (
        (-R(1, 6), 2),
        (-R(5, 6), 2),
    )
    assert a.selected == (R(7, 6), R(11, 6))


@pytest.mark.parametrize(
    "mutation", ["empty", "domain", "arrow", "extra", "image_stage", "substitution"]
)
def test_unknown_parent_methods_or_figure_stage_are_not_silently_accepted(mutation):
    p = parent("542039")
    _, f, _, _ = read(case("542039")["context"])
    if mutation == "empty":
        p = ""
    if mutation == "domain":
        p = p.replace(r"\Rightarrow", r"\iff")
    if mutation == "arrow":
        p = p.replace(r"\log_2", r"\ln")
    if mutation == "extra":
        p += "<p>Другое решение.</p>"
    if mutation == "substitution":
        p += '<p><span data-inline-latex="t=\\sin x"></span></p>'
    if mutation == "image_stage":
        s = BeautifulSoup(p, "html.parser")
        im = s.img.extract()
        first = s.select("[data-inline-latex]")[0]
        prefix = s.new_tag("span")
        prefix["data-inline-latex"] = f
        first.insert_before(prefix)
        prefix.insert_after(im)
        p = str(s)
    with pytest.raises(UnsupportedCondition):
        analysis(f, prototype=p)


def test_existing_repeated_log_polynomial_is_not_intercepted():
    f = r"\log_2(2\sin^2(x))+2\log_2(2\sin^2(x))=0"
    assert compile_linear(f, parent("542039")) is None
