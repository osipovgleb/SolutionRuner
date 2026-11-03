"""Independent lengths and exact sine values for circumference quantity proofs."""

import sympy as sp

SINES = {
    30: sp.Rational(1, 2),
    45: sp.sqrt(2) / 2,
    60: sp.sqrt(3) / 2,
    90: sp.S.One,
    120: sp.sqrt(3) / 2,
    135: sp.sqrt(2) / 2,
    150: sp.Rational(1, 2),
}
MODES = {
    "polygon_vertices",
    "right_radius",
    "right_hypotenuse",
    "right_legs",
    "isosceles_diameter",
    "sine_radius",
    "sine_side",
    "hexagon_side",
    "hexagon_diameter",
}


def variables(m):
    v = m.given[0]
    if m.mode == "polygon_vertices":
        return {
            "n": 360 / (180 - v),
            r"\alpha": v,
            r"\angle OAB": v / 2,
            r"\angle ABO": v / 2,
            r"\angle AOB": 180 - v,
        }
    if m.mode.startswith("right_"):
        if m.mode == "right_legs":
            a, b = m.given[:2]
            hyp = sp.sqrt(a * a + b * b)
        else:
            hyp = v if m.mode == "right_radius" else 2 * v
            a, b = 3 * hyp / 5, 4 * hyp / 5
        return {"AB": hyp, "AC": a, "BC": b, "R": hyp / 2, "D": hyp}
    if m.mode == "isosceles_diameter":
        return {
            r"\angle A": 30,
            r"\angle B": 30,
            r"\sin A": sp.Rational(1, 2),
            r"\sin30^{\circ}": sp.Rational(1, 2),
            "BC": v,
            "d": 2 * v,
        }
    if m.mode.startswith("sine_"):
        angle = m.given[1]
        sine = SINES[int(angle)]
        radius = v / (2 * sine) if m.mode == "sine_radius" else v
        return {
            "AB": 2 * radius * sine,
            "R": radius,
            r"\sin C": sine,
            r"\sin" + str(int(angle)) + r"^{\circ}": sine,
        }
    radius = v if m.mode == "hexagon_side" else v / 6
    return {
        "R": radius,
        "P": 6 * radius,
        "a": radius,
        "AB": radius,
        "AO": radius,
        "OA": radius,
        "OB": radius,
        "D": 2 * radius,
        r"\angle AOB": 60,
    }
