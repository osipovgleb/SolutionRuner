"""Independent regular-hexagon coordinates check each translated angle and plane."""

import pytest
import sympy as sp
from volume_sections_source_cases import raw, replace

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.hexagonal_pyramid_skew_model import read


def verify(m):
    a, e = m.q["a"], m.q["e"]
    p = {
        name: sp.Matrix([a * sp.sin(i * sp.pi / 3), a * sp.cos(i * sp.pi / 3), 0])
        for i, name in enumerate("ABCDEF")
    }
    p["S"] = sp.Matrix([0, 0, sp.sqrt(e * e - a * a)])
    line = m.names[0]
    u, v = p["S"] - p["B"], p[line[1]] - p[line[0]]
    cosine = sp.simplify(abs(u.dot(v)) / (u.norm() * v.norm()))
    assert sp.simplify(cosine - m.q["cosine"]) == 0
    if m.names[2] == "angle_equal":
        assert v.cross(p["E"] - p["B"]) == sp.zeros(3, 1)
    else:
        plane = m.names[2]
        base = "AE" if plane == "SBD" else "AD"
        normal = (p[plane[1]] - p["S"]).cross(p[plane[2]] - p["S"])
        assert sp.simplify(normal.dot(p[base[1]] - p[base[0]])) == 0
        assert normal.dot(p[base[0]] - p["S"]) != 0


@pytest.mark.parametrize(
    "task,answer",
    [
        ("484567", sp.pi / 3),
        ("511467", sp.Rational(1, 6)),
        ("507675", sp.Rational(1, 4)),
    ],
)
def test_native_angles_and_plane_parallelism(task, answer):
    m = read(raw(task))
    assert sp.simplify(m.answer - answer) == 0
    verify(m)


@pytest.mark.parametrize(
    "task,changes",
    [
        ("484567", [("равны 1,", "равны 3,"), ("равны 2,", "равны 10,")]),
        ("511467", [("равны 12,", "равны 5,"), ("равны 36.", "равны 11.")]),
        ("507675", [("равны 1,", "равны 2,"), ("равны 2.", "равны 5.")]),
    ],
)
def test_changed_edges_preserve_the_actual_geometric_claims(task, changes):
    verify(read(replace(task, *changes)))


@pytest.mark.parametrize("edge", ["0", "1", "-2"])
def test_collapsed_or_nonpositive_pyramids_are_rejected(edge):
    with pytest.raises(ContentPlanError):
        read(replace("484567", ("равны 2,", "равны " + edge + ",")))


@pytest.mark.parametrize(
    "old,new", [("плоскость SBD", "плоскость SBC"), ("прямой AE", "прямой AD")]
)
def test_individually_swapping_one_plane_claim_label_is_rejected(old, new):
    with pytest.raises(ContentPlanError):
        read(replace("511467", (old, new)))
