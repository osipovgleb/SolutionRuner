"""Every native scalar, vector and coordinate equality is verified independently."""

import pytest
from skew_line_equation_oracle import verify
from skew_line_source_cases import CASES, read

from solution_runner.pipelines.solids.spatial_distance_proofs import render


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_native_equation_including_parent_alternatives(case):
    m = read(case)
    html = render(m, {})
    verify(html, m)
    if case["group"] == "699395":
        assert html.index("Решение векторами и координатами") < html.index(
            "без координат"
        )
        assert r"+\frac18\vec{a}\cdot\vec{b}" in html or m.names[0] == "half"
    if case["group"] == "509423":
        assert (
            html.index("теореме косинусов")
            < html.index("Через площадь")
            < html.index("Через половину угла")
        )
    if case["task"] == "511342":
        assert html.index("теорему косинусов") < html.index("Метод координат")
