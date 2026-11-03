"""Independent intercepted-arc values for every cyclic-polygon proof equality."""

from solution_runner.pipelines.circles.cyclic_angle_model import RULES

MODES = frozenset(RULES.values())


def arc(name):
    return r"\overset{\frown}{" + name + "}"


def variables(m):
    a = m.given[0]
    if m.mode == "cyclic_opposite":
        return {
            r"\angle A": a,
            r"\angle C": 180 - a,
            arc("BCD"): 2 * a,
            arc("BAD"): 360 - 2 * a,
        }
    if m.mode == "triangle_arc_ratio":
        unit = 360 / sum(m.given)
        intercepted = max(m.given) * unit
        return {"x": unit, r"\beta": intercepted, r"\alpha": intercepted / 2}
    if m.mode == "cyclic_four_arcs":
        c, d = m.given[2:]
        return {arc("ADC"): c + d, arc("AD"): d, arc("CD"): c, r"\angle B": (c + d) / 2}
    if m.mode == "cyclic_arc_ratio":
        unit = 360 / sum(m.given)
        b, c = m.given[1:3]
        return {
            "x": unit,
            arc("BC"): b * unit,
            arc("CD"): c * unit,
            arc("BCD"): (b + c) * unit,
            r"\angle A": (b + c) * unit / 2,
        }
    b = m.given[1]
    if m.mode == "cyclic_largest":
        return {
            "a": a,
            "b": b,
            r"\gamma": 180 - a,
            r"\delta": 180 - b,
            r"\alpha": 180 - min(a, b),
            r"\max\{\gamma,\delta\}": 180 - min(a, b),
        }
    total = a + b if m.mode == "cyclic_sum" else a
    ad = a if m.mode == "cyclic_sum" else b
    cd = b if m.mode == "cyclic_sum" else a - b
    return {
        r"\angle ABC": total,
        r"\angle ABD": ad,
        r"\angle CAD": cd,
        arc("AD"): 2 * ad,
        arc("CD"): 2 * cd,
        arc("ADC"): 2 * total,
    }
