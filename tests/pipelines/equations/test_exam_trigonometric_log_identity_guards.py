"""Unreviewed logarithm identities retain strict base, argument and pole guards."""

import json
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import read
from solution_runner.pipelines.equations.exam_trigonometric_log_variable import (
    compile_variable,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_log_identities.json"
    ).read_text()
)
R = sp.Rational


def case(key):
    return next(c for c in DATA["cases"] if c["task"] == key)


def parent(key):
    return section(case(key)["context"]["normalized_content"], "solution")["html"]


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_1(\cos x)\log_{\cos x}(\sin^2x)=-1",
        r"\log_{-2}(\cos x)\log_{\cos x}(\sin^2x)=-1",
        r"\log_2(\sin x)\log_{\cos x}(\sin^2x)=-1",
        r"2\log_2(\cos x)\log_{\cos x}(\sin^2x)=-1",
        r"\log_2(\cos x)+\log_{\cos x}(\sin^2x)=-1",
        r"\log_2(\cos x)\log_{\cos x}(\sin^2x)=-\sin x",
        r"\log_2(\cos x)\log_{\cos x}(\sin^4x)=-1",
        r"\log_2(\cos(3x))\log_{\cos(3x)}(\sin^2x)=-1",
        r"\log_2(\cos x)\log_{\cos x}(\sin^2(x+\frac{\pi}{6}))=-1",
    ],
)
def test_chain_identity_requires_the_complete_product_and_reviewed_original_operands(
    formula,
):
    with pytest.raises(UnsupportedCondition):
        compile_variable(formula, parent("696418"))


@pytest.mark.parametrize(
    "formula",
    [
        r"\cos^{-2}x+\sin^{-1}(x-\frac{\pi}{2})=\log_{\sin x}(\cos^2x)",
        r"\cos^{-2}x+\sin^{-1}(x-\frac{\pi}{2})=\log_{\sin x}(\sin^5x)",
        r"\cos^{-2}x+\sin^{-1}(x-\frac{\pi}{2})=\log_{\sin x}^2(\sin^2x)",
        r"\cos^{-3}x+\sin^{-1}(x-\frac{\pi}{2})=\log_{\sin x}(\sin^2x)",
        r"\log_{\sin x}(\sin^2x)=2",
    ],
)
def test_base_power_identity_needs_original_reciprocal_quadratic_and_poles(formula):
    with pytest.raises(UnsupportedCondition):
        compile_variable(formula, parent("636515"))


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_{\sin x}(\cos2x)+\log_{\cos2x}(\sin x)=3",
        r"\log_{\sin x}(\cos2x)+\log_{\cos2x}(\cos x)=2",
        r"2\log_{\sin x}(\cos2x)+\log_{\cos2x}(\sin x)=2",
        r"\log_{\sin x}(\cos2x)+\log_{\cos2x}(\sin x)=x",
    ],
)
def test_reciprocal_identity_requires_mutual_original_bases_and_one_repeated_unit_level(
    formula,
):
    with pytest.raises(UnsupportedCondition):
        compile_variable(formula, parent("704819"))


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_{\sin2x}(\sin x)\log_{\sin2x}(\cos x)=\frac{1}{4}",
        r"\log_{\frac{1}{2}\sin2x}(2\sin x)\log_{\frac{1}{2}\sin2x}(\cos x)=\frac{1}{4}",
        r"\log_{\frac{1}{2}\sin2x}(\sin x)\log_{\frac{1}{2}\sin2x}(\cos x)=\frac{1}{3}",
        r"\log_{\frac{1}{2}\sin2x}(\sin x)+\log_{\frac{1}{2}\sin2x}(\cos x)=\frac{1}{4}",
    ],
)
def test_product_base_identity_cannot_assume_new_bases_are_below_one_without_the_unit_circle_certificate(
    formula,
):
    with pytest.raises(UnsupportedCondition):
        compile_variable(formula, parent("634660"))


def test_commuted_chain_factors_reuse_the_same_mathematical_certificate_and_domains():
    c = case("696418")
    _, _, i, b = read(c["context"])
    a = analyze(r"\log_{\cos x}(\sin^2x)\cdot\log_2(\cos x)=-1", i, b, parent("696418"))
    assert select(a.series, (0, 2, True, False))[0] == (R(1, 4), R(7, 4))
    assert a.selected == (-R(15, 4),)
    assert a.log_product.equality.identity.atoms[0].base == 2


def test_commuted_common_base_factors_keep_the_original_positive_quadrant():
    _, _, i, b = read(case("634660")["context"])
    a = analyze(
        r"\log_{\frac{1}{2}\sin2x}(\cos x)\cdot\log_{\frac{1}{2}\sin2x}(\sin x)=\frac{1}{4}",
        i,
        b,
        parent("634660"),
    )
    assert a.residues == (R(1, 4),) and a.selected == (R(17, 4),)


def test_the_own_base_power_identity_uses_the_actual_affine_base_domain():
    _, _, i, b = read(case("636515")["context"])
    a = analyze(
        r"\cos^{-2}x+\sin^{-1}(x-\frac{\pi}{2})=\log_{1+\sin x}((1+\sin x)^2)",
        i,
        b,
        parent("636515"),
    )
    assert a.residues == (R(1, 3), R(5, 3)) and a.selected == (R(17, 3), R(19, 3))


def test_selection_companion_cannot_be_moved_before_the_chain_computation():
    soup = BeautifulSoup(parent("696418"), "html.parser")
    second = soup.find_all("img")[1].extract()
    soup.img.insert_after(second)
    with pytest.raises(UnsupportedCondition):
        compile_variable(read(case("696418")["context"])[1], str(soup))


@pytest.mark.parametrize("key", ["634660", "636515", "696418", "704819"])
def test_an_unreviewed_extra_substitution_is_not_silently_dropped(key):
    _, f, _, _ = read(case(key)["context"])
    with pytest.raises(UnsupportedCondition):
        compile_variable(
            f, parent(key) + '<p><span data-inline-latex="u=\\sin x"></span></p>'
        )


def test_reciprocal_circle_cannot_be_moved_past_back_substitution():
    soup = BeautifulSoup(parent("704819"), "html.parser")
    extra = soup.new_tag("span")
    extra["data-inline-latex"] = r"\sin x=\frac{1}{2}"
    soup.img.insert_before(extra)
    with pytest.raises(UnsupportedCondition):
        compile_variable(read(case("704819")["context"])[1], str(soup))


def test_chain_pair_cannot_lose_or_swap_the_original_domain_circle():
    soup = BeautifulSoup(parent("696418"), "html.parser")
    first = soup.img.extract()
    soup.append(first)
    with pytest.raises(UnsupportedCondition):
        compile_variable(read(case("696418")["context"])[1], str(soup))
