"""Keep a parent's translated angle and explicitly undo the substitution."""

import re
from dataclasses import replace

import sympy as sp
from bs4 import BeautifulSoup

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .power_arithmetic import ScalarParser
from .trig_symbolic_parser import A


def parent_method(html):
    soup = BeautifulSoup(html, "html.parser")
    shifts = []
    for node in soup.select("[data-inline-latex]"):
        formula = "".join(node["data-inline-latex"].split())
        if not formula.startswith("t=x"):
            continue
        value = ScalarParser(
            formula[2:].replace("x", "a").replace(r"\pi", "p"), {"a", "p"}
        ).parse()
        shift = sp.cancel((value - A) / sp.Symbol("p", real=True))
        if (
            shift.is_Rational is not True
            or (12 * shift).is_Integer is not True
            or abs(shift) > 2
        ):
            raise UnsupportedCondition(
                "the translated angle must be x plus a reviewed pi shift"
            )
        shifts.append(shift)
    if not shifts:
        return html, sp.S.Zero
    if len(set(shifts)) != 1 or shifts[0] == 0:
        raise UnsupportedCondition("one nonzero angle translation is required")
    for node in soup.select("[data-inline-latex]"):
        formula = node["data-inline-latex"]
        node["data-inline-latex"] = re.sub(
            r"\\(sin|cos)(\s*\d*)t", lambda m: "\\" + m[1] + m[2] + "x", formula
        )
    return str(soup), shifts[0]


def translated_atoms(atoms, shift):
    result = {}
    for symbol, atom in atoms.items():
        new_shift = atom.shift - atom.coefficient * shift
        if (2 * new_shift).is_Integer is not True:
            raise UnsupportedCondition(
                "the translated equation needs reviewed half-pi shifts"
            )
        argument = sp.latex(
            atom.coefficient * sp.Symbol("x", real=True) + new_shift * sp.pi
        )
        result[symbol] = replace(
            atom, shift=new_shift, text="\\" + atom.function + "(" + argument + ")"
        )
    return result


def proof(a):
    from .exam_trigonometric_proof import first, pi, series_lines

    inner = replace(
        a,
        translation=sp.S.Zero,
        series=tuple((q + a.translation, p) for q, p in a.series),
    )
    intro, steps = first(inner)
    soup = BeautifulSoup(intro + steps, "html.parser")
    for node in soup.select("[data-inline-latex]"):
        node["data-inline-latex"] = re.sub(
            r"(?<![A-Za-z])x(?![A-Za-z])", "t", node["data-inline-latex"]
        )
    html = str(soup) + "<p>Сделаем обратную замену:</p>"
    html += line("x=t-(" + pi(a.translation) + ")")
    for text in series_lines(a.series):
        html += line(text + r",\quad k\in\mathbb Z")
    return "<p>Сделаем замену угла:</p>" + line("t=x+(" + pi(a.translation) + ")"), html
