"""Keep a parent's affine families with exact forbidden residue classes of the index."""

from dataclasses import dataclass

import sympy as sp

from ..word_problems.common import UnsupportedCondition


@dataclass(frozen=True)
class Family:
    offset: sp.Rational
    period: sp.Rational
    parameter: str
    modulus: int
    excluded: tuple

    def accepts(self, index):
        return index % self.modulus not in self.excluded


def prepare(a, parent_html):
    from .exam_trigonometric_parameters import names
    from .exam_trigonometric_selection import branch_series, equivalent_series, periodic

    result = []
    for b in a.branches:
        nominal = branch_series(b, False)
        if len(nominal) != 1:
            raise UnsupportedCondition(
                "one affine family per quotient factor is required"
            )
        q, p = nominal[0]
        retained = periodic(b.residues)
        if not retained:
            continue
        modulus = sp.cancel(retained[0][1] / p)
        if modulus.is_Integer is not True or not 1 <= modulus <= 24:
            raise UnsupportedCondition("a bounded exact index modulus is required")
        excluded = tuple(
            k
            for k in range(int(modulus))
            if all(
                sp.cancel((q + k * p - r) / step).is_Integer is not True
                for r, step in retained
            )
        )
        physical = ((q / a.scale, p / a.scale),)
        letters = names(parent_html, physical)
        if not letters:
            raise UnsupportedCondition(
                "the parent's quotient-family parameter must match its computed series"
            )
        result.append(Family(*physical[0], letters[0], int(modulus), excluded))
    expanded = tuple(
        (f.offset + k * f.period, f.modulus * f.period)
        for f in result
        for k in range(f.modulus)
        if f.accepts(k)
    )
    if not equivalent_series(expanded, a.series):
        raise UnsupportedCondition(
            "restricted families must equal the complete filtered root set"
        )
    return tuple(result)


def formulas(a):
    from .exam_trigonometric_proof import series_lines

    result = []
    for f in a.restricted_families:
        text = series_lines(((f.offset, f.period),))[0].replace("k", f.parameter)
        text += r",\quad " + f.parameter + r"\in\mathbb Z"
        if f.excluded:
            p = sp.Symbol("p", integer=True)
            text += (
                r"\setminus\{"
                + ";".join(sp.latex(f.modulus * p + k) for k in f.excluded)
                + r"\mid p\in\mathbb Z\}"
            )
        result.append(text)
    return tuple(result)


def selection_rows(a):
    from .exam_trigonometric import select

    if not a.restricted_families:
        return tuple(
            (
                *row,
                a.family_parameters[i] if a.family_parameters else "k",
                tuple(range(row[2], row[3] + 1)),
            )
            for i, row in enumerate(a.selections)
        )
    rows = []
    for f in a.restricted_families:
        _, trace = select(((f.offset, f.period),), a.bounds)
        q, p, start, end, _ = trace[0]
        indices = tuple(k for k in range(start, end + 1) if f.accepts(k))
        rows.append(
            (q, p, start, end, tuple(q + p * k for k in indices), f.parameter, indices)
        )
    return tuple(rows)
