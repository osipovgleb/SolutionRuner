"""Preserve table substitution, periodicity and parity in numeric solutions."""

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .trig_angles import angle_text, signs


def _function(atom, q, sign=1):
    return (
        ("-" if sign < 0 else "")
        + chr(92)
        + atom.function
        + "("
        + angle_text(q, atom.degrees)
        + ")"
    )


def render(expression, calculation):
    parser = calculation.parser
    values = {s: a.actual() for s, a in parser.atoms.items()}
    actual = sp.simplify(calculation.original.xreplace(values))
    if actual != calculation.exact:
        raise UnsupportedCondition("the independent table substitution disagrees")
    html = "<p>Вычислим значения тригонометрических функций по таблице. При необходимости используем периодичность и чётность или нечётность:</p>"
    if any(a.q < 0 for a in parser.atoms.values()):
        html += line(r"\cos(-t)=\cos t,\quad\sin(-t)=-\sin t,\quad\tg(-t)=-\tg t")
    if any(abs(a.q) > 1 for a in parser.atoms.values()):
        html += line(
            r"\sin(t+2\pi)=\sin t,\quad\cos(t+2\pi)=\cos t,\quad\tg(t+\pi)=\tg t"
        )
    seen = set()
    for atom in parser.atoms.values():
        if atom.text in seen:
            continue
        seen.add(atom.text)
        current = atom.text
        q = atom.q
        direction = 1
        if q < 0:
            direction = 1 if atom.function == "cos" else -1
            q = -q
            step = _function(atom, q, direction)
            html += line(current + "=" + step)
            current = step
        period = 1 if atom.function in ("tg", "ctg") else 2
        normalized = q % period
        if normalized != q:
            step = _function(atom, normalized, direction)
            html += line(current + "=" + step)
            current = step
        ref = normalized % 1
        ref = min(ref, 1 - ref)
        sign = signs(atom.function, normalized) * direction
        if ref != normalized and sign:
            step = _function(atom, ref, sign)
            html += line(current + "=" + step)
            current = step
        html += line(current + "=" + sp.latex(atom.actual()))
    html += "<p>Подставим табличные значения и выполним арифметические действия:</p>"
    substituted = sp.latex(
        calculation.original,
        symbol_names={s: "(" + sp.latex(v) + ")" for s, v in values.items()},
    )
    html += line(expression + "=" + substituted)
    html += line(substituted + "=" + sp.latex(calculation.exact))
    return html
