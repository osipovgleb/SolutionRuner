"""Check equal-side angle values using independent coordinate constructions."""

import math

from test_altitude_quad_preparation import angle
from test_orthocenter_preparation import coordinates, intersect


def checked_values(m):
    if m.mode == "exterior":
        return _exterior_values(m)
    points = coordinates(m.alpha, m.beta)
    if m.mode == "extension":
        length = math.dist(points["B"], points["C"])
        points["D"] = (points["B"][0] + length, 0)
        assert points["A"][0] < points["B"][0] < points["D"][0]
        assert abs(math.dist(points["B"], points["D"]) - length) < 1e-9
        values = {
            "A": m.alpha,
            "B": m.beta,
            "C": m.gamma,
            "CBD": 180 - m.beta,
            "D": m.beta / 2,
        }
        for name, value in [
            ("ABC", m.beta),
            ("CBD", 180 - m.beta),
            ("BDC", m.beta / 2),
            ("BCD", m.beta / 2),
        ]:
            assert abs(angle(points, name) - float(value)) < 1e-8
        count = 9
    else:
        length = math.dist(points["A"], points["C"])
        base = math.dist(points["A"], points["B"])
        points["E"] = (length, 0)
        points["D"] = tuple(
            (length * points["B"][i] + base * points["C"][i]) / (length + base)
            for i in [0, 1]
        )
        assert 0 < points["E"][0] < points["B"][0]
        assert (
            abs(
                math.dist(points["D"], points["C"])
                - math.dist(points["D"], points["E"])
            )
            < 1e-8
        )
        assert abs(angle(points, "CAD") - angle(points, "EAD")) < 1e-8
        values = {
            "B": m.beta,
            "C": m.gamma,
            "DEA": m.gamma,
            "DEB": 180 - m.gamma,
            "BDE": m.gamma - m.beta,
        }
        for name in ["DEA", "DEB", "BDE"]:
            assert abs(angle(points, name) - float(values[name])) < 1e-8
        count = 7
    return values, count


def _exterior_values(m):
    points = coordinates(m.alpha, m.beta)
    ac = math.dist(points["A"], points["C"])
    bc = math.dist(points["B"], points["C"])
    c, b = points["C"], points["B"]
    points["E"] = tuple(c[i] + bc * c[i] / ac for i in [0, 1])
    bisector = tuple((b[i] - c[i]) / bc + c[i] / ac for i in [0, 1])
    points["D"] = intersect(c, bisector, points["A"], (1, 0))
    forward = m.beta > m.alpha
    assert points["D"][0] > points["B"][0] if forward else points["D"][0] < 0
    assert abs(math.dist(c, points["E"]) - bc) < 1e-9
    assert abs(angle(points, "BCD") - angle(points, "DCE")) < 1e-8
    assert abs(angle(points, "BDC") - angle(points, "CDE")) < 1e-8
    half = (m.alpha + m.beta) / 2
    values = {
        "A": m.alpha,
        "B": m.beta,
        "BCE": m.alpha + m.beta,
        "BCD": half if forward else 180 - half,
        "CBD": 180 - m.beta if forward else m.beta,
        "BDC": abs(m.beta - m.alpha) / 2,
        "CDE": abs(m.beta - m.alpha) / 2,
        "BDE": abs(m.beta - m.alpha),
    }
    for name in ["BCE", "BCD", "CBD", "BDC", "CDE", "BDE"]:
        assert abs(angle(points, name) - float(values[name])) < 1e-8
    return values, 9 if forward else 8
