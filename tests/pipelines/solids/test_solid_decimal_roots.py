"""Ensure exact bounded rational radicands keep coefficients and existing scalar limits."""

import pytest
import sympy as sp

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.measurements import positive


@pytest.mark.parametrize(
    "raw,expected",
    [
        (r"\sqrt{0{,}75}", sp.sqrt(3) / 2),
        (r"3\sqrt{0.5}", 3 * sp.sqrt(2) / 2),
        (r"2\sqrt{0.125}", sp.sqrt(2) / 2),
    ],
)
def test_fractional_root_with_coefficient(raw, expected):
    assert positive(raw) == expected


@pytest.mark.parametrize("raw", [r"\sqrt{500000.5}", r"\sqrt{0.0}", r"-2\sqrt{0.25}"])
def test_radicand_range_and_positive_measurement_remain_enforced(raw):
    with pytest.raises(ContentPlanError):
        positive(raw)
