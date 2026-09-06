from fractions import Fraction

import pytest

from solution_runner.pipelines.core.numbers import (
    NumberFormatError,
    exact_integer_root,
    format_answer,
    format_latex_fraction,
    parse_rational,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("-12", Fraction(-12)),
        ("0,125", Fraction(1, 8)),
        ("2{,}5", Fraction(5, 2)),
        (r"\frac{7}{12}", Fraction(7, 12)),
        (r"-\frac{3}{5}", Fraction(-3, 5)),
    ],
)
def test_parse_rational_exactly(source: str, expected: Fraction) -> None:
    assert parse_rational(source) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Fraction(7), "7"),
        (Fraction(1, 8), "0,125"),
        (Fraction(-3, 40), "-0,075"),
    ],
)
def test_format_platform_answer(value: Fraction, expected: str) -> None:
    assert format_answer(value) == expected


def test_repeating_answer_requires_an_explicit_fraction_policy() -> None:
    with pytest.raises(NumberFormatError):
        format_answer(Fraction(1, 3))
    assert format_answer(Fraction(1, 3), allow_latex_fraction=True) == r"\frac{1}{3}"
    assert format_latex_fraction(Fraction(-4, 9)) == r"-\frac{4}{9}"


def test_exact_integer_roots_fail_closed() -> None:
    assert exact_integer_root(343, 3) == 7
    assert exact_integer_root(-32, 5) == -2
    with pytest.raises(NumberFormatError):
        exact_integer_root(12, 2)
