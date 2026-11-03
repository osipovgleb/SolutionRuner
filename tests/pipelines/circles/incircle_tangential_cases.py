"""Independent side-length witnesses for tangential quadrilateral proof checks."""

import sympy as sp

MODES = {
    "trapezoid_legs",
    "trapezoid_perimeter",
    "right_trapezoid_radius",
    "tangential_quad",
    "tangent_cuts",
}


def variables(m):
    if m.mode == "tangent_cuts":
        b, c, a = m.given
        return {
            "BQ": b / 2,
            "BR": b / 2,
            "CQ": c / 2,
            "CS": c / 2,
            "AS": a / 2,
            "AR": a / 2,
            "AB": (a + b) / 2,
            "BC": (b + c) / 2,
            "AC": (a + c) / 2,
            r"P_{BKM}": b,
            r"P_{CHO}": c,
            r"P_{AFN}": a,
            r"P_{ABC}": a + b + c,
        }
    if m.mode == "trapezoid_legs":
        a, c = m.given
        height = min(a, c) / 2
        difference = sp.sqrt(a * a - height * height) + sp.sqrt(c * c - height * height)
        b, d = (a + c - difference) / 2, (a + c + difference) / 2
        perimeter = 2 * (a + c)
    elif m.mode == "trapezoid_perimeter":
        perimeter = m.given[0]
        a = c = perimeter / 4
        b, d = perimeter / 8, 3 * perimeter / 8
    elif m.mode == "right_trapezoid_radius":
        perimeter, c = m.given
        a = perimeter / 2 - c
        difference = sp.sqrt(c * c - a * a)
        b, d = (perimeter / 2 - difference) / 2, (perimeter / 2 + difference) / 2
    elif m.target == "perimeter":
        a, c = m.given
        perimeter = 2 * (a + c)
        b, d = (a + c) / 3, 2 * (a + c) / 3
    elif m.target == "fourth_side":
        a, b, c = m.given
        d, perimeter = a + c - b, 2 * (a + c)
    elif m.target == "opposite_side":
        perimeter, a = m.given
        c, b, d = perimeter / 2 - a, perimeter / 6, perimeter / 3
    else:
        perimeter, a, b = m.given
        c, d = perimeter / 2 - a, perimeter / 2 - b
    result = {
        "AB": a,
        "BC": b,
        "CD": c,
        "AD": d,
        "P": perimeter,
        r"P_{ABCD}": perimeter,
        "p": perimeter / 2,
        "m": (b + d) / 2,
    }
    if m.mode == "right_trapezoid_radius":
        result["r"] = a / 2
    if m.mode == "tangential_quad" and m.target == "larger_side":
        result.update(a=a, b=b, c=c, d=d)
        result[r"\max\{c,d\}"] = max(c, d)
    return result
