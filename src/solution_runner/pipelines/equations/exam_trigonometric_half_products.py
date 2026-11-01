"""Reduce paired half-angle sine/cosine powers without admitting odd single factors."""

import sympy as sp

from ..word_problems.common import UnsupportedCondition


def normalize(values, atoms, denominators):
    from .exam_trigonometric_radical_equation import trig_polynomial

    groups = {}
    for symbol, atom in atoms.items():
        if atom.function in ("sin", "cos") and atom.coefficient.q == 2:
            groups.setdefault((atom.coefficient, atom.shift), {})[atom.function] = (
                symbol,
                atom,
            )
    if not groups:
        return values, atoms, denominators, ()
    retained = dict(atoms)
    identities = []
    for (coefficient, shift), group in groups.items():
        sine = group.get("sin", (sp.Dummy("half_sine"), None))[0]
        cosine = group.get("cos", (sp.Dummy("half_cosine"), None))[0]
        double_sine = trig_polynomial("sin", 2 * coefficient, 2 * shift)
        double_cosine = trig_polynomial("cos", 2 * coefficient, 2 * shift)
        values = [
            reduce_pair(v, sine, cosine, double_sine, double_cosine) for v in values
        ]
        denominators = [
            reduce_pair(v, sine, cosine, double_sine, double_cosine)
            for v in denominators
        ]
        for symbol, _ in group.values():
            retained.pop(symbol)
        if len(group) == 2:
            text = "".join(
                atom.text.replace(r"\alpha", "x")
                for _, atom in (group["sin"], group["cos"])
            )
            identities.append((text, double_sine / 2))
        else:
            _, atom = next(iter(group.values()))
            square = (
                (1 - double_cosine) / 2
                if atom.function == "sin"
                else (1 + double_cosine) / 2
            )
            identities.append((atom.text.replace(r"\alpha", "x") + "^2", square))
    return values, retained, denominators, tuple(identities)


def reduce_pair(expression, sine, cosine, double_sine, double_cosine):
    def polynomial(value):
        if not value.is_polynomial(sine, cosine):
            raise UnsupportedCondition("the paired half angles must occur polynomially")
        result = 0
        for (a, b), coefficient in sp.Poly(value, sine, cosine).terms():
            if a % 2 != b % 2 or a + b > 12:
                raise UnsupportedCondition(
                    "an unpaired odd half-angle factor is not removed"
                )
            result += (
                coefficient
                * ((1 - double_cosine) / 2) ** (a // 2)
                * ((1 + double_cosine) / 2) ** (b // 2)
                * (double_sine / 2 if a % 2 else 1)
            )
        return sp.expand(result)

    numerator, denominator = sp.fraction(sp.cancel(expression))
    return sp.cancel(polynomial(numerator) / polynomial(denominator))
