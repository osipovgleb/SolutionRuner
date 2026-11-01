"""A log zero requires a defined log, including at radical-free boundary roots."""

import pytest
import sympy as sp

from solution_runner.pipelines.equations.exam_trigonometric import select
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_log_product import (
    branches,
    compile_product,
    prepare,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

R = sp.Rational


@pytest.mark.parametrize(
    "formula",
    [
        r"(\sin x)\log_1(\cos x)=0",
        r"(\sin x)\log_{-2}(\cos x)=0",
        r"(\sin x)\log_{\tg x}(\cos x)=0",
        r"(\sin x)\log_=0",
        r"(\sin x)\log_3(\log_2(\cos x))=0",
        r"(\sin x)\log_3(\cos x)+1=0",
        r"(\sin x)(\log_3(\cos x)+\log_2(\sin x))=0",
        r"\frac{(\sin x)\log_3(\cos x)}{\log_2(\sin x)+1}=0",
        r"\frac{(\sin x)\log_3(\cos x)}{\sin x}=0",
        r"(\sin x)\log_3(\sin^2x+\cos^2x)=0",
        r"(\sin x)\log_3(\cos x)=1",
    ],
)
def test_unknown_bases_extra_log_terms_and_cancelled_factors_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_product(formula)


@pytest.mark.parametrize("base", [r"2", r"\frac{1}{2}"])
def test_valid_log_zero_at_argument_one_and_zero_algebraic_factor_is_retained(base):
    c = compile_product(r"(2\cos x-1)\log_{" + base + r"}(-\sin x)=0")
    result = branches(c, C)
    assert tuple(sorted({q for b in result for q in b.residues})) == (R(3, 2), R(5, 3))
    assert any(R(3, 2) in b.residues for b in result)
    # -sin x=1 is valid; an argument bounded by one does not mean a nonzero log.
    assert select(
        tuple((q, 2) for b in result for q in b.residues), (0, 2, True, False)
    )[0] == (R(3, 2), R(5, 3))


def test_original_log_denominator_removes_argument_one_before_zero_cases():
    c = compile_product(r"\frac{(\sin x)\log_3(2\cos x)}{\log_4(\cos x)}=0")
    assert all(0 not in b.residues for b in branches(c, S))
    assert 0 in next(b.candidates for b in branches(c, S) if b.variable == S)


def test_parent_cannot_request_division_by_a_factor_not_proved_nonzero():
    c = compile_product(r"(\sin x)\log_3(\cos x)=0")
    with pytest.raises(UnsupportedCondition):
        prepare(c, "<p>Можно разделить обе части уравнения на синус.</p>")
    assert c.log_product.divide == 1
    for parent in (
        r"<p>Наибольшее значение аргумента равно 0,8.</p>",
        r'<span data-inline-latex="\log_3(\cos x)=0"></span>',
    ):
        with pytest.raises(UnsupportedCondition):
            prepare(c, parent)
