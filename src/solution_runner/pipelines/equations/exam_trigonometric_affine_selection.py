"""Select isolated roots in physical radians, keeping periodic series separate."""

from functools import cmp_to_key

import sympy as sp

from .exam_scalar import compare


def isolated(roots, bounds):
    lo, hi, lc, uc = bounds
    result = []
    for root in roots:
        left, right = compare(root, lo * sp.pi), compare(root, hi * sp.pi)
        if (left > 0 or (left == 0 and lc)) and (right < 0 or (right == 0 and uc)):
            result.append(root / sp.pi)
    return tuple(result)


def combine(periodic, roots, bounds):
    values = set(periodic) | set(isolated(roots, bounds))
    return tuple(
        sorted(values, key=cmp_to_key(lambda a, b: compare(a * sp.pi, b * sp.pi)))
    )


def all_roots(a):
    from .exam_trigonometric_proof import families

    finite = r"\{" + r";\ ".join(sp.latex(r) for r in a.affine.roots) + r"\}"
    if not a.series:
        return finite
    periodic = (
        r"\{"
        + r";\ ".join(f.removeprefix("x=") for f in families(a))
        + r"\mid k\in\mathbb Z\}"
    )
    return finite + r"\cup" + periodic
