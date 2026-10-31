"""Explain excluded physical-angle series of a shifted linear factor."""

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_compile import C, S


def proof(branch, poles, *, scale=sp.S.One):
    from .exam_trigonometric_inverse import angles, ordered
    from .exam_trigonometric_proof import formula, series_lines

    residues = ordered(
        (q - branch.angle_shift) % 2
        for q in angles(branch.variable, branch.candidates[0])
    )
    html = ""
    for q in residues:
        if q in branch.residues:
            continue
        for pole in poles:
            value = sp.simplify(pole.subs({S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}))
            if value == 0:
                html += "<p>Эта серия нарушает исходную область определения и исключается:</p>"
                html += line(
                    series_lines(((q / scale, sp.Integer(2) / scale),))[0]
                    + r",\quad k\in\mathbb Z"
                )
                html += line(
                    formula(pole, "(" + sp.latex(q * sp.pi) + r"+2\pi k)") + "=0"
                )
    return html
