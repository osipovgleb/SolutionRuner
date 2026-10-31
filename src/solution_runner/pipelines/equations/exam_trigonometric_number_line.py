"""Validate mixed finite/periodic roots in reviewed line and circle figures."""

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_affine_selection import isolated
from .exam_trigonometric_inverse import decode


def validate_isolated(entry, a):
    if (
        a.affine is None
        or tuple(map(sp.Rational, entry["isolated_roots"])) != a.affine.roots
    ):
        raise UnsupportedCondition(
            "the algebraic factor must match the figure's isolated roots"
        )
    selected = tuple(decode(q) for q in entry["isolated_selected"])
    if selected != isolated(a.affine.roots, a.bounds):
        raise UnsupportedCondition(
            "the isolated roots must be selected in physical radians"
        )


def validate(entry, a):
    validate_isolated(entry, a)
    bounds = tuple(decode(q) for q in entry["bounds"][:2]) + tuple(entry["bounds"][2:])
    labels = tuple(decode(q) for q in entry["labels"])
    residues = tuple(decode(q) for q in entry["residues"])
    if (
        bounds != a.bounds
        or labels != a.selected
        or residues != a.residues
        or a.selection_method != "number_line"
    ):
        raise UnsupportedCondition(
            "the number-line interval and complete root sets must match the equation"
        )
