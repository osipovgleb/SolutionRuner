"""Bounds, overlapping log cases and native geometry cannot be inferred from saved roots."""

import gzip
import math
import re
from xml.etree import ElementTree as ET

import pytest
import sympy as sp

from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_log_methods import (
    upper_bound,
)
from solution_runner.pipelines.equations.exam_trigonometric_log_product import (
    branches,
    compile_product,
    prepare,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

R = sp.Rational


@pytest.mark.parametrize("argument", [C, -C, -2 * C, S * S, S / C])
def test_a_log_argument_can_reach_one_or_needs_another_bound(argument):
    with pytest.raises(UnsupportedCondition):
        upper_bound(argument)


@pytest.mark.parametrize(
    "argument,expected", [(-R(4, 5) * C, R(4, 5)), (R(1, 10) + R(4, 5) * S, R(9, 10))]
)
def test_maximum_is_computed_from_the_actual_affine_argument(argument, expected):
    assert upper_bound(argument) == expected


def test_denominator_only_log_has_no_extra_zero_log_case():
    c = compile_product(r"\frac{\sin x}{\log_3(\cos x)}=0")
    assert c.log_product.argument is None
    assert not any(b.residues for b in branches(c, S))


def test_overlapping_log_first_cases_keep_the_root_in_the_first_case():
    c = compile_product(r"(\sin x)\log_2(\cos x)=0")
    c = prepare(
        c,
        r'<p>Уравнение определено при положительном аргументе.</p><span data-inline-latex="\log_2(\cos x)=0"></span>',
    )
    assert c.log_product.log_first
    b = branches(c, S)
    assert b[0].residues == (sp.S.Zero,)
    assert all(not x.residues for x in b[1:])
    assert c.log_product.argument == C


@pytest.mark.parametrize("offset", [R(1, 2), sp.S.One, -sp.S.One])
def test_a_multiple_angle_remaining_factor_must_be_strictly_nonzero(offset):
    formula = r"\frac{\sin 2x(\cos 2x+(" + sp.latex(offset) + r"))}{\log_4(\cos x+1)}=0"
    c = compile_product(formula)
    parent = r'<p>При условиях области определения:</p><span data-inline-latex="\sin2x(\cos2x+2)=0\iff\sin2x=0"></span>'
    with pytest.raises(UnsupportedCondition):
        prepare(c, parent)


def test_a_parent_cannot_override_the_actual_maximum_by_its_old_number():
    c = compile_product(r"(\sin x)\log_3(-\cos x)=0")
    with pytest.raises(UnsupportedCondition):
        prepare(c, "<p>Наибольшее значение аргумента равно 0,8.</p>")


def test_two_source_figures_without_explicit_subparts_fail_closed():
    c = compile_product(r"(\sin x)\log_3(\cos x)=0")
    parent = r'<p>Уравнение определено при положительном аргументе.</p><span data-inline-latex="\log_3(\cos x)=0"></span><img/><img/>'
    with pytest.raises(UnsupportedCondition):
        prepare(c, parent)


def test_auxiliary_angle_figure_uses_its_native_axes_and_blue_arc_endpoints():
    aid, entry = next((aid, e) for aid, e in CIRCLES.items() if e["task"] == "696038")
    root = ET.fromstring(gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes()))
    axes = entry["native_axes"]
    assert len(axes) == 2 and all(
        any(n.tag.endswith("line") and n.attrib == a for n in root.iter()) for a in axes
    )
    vertical = next(a for a in axes if a["x1"] == a["x2"])
    horizontal = next(a for a in axes if a["y1"] == a["y2"])
    assert entry["circle"][:2] == [float(vertical["x1"]), float(horizontal["y1"])]
    tokens = re.findall(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+)", entry["native_circle_path"])
    assert tokens.pop(0) == "M"
    current = complex(float(tokens.pop(0)), float(tokens.pop(0)))
    ends = [[current.real, current.imag]]
    while tokens:
        cmd = tokens.pop(0)
        assert cmd in ("c", "S", "s")
        values = [float(tokens.pop(0)) for _ in range(6 if cmd == "c" else 4)]
        end = complex(*values[-2:])
        current = end if cmd == "S" else current + end
        ends.append([current.real, current.imag])
    assert len(ends) == 4
    assert all(
        math.dist(a, b) < 1e-9
        for a, b in zip(ends, entry["native_quarter_endpoints"], strict=True)
    )
    radius = (max(p[0] for p in ends) - min(p[0] for p in ends)) / 2
    assert math.isclose(entry["circle"][2], radius, abs_tol=1e-9)
    assert len(entry["green_markers"]) == 2
