"""All native answers follow from independent circle geometry and solid determinants."""

import pytest
import sympy as sp
from round_solid_source_cases import CASES, changed, raw

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids import (
    concentric_sphere_section_model,
    cylinder_axis_chord_model,
    cylinder_rectangle_volume_model,
    hex_pyramid_insphere_model,
)

READERS = {
    "502115": concentric_sphere_section_model.read,
    "520803": cylinder_axis_chord_model.read,
    "520938": cylinder_axis_chord_model.read,
    "502023": hex_pyramid_insphere_model.read,
    "514026": cylinder_rectangle_volume_model.read,
}
ANSWERS = {
    "502115": 13,
    "504945": 12,
    "502135": 10,
    "520803": sp.atan(sp.Rational(2, 3)),
    "520853": sp.atan(sp.Rational(17, 6)),
    "520879": sp.Rational(420, 29),
    "520915": 12,
    "520938": 435 * sp.pi,
    "520945": 525 * sp.pi,
    "697030": 440 * sp.pi,
    "697050": 455 * sp.pi,
    "502023": 64 * (11 - 4 * sp.sqrt(7)) * sp.pi,
    "502054": 12 * (7 - 4 * sp.sqrt(3)) * sp.pi,
    "511368": 16 * (11 - 4 * sp.sqrt(7)) * sp.pi,
    "514026": 144 + 72 * sp.sqrt(3),
    "517181": 64 + 32 * sp.sqrt(3),
    "517219": 12 + 6 * sp.sqrt(3),
    "524051": 12 + 6 * sp.sqrt(3),
    "524073": 64 + 32 * sp.sqrt(3),
}


def eq(a, b):
    assert sp.simplify(a - b) == 0


def volume(a, b, c, d):
    return abs(sp.det(sp.Matrix.hstack(b - a, c - a, d - a))) / 6


def verify(m):
    g = dict(m.given)
    if m.mode == "concentric_sphere_parallel_section_area":
        inner2 = 4 + g["alpha_area"] / sp.pi
        outer2 = inner2 + g["beta_area"] / sp.pi
        eq(sp.pi * (outer2 - 4), m.answer)
    elif m.mode == "cylinder_axis_chord_geometry":
        a, b, h = g["a"], g["b"], g["H"]
        d = sp.sqrt(a * a + b * b)
        A, C = sp.zeros(3, 1), sp.Matrix([d, 0, 0])
        B = sp.Matrix([a * a / d, a * b / d, 0])
        C1 = C + sp.Matrix([0, 0, h])
        eq((B - A).norm(), a)
        eq((B - C).norm(), b)
        eq((B - C / 2).norm(), d / 2)
        eq((A - B).dot(C1 - B), 0)
        target = m.names[0]
        answer = (
            sp.acos(h / (C1 - A).norm())
            if target == "angle"
            else (B - A).cross(C1 - A).norm() / (C1 - A).norm()
            if target == "distance"
            else sp.pi * d * h
        )
        assert (
            sp.simplify(answer - m.answer) == 0
            or target == "angle"
            and sp.simplify(sp.tan(answer) - sp.tan(m.answer)) == 0
        )
    elif m.mode == "hexagonal_pyramid_insphere_area":
        e, h = g["e"], g["H"]
        a = sp.sqrt(e * e - h * h)
        base = 3 * sp.sqrt(3) * a * a / 2
        lateral = 3 * a * sp.sqrt(h * h + 3 * a * a / 4)
        radius = base * h / (base + lateral)
        eq(radius, m.q["sphere_radius"])
        apothem = sp.sqrt(3) * a / 2
        eq((h - radius) * apothem / sp.sqrt(h * h + apothem * apothem), radius)
        eq(4 * sp.pi * radius * radius, m.answer)
    else:
        R, h = g["R"], g["H"]
        q = sp.sqrt(3) * R / 2
        A, B = sp.Matrix([-q, -R / 2, h]), sp.Matrix([-q, R / 2, h])
        M, N = sp.Matrix([-q, -R / 2, 0]), sp.Matrix([-q, R / 2, 0])
        C = sp.Matrix([R, 0, 0])
        eq((A - N).norm(), (B - M).norm())
        eq(volume(C, A, B, N) + volume(C, A, N, M), m.answer)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_native_condition_and_answer(case):
    m = READERS[case["group"]](raw(case["task"]))
    eq(m.answer, ANSWERS[case["task"]])
    verify(m)


@pytest.mark.parametrize(
    "group,task,pairs",
    [
        (
            "502115",
            "502115",
            [("равна 8.", r"равна 3\pi."), ("равна 5.", r"равна 2\pi.")],
        ),
        (
            "520803",
            "520803",
            [
                ("AB = 6", "AB = 5"),
                ("BB_1 = 15", "BB_1 = 7"),
                ("B_1C_1 = 8", "B_1C_1 = 12"),
            ],
        ),
        ("502023", "502023", [("равно 10,", "равно 15,"), ("равна 6,", "равна 9,")]),
        (
            "514026",
            "514026",
            [("высотой 12", "высотой 5"), ("основания 6", "основания 3")],
        ),
    ],
)
def test_other_exact_dimensions_keep_the_same_geometric_construction(
    group, task, pairs
):
    verify(READERS[group](changed(task, *pairs)))


@pytest.mark.parametrize(
    "task,pairs",
    [
        ("502023", [("равно 10,", "равно 6,")]),
        ("502023", [("высота равна 6", "высота равна 7")]),
        ("502054", [("равен 30°", "равен 45°")]),
    ],
)
def test_collapsed_pyramids_or_false_claims_are_rejected(task, pairs):
    with pytest.raises(ContentPlanError):
        hex_pyramid_insphere_model.read(changed(task, *pairs))


@pytest.mark.parametrize(
    "group,task,old,new",
    [
        ("502115", "502115", "касается меньшего шара", "касается большего шара"),
        ("520803", "520803", "пересекает ось", "не пересекает ось"),
        ("514026", "514026", "с одной стороны", "с разных сторон"),
        ("514026", "524051", "по одну сторону", "по разные стороны"),
    ],
)
def test_changed_tangency_axis_or_side_conditions_do_not_match(group, task, old, new):
    assert READERS[group](changed(task, (old, new))) is None


def test_missing_source_answer_is_not_used_to_compute_the_sphere_area():
    case = next(c for c in CASES if c["task"] == "511368")
    assert not any(
        s["key"] == "answer" for s in case["context"]["normalized_content"]["sections"]
    )
    eq(hex_pyramid_insphere_model.read(raw("511368")).answer, ANSWERS["511368"])
