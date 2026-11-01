"""Unreviewed log definitions and inverse-angle certificates fail closed."""

import json
from pathlib import Path

import pytest
import sympy as sp

from solution_runner.pipelines.equations.exam_exponential import X
from solution_runner.pipelines.equations.exam_inverse_bounds import validate
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_inverse import decode
from solution_runner.pipelines.equations.exam_trigonometric_log_equality import (
    compile_equality,
)
from solution_runner.pipelines.equations.exam_trigonometric_log_product import (
    branches,
    failed,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_log_equalities.json"
    ).read_text()
)


def parent(key):
    return section(
        next(c for c in DATA["cases"] if c["task"] == key)["context"][
            "normalized_content"
        ],
        "solution",
    )["html"]


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_1(\sin x)=1",
        r"\log_{\cos x}(\sin x)=1",
        r"\log_{-2}(\sin x)=1",
        r"\log_2^2(\sin x)=1",
        r"\log_2(\sin x)+1=2",
        r"\log_2(\sin^3x)=1",
        r"\log_2(\sin^2x+\cos^2x)=1",
        r"\log_2(2)=1",
        r"\log_4(2^{3x}-\sqrt{3}\cos x-\sin 2x)=x",
        r"\log_4(2^{2x+1}-\sqrt{3}\cos x-\sin 2x)=x",
        r"\log_4(2^{x}+2^{x}-\sqrt{3}\cos x-\sin 2x)=x",
        r"\log_4(2^{2x}-\sqrt{3}\cos x-\sin 2x)=x^2",
        r"\log_3(\sin x+x)=1",
        r"\log_3(\sin 2x)=\log_2(\sqrt{2}\cos x)",
        r"\log_2(\sin 2x)=\log_2(1+\cos x)",
        r"\log_4(2^{2x}+(\sin x)^3)=x",
        r"\log_4(2^{2x}-\sin 2x)=\sqrt{x}",
    ],
)
def test_unreviewed_bases_powers_targets_and_nonpolynomial_remainders_fail_closed(
    formula,
):
    with pytest.raises(UnsupportedCondition):
        compile_equality(formula, parent("517509"))


def test_a_cancelled_original_cosine_pole_still_removes_the_whole_cosine_zero_case():
    e = compile_equality(
        r"\log_4(2^{2x}+\frac{\cos x}{\cos x}-1-\sqrt{3}\cos x-\sin 2x)=x",
        parent("517509"),
    )
    assert C in e.poles and failed(e, sp.Rational(1, 2)) is not None
    assert tuple(sorted({q for b in branches(e, C) for q in b.residues})) == (
        sp.Rational(4, 3),
        sp.Rational(5, 3),
    )


def test_matching_powers_are_an_exact_real_identity_not_a_float_comparison():
    assert (
        sp.simplify(2 ** (2 * X) - 4**X) == 0
        and sp.simplify(5 ** (3 * X) - 125**X) == 0
    )
    e = compile_equality(r"\log_4(2^{2x}-\sqrt{3}\cos x-\sin 2x)=x", parent("517509"))
    for q in (sp.Rational(1, 2), sp.Rational(4, 3), sp.Rational(5, 3)):
        assert failed(e, q) is None
    assert e.raw == -sp.sqrt(3) * C - 2 * S * C


@pytest.mark.parametrize(
    "value",
    [
        {"rational": "1", "acos": {"sqrt": 0, "coefficient": "1/4"}, "coefficient": 1},
        {
            "rational": "1",
            "acos": {"sqrt": True, "coefficient": "1/4"},
            "coefficient": 1,
        },
        {"rational": "1", "acos": {"sqrt": 2, "coefficient": "2"}, "coefficient": 1},
        {
            "rational": "1",
            "acos": {"sqrt": 2, "coefficient": "1/4", "unknown": 1},
            "coefficient": 1,
        },
        {"rational": "1", "atan": {"sqrt": 2, "coefficient": "1/4"}, "coefficient": 1},
        {"rational": "1", "acos": {"sqrt": 2, "coefficient": "1/4"}, "coefficient": 2},
    ],
)
def test_unreviewed_quadratic_inverse_labels_cannot_enter_source_metadata(value):
    with pytest.raises(UnsupportedCondition):
        decode(value)


@pytest.mark.parametrize(
    "q",
    [
        2 * sp.acos(sp.sqrt(2) / 4) / sp.pi,
        sp.acos(sp.log(2)) / sp.pi,
        sp.acos((sp.sqrt(2) + sp.sqrt(3)) / 4) / sp.pi,
    ],
)
def test_inverse_scope_remains_bounded_to_one_unit_quadratic_angle(q):
    with pytest.raises(UnsupportedCondition):
        validate(q)


def test_the_bounded_quadratic_cosine_label_and_its_closed_selection_are_accepted():
    a = decode(
        {"rational": "1", "acos": {"sqrt": 2, "coefficient": "1/4"}, "coefficient": 1}
    )
    assert a == 1 + sp.acos(sp.sqrt(2) / 4) / sp.pi
    validate(a)


def test_missing_parent_or_extra_alternative_cannot_choose_a_different_method():
    f = r"\log_4(2^{2x}-\sqrt{3}\cos x-\sin 2x)=x"
    for prototype in (
        "<p>Решите численно.</p>",
        parent("517509") + "<p>Приведём другое решение пункта б).</p>",
    ):
        with pytest.raises(UnsupportedCondition):
            compile_equality(f, prototype)
