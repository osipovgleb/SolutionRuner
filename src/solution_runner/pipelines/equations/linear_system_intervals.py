"""Solve two affine inequalities with exact rational endpoints and explicit steps."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import re


@dataclass(frozen=True)
class Interval:
    """Represent one connected solution set; None endpoints denote infinities."""

    lower: Fraction | None = None
    upper: Fraction | None = None
    lower_closed: bool = False
    upper_closed: bool = False
    empty: bool = False

    def key(self) -> tuple[str | None, str | None, bool, bool, bool]:
        """Return a JSON-compatible exact identity for reviewed options."""
        return (str(self.lower) if self.lower is not None else None,
                str(self.upper) if self.upper is not None else None,
                self.lower_closed, self.upper_closed, self.empty)


@dataclass(frozen=True)
class Inequality:
    """Retain the source row and exact moved coefficient, constant and bound."""

    source: str
    coefficient: Fraction
    rhs: Fraction
    relation: str
    bound_relation: str
    bound: Fraction


def number(value: Fraction) -> str:
    """Format terminating decimals like the source, otherwise use an exact fraction."""
    if value.denominator == 1:
        return str(value.numerator)
    denominator = value.denominator
    while denominator % 2 == 0:
        denominator //= 2
    while denominator % 5 == 0:
        denominator //= 5
    if denominator == 1:
        from decimal import Decimal
        return format(Decimal(value.numerator) / Decimal(value.denominator), 'f').replace('.', '{,}')
    sign = '-' if value < 0 else ''
    return sign + rf'\frac{{{abs(value.numerator)}}}{{{value.denominator}}}'


def _affine(raw: str) -> tuple[Fraction, Fraction]:
    """Parse only a sum of rational decimal constants and linear x terms."""
    tokens = re.findall(r'[+-]?(?:\d+(?:\.\d+)?x?|x)', raw)
    if not raw or ''.join(tokens) != raw:
        raise ValueError('unsupported affine expression')
    coefficient = Fraction(0)
    constant = Fraction(0)
    for token in tokens:
        if token.endswith('x'):
            scalar = token[:-1]
            coefficient += Fraction(scalar + '1' if scalar in ('', '+', '-') else scalar)
        else:
            constant += Fraction(token)
    return coefficient, constant


def parse_system(latex: str) -> tuple[Inequality, ...]:
    """Parse exactly two supported rows, preserving strict and closed relations."""
    if not latex.startswith(r'\begin{cases}') or not latex.endswith(r'\end{cases}'):
        raise ValueError('cases system is required')
    rows = latex[len(r'\begin{cases}'):-len(r'\end{cases}')].split(r'\\')
    if len(rows) != 2:
        raise ValueError('exactly two inequality rows are required')
    result = []
    for original in rows:
        raw = original.replace('{,}', '.').replace(' ', '').replace('−', '-')
        for source, target in [(r'\leqslant', '<='), (r'\geqslant', '>='),
                               (r'\leq', '<='), (r'\geq', '>='),
                               (r'\le', '<='), (r'\ge', '>='), (r'\lt', '<'), (r'\gt', '>')]:
            raw = raw.replace(source, target)
        raw = raw.rstrip(',.')
        match = re.fullmatch(r'(.+?)(<=|>=|<|>)(.+)', raw)
        if not match:
            raise ValueError('one relation per row is required')
        left, relation, right = match.groups()
        a, b = _affine(left)
        c, d = _affine(right)
        coefficient, rhs = a - c, d - b
        if not coefficient:
            raise ValueError('constant-only inequality needs separate review')
        flipped = {'<': '>', '>': '<', '<=': '>=', '>=': '<='}
        result.append(Inequality(original.rstrip(',.'), coefficient, rhs, relation,
                                 flipped[relation] if coefficient < 0 else relation, rhs / coefficient))
    return tuple(result)


def solve(rows: tuple[Inequality, ...]) -> Interval:
    """Intersect exact half-lines, including singleton and empty intersections."""
    lower = upper = None
    lc = uc = False
    for row in rows:
        closed = row.bound_relation.endswith('=')
        if row.bound_relation.startswith('>'):
            if lower is None or row.bound > lower:
                lower, lc = row.bound, closed
            elif row.bound == lower:
                lc = lc and closed
        else:
            if upper is None or row.bound < upper:
                upper, uc = row.bound, closed
            elif row.bound == upper:
                uc = uc and closed
    empty = lower is not None and upper is not None and (lower > upper or (lower == upper and not (lc and uc)))
    return Interval(None, None, False, False, True) if empty else Interval(lower, upper, lc, uc)


def interval_latex(interval: Interval) -> str:
    """Format a verified set using the source's interval convention."""
    if interval.empty:
        return r'\varnothing'
    lower = number(interval.lower) if interval.lower is not None else r'-\infty'
    upper = number(interval.upper) if interval.upper is not None else r'+\infty'
    return ('[' if interval.lower_closed else '(') + lower + ';' + upper + (']' if interval.upper_closed else ')')


def relation_latex(relation: str) -> str:
    """Translate an exact comparison into a LaTeX command where needed."""
    return {'<=': r'\le ', '>=': r'\ge ', '<': r'\lt ', '>': r'\gt '}[relation]


def solution_html(latex: str, rows: tuple[Inequality, ...], result: Interval, answer: str) -> str:
    """Keep both inequalities together in the parent's compact equivalence chain."""
    from html import escape
    def system(values: list[str]) -> str:
        """Enclose simultaneous rows in one cases expression."""
        return r'\begin{cases}' + r'\\'.join(values) + r'\end{cases}'
    moved = []
    bounds = []
    for row in rows:
        coefficient = '' if row.coefficient == 1 else '-' if row.coefficient == -1 else number(row.coefficient)
        moved.append(coefficient + 'x' + relation_latex(row.relation) + number(row.rhs))
        bounds.append('x' + relation_latex(row.bound_relation) + number(row.bound))
    stages = [latex]
    for stage in (system(moved), system(bounds)):
        if stage != stages[-1]:
            stages.append(stage)
    if not result.empty:
        if result.lower is not None and result.upper is not None:
            final = ('x=' + number(result.lower) if result.lower == result.upper else
                     number(result.lower) + relation_latex('<=' if result.lower_closed else '<')
                     + 'x' + relation_latex('<=' if result.upper_closed else '<') + number(result.upper))
        elif result.lower is not None:
            final = 'x' + relation_latex('>=' if result.lower_closed else '>') + number(result.lower)
        else:
            final = 'x' + relation_latex('<=' if result.upper_closed else '<') + number(result.upper)
        stages.append(final)
    chain = r'\iff '.join(stages)
    formula = '<center><p><span data-inline-latex="' + escape(chain, quote=True) + '"></span>.</p></center>'
    if result.empty:
        conclusion = f'Система не имеет решений. Этому соответствует вариант {answer}.'
    else:
        kind = 'точка' if result.lower == result.upper else ('отрезок' if result.lower_closed and result.upper_closed else 'полуинтервал' if result.lower_closed or result.upper_closed else 'интервал') if result.lower is not None and result.upper is not None else 'луч'
        conclusion = f'Решению системы соответствует вариант {answer}.' if kind == 'точка' else f'Решением системы является {kind}, изображённый под номером {answer}.'
    return '<p>Решим систему:</p>' + formula + '<p>' + conclusion + '</p>'
