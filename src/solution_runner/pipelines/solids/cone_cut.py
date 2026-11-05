"""Compute cut-cone volumes from reviewed diagram dimensions and shared sector fractions."""

import sympy as sp

from ..core.errors import ContentPlanError
from .cone_model import ConeQuantity
from .cone_sources import DATA, source_bytes
from .measurements import positive, sector_fraction


def solve(kind, given):
    values = tuple(positive(str(v)) for v in given)
    if len(values) != 3:
        raise ContentPlanError("three reviewed cut-cone dimensions are required")
    radius, height, angle = values
    answer = sp.simplify(radius**2 * height * sector_fraction(angle, kind) / 3)
    return ConeQuantity(
        "sector",
        kind,
        values,
        answer,
        input_kind="sector",
        radius=radius,
        height=height,
    )


def read(source):
    if source not in DATA["sectors"]:
        raise ContentPlanError("the numbered cut-cone figure needs review")
    source_bytes(source)
    f = DATA["sectors"][source]
    return solve(f["kind"], f["given"])
