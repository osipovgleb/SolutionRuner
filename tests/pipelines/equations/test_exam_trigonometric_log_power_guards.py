"""Common-base and parent-chain extensions reject unrelated complete expressions."""

import json
from pathlib import Path

import pytest
import sympy as sp

from solution_runner.pipelines.equations.exam_trigonometric_log_parent import (
    definition_chain,
    small_fractions,
)
from solution_runner.pipelines.equations.exam_trigonometric_log_polynomial_style import (
    declared_levels,
)
from solution_runner.pipelines.equations.exam_trigonometric_log_powers import (
    compile_powers,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_log_powers.json"
    ).read_text()
)
PARENT = section(
    next(c for c in DATA["cases"] if c["task"] == "630105")["context"][
        "normalized_content"
    ],
    "solution",
)["html"]


@pytest.mark.parametrize(
    "formula",
    [
        r"1^{2\log_2^2(\sin x)}=1/1^{\log_2(\sin x)}",
        r"0^{2\log_2^2(\sin x)}=0/0^{\log_2(\sin x)}",
        r"5^{2\log_2^2(\sin x)}=7/7^{\log_2(\sin x)}",
        r"5^{2\log_2^2(\sin x)}=6/5^{\log_2(\sin x)}",
        r"5^{2\log_2^2(\sin x)}=0",
        r"5^{2\log_2^2(\sin x)}=-5",
        r"5^{2\log_2^2(\sin x)}=5/5^{\log_2(\cos x)}",
        r"5^{2\log_2^2(\sin x)}=5/5^{\log_3(\sin x)}",
        r"5^{2\log_2^2(\sin x)}=5/5^{1/\log_2(\sin x)}",
        r"5^{2\log_2^2(\sin x)+\sin x}=5/5^{\log_2(\sin x)}",
        r"5^{2\log_2^2(\sin x)}+1=5/5^{\log_2(\sin x)}",
        r"5^{2\log_2^3(\sin x)}=5/5^{\log_2(\sin x)}",
        r"5^{2\log_2^2(\sin x)}=5\cdot 5^{2\log_2^2(\sin x)}",
        r"5^{2\log_2^2(\sin x)}=5^{2\log_2^2(\sin x)}",
        r"5^{101\log_2^2(\sin x)}=5/5^{\log_2(\sin x)}",
        r"1001^{2\log_2^2(\sin x)}=1001/1001^{\log_2(\sin x)}",
        r"5^{2\log_2^2(\sin x/\cos x)}=5/5^{\log_2(\sin x/\cos x)}",
        r"5^{2\log_2^2(\sin x\cos x/\cos x)}=5/5^{\log_2(\sin x\cos x/\cos x)}",
        r"5^{2\log_1^2(\sin x)}=5/5^{\log_1(\sin x)}",
        r"5^{2\log_2^2(0)}=5/5^{\log_2(0)}",
    ],
)
def test_unreviewed_bases_sides_degrees_arguments_and_poles_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_powers(formula, PARENT)


CHAIN = r"\cos x+\sin2x+8=8\Leftrightarrow\cos x+2\cos x\sin x=0\Leftrightarrow\cos x(2\sin x+1)=0"


def test_parent_definition_chain_checks_both_exact_transitions():
    assert definition_chain([CHAIN])


@pytest.mark.parametrize(
    "old,new",
    [
        ("+8=8", "+8=9"),
        ("+8=8", "+0=0"),
        ("+8=8", "-8=-8"),
        ("2\\cos x\\sin x=0", "3\\cos x\\sin x=0"),
        ("2\\cos x\\sin x=0", "2\\cos x\\sin x=1"),
        ("(2\\sin x+1)=0", "(2\\sin x+2)=0"),
        ("(2\\sin x+1)=0", "(2\\sin x+1)=1"),
    ],
)
def test_incorrect_parent_definition_or_factorization_is_not_guessed(old, new):
    assert old in CHAIN and not definition_chain([CHAIN.replace(old, new)])


def test_single_digit_parent_fraction_preserves_both_actual_log_levels():
    f = r"\log_2(\cos x)=-1\\\log_2(\cos x)=\frac12\end{aligned}"
    assert declared_levels([f]) == ([sp.Rational(1, 2), sp.sqrt(2)], None)
    assert small_fractions(r"\frac{1}{2}+\frac123") == r"\frac{1}{2}+\frac123"


def test_missing_parent_common_base_method_is_rejected():
    with pytest.raises(UnsupportedCondition):
        compile_powers(
            r"5^{2\log_2^2(\sin x)}=5/5^{\log_2(\sin x)}", "<p>Решим уравнение.</p>"
        )
