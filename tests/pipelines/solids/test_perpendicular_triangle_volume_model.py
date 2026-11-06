"""Section intersections and tetrahedral determinants do not rely on printed answers."""

import pytest
import sympy as sp
from volume_sections_source_cases import raw, replace

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.perpendicular_triangle_volume_model import read


def verify(m):
    a, r = m.q["a"], m.q["MT_fraction"]
    U, B = sp.Matrix([-a / 2, 0, 0]), sp.Matrix([a / 2, 0, 0])
    M, X = sp.Matrix([0, sp.sqrt(3) * a / 2, 0]), sp.Matrix([0, 0, sp.sqrt(3) * a / 2])
    P, T = (U + M) / 2, M + r * (B - M)
    actual = abs(sp.det(sp.Matrix.hstack(P - M, T - M, X - M))) / 6
    assert sp.simplify(actual - m.answer) == 0
    normal = (P - X).cross(T - X)
    fraction = sp.simplify(normal.dot(X - M) / normal.dot(-M))
    assert sp.simplify(fraction - m.q["ME_fraction"]) == 0
    assert sp.simplify(fraction / (1 - fraction) - m.q["cut_ratio"]) == 0
    if m.names[2] == "inequality":
        delta = (U - T).norm() ** 2 - (B - P).norm() ** 2
        assert sp.simplify(delta - m.q["difference"]) == 0 and delta > 0


@pytest.mark.parametrize(
    "task,answer",
    [
        ("501549", 375 * sp.sqrt(3) / 8),
        ("501555", 24),
        ("505241", 24),
        ("511363", sp.Rational(81, 8)),
    ],
)
def test_all_original_statements_and_claims(task, answer):
    m = read(raw(task))
    assert sp.simplify(m.answer - answer) == 0
    verify(m)


@pytest.mark.parametrize(
    "division,claim", [("1: 1", "1: 1"), ("5: 2", "4: 7"), ("1: 2", "4: 3")]
)
def test_other_edge_divisions_have_the_true_median_ratio(division, claim):
    m = read(
        replace(
            "501549",
            ("BT: TM = 3: 1", "BT: TM = " + division),
            ("отношении 1: 2", "отношении " + claim),
        )
    )
    verify(m)


@pytest.mark.parametrize(
    "task,changes",
    [
        ("501549", [("10\\sqrt{3}", "5")]),
        ("501555", [("BC = 8", "BC = 3")]),
        ("511363", [("BC=6", "BC=9")]),
    ],
)
def test_resized_triangles_recompute_the_complete_volume(task, changes):
    verify(read(replace(task, *changes)))


@pytest.mark.parametrize(
    "task,changes",
    [
        ("501549", [("отношении 1: 2", "отношении 1: 3")]),
        ("501555", [("BT: TM = 1: 3", "BT: TM = 1: 1")]),
        ("501549", [("середина AM", "середина CM")]),
        ("501549", [("10\\sqrt{3}", "0")]),
    ],
)
def test_false_claims_wrong_midpoints_and_degenerate_lengths_are_rejected(
    task, changes
):
    with pytest.raises(ContentPlanError):
        read(replace(task, *changes))
