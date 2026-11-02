"""Certify reciprocal logs with a finite physical x domain before filtering roots."""

from dataclasses import dataclass, replace

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_exponential import X
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_global_indices import positive_intervals, windows
from .exam_trigonometric_log_base_change import reciprocal
from .exam_trigonometric_radical_equation import same, trig_polynomial


@dataclass(frozen=True)
class FiniteBaseLog:
    phase: sp.Rational
    intervals: tuple
    families: tuple
    poles: tuple
    factors: tuple

    def series(self):
        from .exam_trigonometric import select
        from .exam_trigonometric_selection import periodic

        return periodic(select(self.families, (0, 2, True, False))[0])

    def rows(self):
        rows = []
        count = 0
        for q, p in self.series():
            for start, end in windows(self.intervals, q, p):
                if start is None or end is None or end - start > 100:
                    raise UnsupportedCondition(
                        "finite logarithm index windows must be bounded"
                    )
                count += end - start + 1
                if count > 200:
                    raise UnsupportedCondition("too many finite logarithm candidates")
                rows.append(
                    (q, p, start, end, tuple(q + k * p for k in range(start, end + 1)))
                )
        return tuple(rows)


def data_of(value):
    equality = value.log_product.equality if value.log_product is not None else None
    return (
        equality.identity.finite_base
        if equality is not None and equality.identity is not None
        else None
    )


def argument_phase(argument, fixed):
    denominator = trig_polynomial("sin", sp.Integer(3))
    numerator = sp.cancel(argument * denominator)
    if (
        not numerator.is_polynomial(S, C)
        or sp.Poly(numerator, S, C).total_degree() != 1
    ):
        raise UnsupportedCondition(
            "a linear sine/cosine numerator over original sine triple-angle is required"
        )
    p, q = numerator.coeff(S), numerator.coeff(C)
    if numerator != p * S + q * C or sp.simplify(p * p + q * q - fixed * fixed) != 0:
        raise UnsupportedCondition(
            "the same-base target must equal the numerator amplitude"
        )
    phase = next(
        (
            sp.Rational(n, 6)
            for n in range(-5, 7)
            if sp.simplify(p / fixed - sp.cos(n * sp.pi / 6)) == 0
            and sp.simplify(q / fixed - sp.sin(n * sp.pi / 6)) == 0
        ),
        None,
    )
    if phase is None:
        raise UnsupportedCondition("a reviewed sixth-pi amplitude phase is required")
    first = trig_polynomial("sin", sp.S.One, -phase / 2)
    second = trig_polynomial("cos", sp.Integer(2), phase / 2)
    second = sp.expand(second + second.subs({S: 0, C: 0}) * (S * S + C * C - 1))
    raw = first * second
    if not same(-2 * raw, numerator / fixed - denominator):
        raise UnsupportedCondition("the complete sum-to-product identity is not exact")
    return phase, raw, denominator, (first, second)


def certify(value, atoms, poles, angles):
    variable, fixed, level, mapped = reciprocal(value, atoms, poles)
    base = variable.base
    if (
        level != 0
        or base.free_symbols != {X}
        or not base.is_polynomial(X)
        or sp.degree(base, X) != 2
        or sp.Poly(base, X).LC() >= 0
        or any(
            c.is_Rational is not True or abs(c) > 1000 or c.q > 100
            for c in sp.Poly(base, X).all_coeffs()
        )
        or any(
            a.function not in ("sin", "cos")
            or a.coefficient not in (1, 3)
            or a.shift
            or a.variable != r"\alpha"
            for a in angles.values()
        )
    ):
        raise UnsupportedCondition(
            "a bounded concave quadratic physical base and original first/triple angles are required"
        )
    phase, raw, denominator, factors = argument_phase(variable.argument, fixed.base)
    other_poles = tuple(p for p in poles if p != fixed.symbol)
    if not other_poles or any(
        sp.cancel(p / denominator).free_symbols or p == 0 for p in other_poles
    ):
        raise UnsupportedCondition(
            "only the original triple-angle and reciprocal-log poles are reviewed"
        )
    intervals = positive_intervals(base)
    if len(intervals) != 1 or any(not v.is_finite for v in intervals[0]):
        raise UnsupportedCondition(
            "one finite open interval for the original log base is required"
        )
    data = FiniteBaseLog(
        phase,
        intervals,
        ((phase / 2, sp.S.One), ((1 - phase) / 4, sp.Rational(1, 2))),
        mapped,
        factors,
    )
    data.rows()
    return raw, (variable, fixed), data


def identity(value, atoms, logs, poles, angles):
    from .exam_trigonometric_log_equality import original_text
    from .exam_trigonometric_log_identity import LogIdentity

    raw, atoms, details = certify(value, atoms, poles, angles)
    source = {e[0]: (original_text(e[3]), original_text(e[4])) for e in logs}
    data = LogIdentity(
        "finite_base",
        atoms,
        tuple(source[a.symbol] for a in atoms),
        sp.S.Zero,
        atoms[1].base,
        raw,
        None,
        "",
        "none",
        finite_base=details,
    )
    return raw, data


def branches(compiled, preferred, allow_inverse):
    from .exam_trigonometric_radical_product import factor_branches

    return tuple(
        b
        for factor in data_of(compiled).factors
        for b in factor_branches(factor, preferred, allow_inverse)
    )


def prepare(a):
    data = data_of(a)
    if data is None:
        return a
    from .exam_trigonometric_affine_selection import isolated
    from .exam_trigonometric_log_product import failed

    candidates = {q for _, _, _, _, row in data.rows() for q in row}
    full = tuple(q for q in sorted(candidates) if failed(a, q) is None)
    selected = isolated(tuple(q * sp.pi for q in full), a.bounds)
    return replace(a, finite_roots=full, selected=selected)
