"""Exact angles, table values and small-multiple reduction relations."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .power_arithmetic import ScalarParser, balanced, clean

S, C = sp.symbols("S C", positive=True)
PI = sp.Symbol("p", real=True)


def parse_angle(text):
    text = clean(text)
    degrees = False
    for _ in range(20):
        if text.endswith((r"^{\circ}", r"^\circ")):
            if degrees:
                raise UnsupportedCondition("duplicate angle unit")
            degrees = True
            text = text.removesuffix(r"^{\circ}").removesuffix(r"^\circ")
        elif text.startswith("("):
            inner, end = balanced(text, 0, "(", ")")
            if end != len(text):
                break
            text = inner
        else:
            break
    value = ScalarParser(text.replace(r"\pi", "p"), {"p"}).parse()
    q = value / 180 if degrees else sp.cancel(value / PI)
    if q.is_Rational is not True or abs(q) > 10000 or q.q > 10000:
        raise UnsupportedCondition(
            "a bounded exact degree or rational-pi angle is required"
        )
    return q, degrees


def angle_text(q, degrees):
    if degrees:
        return sp.latex(q * 180) + r"^{\circ}"
    return sp.latex(q * sp.pi)


def signs(function, q):
    reduced = q % 2
    sine = 0 if reduced in (0, 1) else 1 if reduced < 1 else -1
    cosine = (
        0
        if reduced in (sp.Rational(1, 2), sp.Rational(3, 2))
        else 1
        if reduced < sp.Rational(1, 2) or reduced > sp.Rational(3, 2)
        else -1
    )
    if function == "sin":
        return sine
    if function == "cos":
        return cosine
    if function == "tg":
        if not cosine:
            raise UnsupportedCondition("the tangent is undefined at this angle")
        return sine * cosine
    if not sine:
        raise UnsupportedCondition("the cotangent is undefined at this angle")
    return sine * cosine


@dataclass(frozen=True)
class TrigAtom:
    function: str
    q: sp.Rational
    degrees: bool
    text: str

    def actual(self):
        return {"sin": sp.sin, "cos": sp.cos, "tg": sp.tan, "ctg": sp.cot}[
            self.function
        ](self.q * sp.pi)


def relation(q, base):
    for k in [0, 1, -1, 2, -2, 3, -3, 4, -4]:
        h = 2 * (q - k * base)
        if h.is_Integer:
            return k, int(h)
    return None


def choose_base(atoms):
    candidates = []
    for atom in atoms:
        q = atom.q % 1
        q = min(q, 1 - q)
        if q and q != sp.Rational(1, 2) and q not in candidates:
            candidates.append(q)
    if not candidates and atoms:
        candidates = [sp.Rational(1, 6)]
    valid = []
    for base in candidates:
        relations = [relation(a.q, base) for a in atoms]
        if all(
            rel or a.q.q in [1, 2, 3, 4, 6]
            for a, rel in zip(atoms, relations, strict=True)
        ):
            multiples = [abs(rel[0]) for rel in relations if rel]
            valid.append((max(multiples, default=0), sum(multiples), base))
    if valid:
        return min(valid)[2]
    raise UnsupportedCondition(
        "the reviewed trigonometric angles have no common small-multiple relation"
    )


def polynomial(atom, base):
    rel = relation(atom.q, base)
    if rel is None:
        if atom.q.q not in [1, 2, 3, 4, 6]:
            raise UnsupportedCondition("unsupported unrelated trigonometric angle")
        return atom.actual()
    k, h = rel
    sine, cosine = sp.Integer(0), sp.Integer(1)
    for _ in range(abs(k)):
        sine, cosine = (
            sp.expand(sine * C + cosine * S),
            sp.expand(cosine * C - sine * S),
        )
    if k < 0:
        sine = -sine
    a, b = [sp.Integer(v) for v in [(0, 1, 0, -1)[h % 4], (1, 0, -1, 0)[h % 4]]]
    sn = sp.expand(a * cosine + b * sine)
    cs = sp.expand(b * cosine - a * sine)
    return {
        "sin": lambda: sn,
        "cos": lambda: cs,
        "tg": lambda: sn / cs,
        "ctg": lambda: cs / sn,
    }[atom.function]()


def reduce_polynomial(expression):
    numerator, denominator = sp.fraction(sp.cancel(expression))

    def remainder(poly):
        return sp.rem(poly, C * C + S * S - 1, C)

    denominator = remainder(denominator)
    if denominator == 0:
        raise UnsupportedCondition("the original trigonometric denominator vanishes")
    return sp.cancel(remainder(numerator) / denominator)


def latex(expression, base, degrees):
    theta = angle_text(base, degrees)
    return sp.latex(
        expression,
        symbol_names={S: r"(\sin(" + theta + "))", C: r"(\cos(" + theta + "))"},
    )
