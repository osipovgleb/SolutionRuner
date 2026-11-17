"""Arithmetic in coordinate-line options stays restricted to reviewed operators."""

import pytest

from solution_runner.pipelines.equations.coordinate_line_multiple_values import (
    _evaluate,
)
from solution_runner.pipelines.triangles.right.planner import RightTrianglePlanError


@pytest.mark.parametrize(
    ("expression", "values", "expected"),
    [
        ("ab+2c", {"a": -2, "b": 3, "c": 4}, 2),
        ("x^2-y", {"x": -3, "y": 2}, 7),
        ("-a+b", {"a": -2, "b": 3}, 5),
        ("x^-1", {"x": 2}, 0),
    ],
)
def test_reviewed_arithmetic(expression, values, expected):
    assert _evaluate(expression, values) == expected


@pytest.mark.parametrize("expression", ["1/2", "a.__class__", "1<<2", "[1]"])
def test_rejects_unreviewed_syntax(expression):
    with pytest.raises(RightTrianglePlanError):
        _evaluate(expression, dict.fromkeys("abcxy", 1))
