"""Unreviewed variable-base identities must not relax fixed-base log parsing."""

import json
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.equations.exam_trigonometric import analyze
from solution_runner.pipelines.equations.exam_trigonometric_circle import read
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_log_equality import (
    compile_equality,
)
from solution_runner.pipelines.equations.exam_trigonometric_log_variable import (
    compile_variable,
)
from solution_runner.pipelines.equations.exam_trigonometric_log_variable_methods import (
    certify,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_log_variable.json"
    ).read_text()
)


def case(key):
    return next(c for c in DATA["cases"] if c["task"] == key)


def parent(key):
    return section(case(key)["context"]["normalized_content"], "solution")["html"]


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_{\sin x}(1+\cos x)=-1",
        r"\log_{\sin x}(1+\cos x)=5",
        r"\log_{\sin x}(1+\cos x)=\frac12",
        r"\log_{\sin x}(1+\cos x)=x",
        r"\log_{\sin x}(1+\cos x)=\sin x",
        r"2\log_{\sin x}(1+\cos x)=2",
        r"\log_{1+\sin x}(1+\cos x)=2",
        r"\log_{\sin x+\cos x}(1+\cos x)=2",
        r"\log_{\sin^2x}(1+\cos x)=2",
        r"\log_{\sin(\frac{x}{2})}(1+\cos x)=2",
        r"\log_{\sin(13x)}(1+\cos x)=2",
        r"\log_{\sin(x+\frac\pi6)}(1+\cos x)=2",
        r"\log_{\sin x}(\sin^2x+\cos^2x)=0",
        r"\log_{\sin x}(\log_{\sin x}(1+\cos x))=2",
        r"\log_{\sin x}(1+\cos x)=\log_{\cos x}3+2",
        r"\log_{\sin x}(1+\cos x)=\log_{\sin x}(-3)+2",
        r"\log_{\sin x}(1+\cos x)=\log_{\sin x}(\cos x)+2",
        r"\log_{\sin x}(\cos x+\frac{\sin x}{\sin x})=2",
        r"\log_{\sin x}^2(1+\cos x)=2",
    ],
)
def test_unreviewed_levels_bases_arguments_angles_and_original_poles_fail_closed(
    formula,
):
    with pytest.raises(UnsupportedCondition):
        compile_variable(formula, parent("559574"))


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_2(\sin x)=1",
        r"\log_2(\sin x)+\log_2(\cos x)=-1",
        r"2^{\log_2^2(\sin x)}=2^{\log_2(\sin x)}",
    ],
)
def test_fixed_base_families_are_not_intercepted(formula):
    assert compile_variable(formula, parent("559574")) is None


def test_existing_fixed_base_definition_parser_still_rejects_variable_bases():
    with pytest.raises(UnsupportedCondition):
        compile_equality(r"\log_{\sin x}(1+\cos x)=2", parent("559574"))


@pytest.mark.parametrize(
    "prototype",
    [
        "<p>Решите численно.</p>",
        "<p>Сделаем другую замену.</p>",
    ],
)
def test_an_unknown_parent_cannot_supply_a_new_definition_method(prototype):
    with pytest.raises(UnsupportedCondition):
        compile_variable(r"\log_{\sin x}(1+\cos x)=2", prototype)


@pytest.mark.parametrize("key", ["559574", "626504", "650209", "668195", "698474"])
def test_an_extra_substitution_or_alternative_is_not_silently_discarded(key):
    _, formula, interval, bounds = read(case(key)["context"])
    for tail in (
        "<p>Другое решение.</p>",
        '<p><span data-inline-latex="t=\\sin x"></span></p>',
    ):
        with pytest.raises(UnsupportedCondition):
            analyze(formula, interval, bounds, parent(key) + tail)


@pytest.mark.parametrize(
    "raw,base,method",
    [
        (S + C, S, "quadratic"),
        (S**4 + C, S, "cos_double"),
        (S + C, C, "cot"),
        (S * C, S, "cot_double"),
        (S + C, S, "unknown"),
    ],
)
def test_a_parent_method_requires_its_exact_algebraic_certificate(raw, base, method):
    with pytest.raises(UnsupportedCondition):
        certify(raw, base, method)


def test_cosine_definition_keeps_all_three_original_domain_conditions():
    _, f, i, b = read(case("650209")["context"])
    a = analyze(f, i, b, parent("650209"))
    from solution_runner.pipelines.equations.exam_trigonometric_log_product import (
        conditions,
        failed,
    )

    assert conditions(a) == (
        (C, "positive"),
        (C - 1, "nonzero"),
        (a.log_product.argument, "positive"),
    )
    assert failed(a, sp.S.Zero) == (C - 1, "nonzero", 0)
    assert failed(a, sp.S.One) is not None


def test_an_unreviewed_intermediate_figure_stage_is_not_moved_to_the_definition():
    soup = BeautifulSoup(parent("698474"), "html.parser")
    extra = soup.new_tag("span")
    extra["data-inline-latex"] = r"x=\pi k"
    soup.img.insert_before(extra)
    with pytest.raises(UnsupportedCondition):
        compile_variable(read(case("698474")["context"])[1], str(soup))
