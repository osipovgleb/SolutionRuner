"""Certify a polynomial radical times a logarithm, retaining both parent methods."""

from dataclasses import dataclass
from functools import cmp_to_key

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_exponential import X, select_roots
from .exam_logarithmic_algebra import roots
from .exam_logarithmic_branches import Analysis, Branch, allowed, constraints
from .exam_logarithmic_input import SYMBOLS
from .exam_rational import Selection
from .exam_scalar import compare


@dataclass(frozen=True)
class RadicalProduct:
    radicand: sp.Expr
    level: sp.Expr
    domain: sp.Set


def analyze_product(atoms, expression, radicand, interval, bounds, parent):
    if (
        len(atoms) != 1
        or atoms[0].base.has(X)
        or atoms[0].root
        or atoms[0].denominator
        or any(s in parent for s in ("ещё одно решение", "другим способом"))
        or not all(
            s in parent
            for s in (
                "первый множитель",
                "второй множитель",
                "примечание",
                "область определения",
            )
        )
    ):
        raise UnsupportedCondition(
            "one radical-log product with candidate checks and its full-domain note is required"
        )
    atom = atoms[0]
    v, z = SYMBOLS[3], atom.symbol
    scale = expression.coeff(v).coeff(z)
    if scale.is_Rational is not True or scale == 0:
        raise UnsupportedCondition("a nonzero constant radical-log product is required")
    level = sp.cancel(-expression.subs(v, 0) / (scale * z))
    if (
        level.is_Rational is not True
        or not 0 <= level <= 20
        or level.q > 12
        or sp.expand(expression - scale * (v - level) * z) != 0
        or any(
            not 1 <= sp.Poly(p, X).degree() <= 2
            or any(c.is_Rational is not True for c in sp.Poly(p, X).all_coeffs())
            for p in (radicand, atom.argument)
        )
    ):
        raise UnsupportedCondition(
            "one affine radical factor and two rational linear/quadratic operands are required"
        )
    branches = tuple(
        Branch(kind, p, tuple(sorted(roots(p), key=cmp_to_key(compare))), source)
        for kind, p, source in (
            ("radical", radicand - level**2, ()),
            ("level", atom.argument - 1, (atom, 0, 1)),
        )
    )
    conditions = (*constraints(atoms), (radicand, "nonnegative"))
    accepted = [
        r for branch in branches for r in branch.candidates if allowed(r, conditions)
    ]
    full, selected = select_roots(accepted, bounds)
    domain = sp.Intersection(
        sp.solve_univariate_inequality(radicand >= 0, X, relational=False),
        sp.solve_univariate_inequality(atom.argument > 0, X, relational=False),
    )
    return Analysis(
        Selection(full, selected, interval, bounds),
        atoms,
        atoms,
        expression,
        expression,
        conditions,
        branches,
        (),
        "radical-product-note",
        radical_product=RadicalProduct(radicand, level, domain),
    )
