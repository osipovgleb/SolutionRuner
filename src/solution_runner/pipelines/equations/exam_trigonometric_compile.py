"""Compile reviewed single-angle trigonometric equations without losing poles."""

from functools import lru_cache

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .power_arithmetic import clean
from .trig_angles import C as NUMERIC_C
from .trig_angles import S as NUMERIC_S
from .trig_symbolic_parser import SymbolicTrigonometricParser, compile_atoms

S, C, T, U = sp.symbols("s c tangent cotangent", real=True)


def compile_equation(formula):
    text = clean(formula).removesuffix(".")
    if text.count("=") != 1:
        raise UnsupportedCondition("one complete trigonometric equation is required")
    atoms = {}
    denominators = []
    values = []
    for side in text.split("="):
        parser = SymbolicTrigonometricParser(
            side.replace("x", r"\alpha"), atoms, denominators
        )
        values.append(parser.parse().value)
    if any(a.function == "ctg" for a in atoms.values()):
        from .exam_trigonometric_ratios import compile_cotangent

        return compile_cotangent(values, atoms, denominators)
    if atoms and all(a.function == "tg" for a in atoms.values()):
        if any(
            abs(a.coefficient) != 1 or not a.shift.is_Integer for a in atoms.values()
        ) or any(d.free_symbols for d in denominators):
            raise UnsupportedCondition(
                "reviewed tangent polynomials require one angle and no added denominators"
            )
        compiled = {symbol: a.coefficient * T for symbol, a in atoms.items()}
        raw = sp.expand((values[0] - values[1]).xreplace(compiled))
        if not raw.is_polynomial(T) or raw == 0 or sp.degree(raw, T) > 2:
            raise UnsupportedCondition(
                "a nonzero tangent polynomial of degree at most two is required"
            )
        return raw, ()
    base, _, compiled, poles = compile_atoms(parser)
    if (
        base != 1
        or poles
        or any(a.function not in ("sin", "cos") for a in atoms.values())
    ):
        raise UnsupportedCondition(
            "reviewed sine and cosine equations have one base angle and no original denominators"
        )
    raw = sp.expand(
        (values[0] - values[1])
        .xreplace(compiled)
        .xreplace({NUMERIC_S: S, NUMERIC_C: C})
    )
    if not raw.is_polynomial(S, C) or sp.Poly(raw, S, C).total_degree() > 4 or raw == 0:
        raise UnsupportedCondition(
            "a nonzero polynomial of sine and cosine of degree at most four is required"
        )
    identities = tuple(
        dict.fromkeys(
            (
                atom.text.replace(r"\alpha", "x"),
                compiled[symbol].xreplace({NUMERIC_S: S, NUMERIC_C: C}),
            )
            for symbol, atom in atoms.items()
        )
    )
    return raw, identities


@lru_cache(maxsize=128)
def table(variable, value):
    f = sp.sin if variable == S else sp.cos
    result = tuple(
        sp.Rational(i, 12)
        for i in range(24)
        if sp.simplify(f(sp.pi * i / 12) - value) == 0
    )
    if not result:
        raise UnsupportedCondition("a complete reviewed exact angle table is required")
    return result
