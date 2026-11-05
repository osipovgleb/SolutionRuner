"""Compare all triangular-prism tetrahedra and five-vertex hulls with independent slices."""

import itertools
from types import SimpleNamespace

import pytest
import sympy as sp
from prism_region_oracle import coordinates, sliced_volume

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.prism_region import solve

NAMES = ("A", "B", "C", "A_1", "B_1", "C_1")


@pytest.mark.parametrize(
    "names",
    list(itertools.combinations(NAMES, 4)) + list(itertools.combinations(NAMES, 5)),
)
def test_every_triangular_tetrahedron_and_truncated_prism(names):
    p = coordinates(
        SimpleNamespace(body="triangle", given=(sp.Integer(7), sp.Integer(9)))
    )
    expected = sliced_volume(p, names, sp.Integer(9))
    if expected == 0:
        with pytest.raises(ContentPlanError):
            solve("triangle", names, ("7", "9"))
    else:
        assert solve("triangle", names, ("7", "9")).answer == expected


@pytest.mark.parametrize(
    "area,height", [("0", "3"), ("-2", "3"), ("3", "0"), ("3", "-2")]
)
def test_nonpositive_dimensions_are_rejected(area, height):
    with pytest.raises(ContentPlanError):
        solve("triangle", ("A", "B", "C", "A_1"), (area, height))
