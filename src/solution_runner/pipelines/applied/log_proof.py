"""Parent-style binary-log inversion and the two half-life interpretations."""

import sympy as sp

from ..calculus.common import answer
from ..probability.common import line
from .log_questions import DECAY_LAW

_OUTPUT = {
    "capacitor": ("U", r"\text{кВ}"),
    "water": ("T", r"{}^{\circ}\mathrm{C}"),
    "bell_volume": ("V_2", r"\text{л}"),
    "bell_pressure": ("p_2", r"\text{атм}"),
    "decay": ("t", r"\text{мин}"),
}


def final(a):
    label, unit = _OUTPUT[a.question.kind]
    if a.question.maximum:
        label = "{" + label + r"}_{\max}"
    decimal = answer(a.result).replace(",", "{,}")
    return line(
        label
        + "="
        + sp.latex(a.result)
        + ("=" + decimal if a.result.is_Integer is not True else "")
        + r"\ "
        + unit
    )


def scale(q):
    v = q.values
    raw = v["source_values"]
    if q.kind == "capacitor":
        return r"\alpha RC", r"\cdot".join(
            "(" + raw[key] + ")" for key in ["alpha", "resistance", "capacity"]
        )
    if q.kind == "water":
        return r"\alpha\frac{cm}{\gamma}", r"\frac{" + raw["alpha"] + r"\cdot" + raw[
            "heat"
        ] + r"\cdot" + raw["mass_flow"] + "}{" + raw["transfer"] + "}"
    return r"\alpha " + v.get("amount_symbol", "v") + " T", r"\cdot".join(
        "(" + raw[key] + ")" for key in ["alpha", "amount", "temperature"]
    )


def inverse(a):
    q = a.question
    v = q.values
    label, _ = _OUTPUT[q.kind]
    offset = v.get("offset", sp.Integer(0))
    excess = v["initial"] - offset
    denominator = label if not offset else label + "-(" + sp.latex(offset) + ")"
    ratio = (
        r"\frac{" + label + "}{" + sp.latex(v["initial"]) + "}"
        if q.kind == "bell_pressure"
        else r"\frac{" + sp.latex(excess) + "}{" + denominator + "}"
    )
    quantity = {
        "capacitor": "t",
        "water": "x",
        "bell_volume": "A",
        "bell_pressure": "A",
    }[q.kind]
    formula = q.formula.replace("T_room", r"T_{\mathrm{п}}").replace(
        "T_water", r"T_{\mathrm{в}}"
    )
    if v.get("amount_symbol") == r"\nu":
        formula = formula.replace(r"\alpha v", r"\alpha\nu")
    coefficient, numbers = scale(q)
    html = "<p>Подставим известные величины в формулу. Коэффициент перед логарифмом положителен:</p>"
    html += line(quantity + "=" + formula)
    html += line(coefficient + "=" + numbers + "=" + sp.latex(q.scale))
    domain = (
        sp.latex(v["initial"]) + r"\leq " + label
        if q.kind == "bell_pressure"
        else sp.latex(offset) + "<" + label + r"\leq" + sp.latex(v["initial"])
    )
    html += "<p>Учитываем допустимую область и решаем уравнение:</p>"
    html += line(domain)
    html += line(sp.latex(q.scale) + r"\log_2" + ratio + "=" + sp.latex(v["level"]))
    html += line(
        r"\log_2"
        + ratio
        + r"=\frac{"
        + sp.latex(v["level"])
        + "}{"
        + sp.latex(q.scale)
        + "}="
        + sp.latex(a.exponent)
    )
    html += line(ratio + "=2^{" + sp.latex(a.exponent) + "}=" + sp.latex(a.factor))
    if q.kind == "bell_pressure":
        isolated = sp.latex(v["initial"]) + r"\cdot" + sp.latex(a.factor)
    else:
        isolated = (
            ("(" + sp.latex(offset) + ")+" if offset else "")
            + r"\frac{"
            + sp.latex(excess)
            + "}{"
            + sp.latex(a.factor)
            + "}"
        )
    html += line(label + "=" + isolated)
    if q.maximum:
        html += "<p>При указанном времени уравнение задаёт единственное допустимое напряжение; оно же является наибольшим возможным.</p>"
    return html + final(a)


def decay(a):
    q = a.question
    v = q.values
    html = (
        "<p>Подставим начальную массу и период полураспада в закон изменения массы:</p>"
    )
    html += line("m(t)=" + DECAY_LAW)
    html += line(
        sp.latex(v["initial"])
        + r"\cdot2^{-t/"
        + sp.latex(q.scale)
        + "}="
        + sp.latex(v["target"])
    )
    fraction = r"\frac{" + sp.latex(v["target"]) + "}{" + sp.latex(v["initial"]) + "}"
    reduced = sp.latex(v["target"] / v["initial"])
    html += line(
        r"2^{-t/"
        + sp.latex(q.scale)
        + "}="
        + fraction
        + ("=" + reduced if fraction != reduced else "")
    )
    html += line(r"2^{-t/" + sp.latex(q.scale) + "}=2^{" + sp.latex(-a.exponent) + "}")
    html += line(r"-\frac{t}{" + sp.latex(q.scale) + "}=" + sp.latex(-a.exponent))
    html += final(a)
    html += "<p>За каждый период полураспада масса уменьшается вдвое. То же время можно найти по количеству таких периодов:</p>"
    if a.exponent.is_Integer and 0 <= a.exponent <= 10:
        html += line(
            r"\longrightarrow".join(
                sp.latex(v["initial"] / 2**i) for i in range(int(a.exponent) + 1)
            )
            + r"\quad(\text{мг})"
        )
    else:
        html += line(r"m_n=\frac{m_0}{2^n},\quad n=" + sp.latex(a.exponent))
    html += line(
        "t="
        + sp.latex(a.exponent)
        + r"\cdot"
        + sp.latex(q.scale)
        + "="
        + sp.latex(a.result)
        + r"\ \text{мин}"
    )
    return html


def proof(a):
    return decay(a) if a.question.kind == "decay" else inverse(a)
