"""Compute cut-cylinder volumes from reviewed, byte-pinned diagram measurements."""

import json
from importlib.resources import files

import sympy as sp

from ..core.errors import ContentPlanError
from .measurements import positive, sector_fraction

DATA = json.loads(
    files(__package__).joinpath("assets/cylinder_cut_inputs.json").read_text()
)


def solve(mode, kind, given):
    values = tuple(positive(str(v)) for v in given)
    if len(values) != 3:
        raise ContentPlanError("three reviewed cylinder dimensions are required")
    if mode == "sector":
        radius, height, angle = values
        answer = radius**2 * height * sector_fraction(angle, kind)
    elif mode == "stepped":
        radius, total, base = values
        if total < base:
            raise ContentPlanError("the full height must reach the lower cylinder top")
        answer = radius**2 * (base + (total - base) / 2)
    elif mode == "annular":
        outer, inner, height = values
        if outer <= inner:
            raise ContentPlanError(
                "the bore radius must be smaller than the outer radius"
            )
        answer = (outer**2 - inner**2) * height
    else:
        raise ContentPlanError("the cylinder cut needs geometric review")
    return values, sp.simplify(answer)


def read(source):
    from .cylinder_model import CylinderQuantity
    from .cylinder_sources import source_bytes

    if source not in DATA["figures"]:
        raise ContentPlanError("the numbered cylinder figure needs review")
    source_bytes(source)
    f = DATA["figures"][source]
    values, answer = solve(f["mode"], f["kind"], f["given"])
    return CylinderQuantity(f["mode"], values, answer, f["kind"], True)
