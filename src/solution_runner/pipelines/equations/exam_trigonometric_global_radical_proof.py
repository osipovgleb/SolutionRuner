"""Show both radical cases and all index restrictions before selecting roots."""

from collections import defaultdict
from dataclasses import replace

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline
from .exam_scalar import compare
from .exam_trigonometric_global_indices import (
    displayed,
    exact_floor,
    integer_set,
    selected,
    windows,
)


def family_formula(family, *, nominal=False):
    from .exam_trigonometric_proof import series_lines

    q, p = (family.offset, family.period) if nominal else displayed(family)
    return series_lines(((q, p),))[0].replace("k", family.parameter)


def all_roots(a):
    data = a.global_radical
    parts = []
    if data.points:
        parts.append(r"\{" + r";\ ".join(sp.latex(p) for p in data.points) + r"\}")
    groups = defaultdict(list)
    for family in data.families:
        if family.windows:
            groups[integer_set(family, reindexed=True)].append(family)
    for domain, families in groups.items():
        letters = ",".join(dict.fromkeys(f.parameter for f in families))
        parts.append(
            r"\{"
            + r";\ ".join(family_formula(f).removeprefix("x=") for f in families)
            + r"\mid "
            + letters
            + r"\in "
            + domain
            + r"\}"
        )
    return r"\cup".join(parts) or r"\varnothing"


def interval_set(intervals):
    return (
        r"\cup".join(
            "(" + sp.latex(lo) + ";" + sp.latex(hi) + ")" for lo, hi in intervals
        )
        or r"\varnothing"
    )


def factor_steps(a):
    from .exam_trigonometric_proof import formula

    html = line(formula(a.global_radical.factor) + "=0")
    for branch in a.branches:
        for value in branch.values:
            if sp.expand(a.global_radical.factor - branch.variable + value) != 0:
                html += line(formula(branch.variable) + "=" + sp.latex(value))
    html += "<p>Тригонометрическое уравнение даёт серии:</p>"
    for family in a.global_radical.families:
        html += line(
            family_formula(family, nominal=True)
            + r",\quad "
            + family.parameter
            + r"\in\mathbb Z"
        )
    return html


def proof(a):
    from .exam_trigonometric_proof import formula

    data = a.global_radical
    html = line(a.original)
    if data.denominator:
        html += "<p>Найдём корни числителя:</p>" + factor_steps(a)
        html += "<p>Корень в знаменателе должен быть определён и отличен от нуля. Сохраняем также полюсы исходной тригонометрической функции:</p>"
        html += line(sp.latex(data.polynomial) + "(" + formula(data.periodic) + r")>0")
        for pole in a.poles:
            html += line(formula(pole) + r"\ne0")
    else:
        p = sp.latex(data.polynomial)
        html += "<p>Произведение с арифметическим корнем равно нулю в двух случаях:</p>"
        html += line(
            r"\left[\begin{aligned}&"
            + p
            + r"=0,\\&\begin{cases}"
            + p
            + r">0,\\"
            + formula(data.factor)
            + r"=0.\end{cases}\end{aligned}\right."
        )
        html += "<p>Случай 1. Подкоренное выражение равно нулю:</p>" + line(p + "=0")
        html += line(sp.latex(sp.factor(data.polynomial)) + "=0")
        html += line(r"x\in\{" + r";\ ".join(sp.latex(v) for v in data.points) + r"\}")
        html += "<p>Случай 2. Подкоренное выражение положительно, а тригонометрический множитель равен нулю:</p>"
        html += factor_steps(a)
    html += "<p>Ограничим полные серии исходной областью определения. Для точных границ целых индексов используем оценки:</p>"
    html += line(r"3{,}14<\pi<\frac{22}{7}")
    for family in data.families:
        html += domain_steps(data, family)
    html += "<p>Полное множество корней исходного уравнения:</p>" + line(all_roots(a))
    return "<p>Сохраним исходную область определения при решении уравнения:</p>", html


def domain_steps(data, family):
    from .exam_trigonometric_proof import formula

    html = line(family_formula(family, nominal=True))
    if data.denominator:
        html += line(
            r"\frac{x}{\pi}="
            + sp.latex(
                family.offset
                + family.period * sp.Symbol(family.parameter, integer=True)
            )
        )
        html += line(formula(data.periodic) + "=" + sp.latex(family.coefficient))
        html += line(sp.latex(data.polynomial * family.coefficient) + ">0")
    else:
        html += line(sp.latex(data.polynomial) + ">0")
    html += line(r"x\in " + interval_set(family.intervals))
    for lo, hi in family.intervals:
        left = (
            -sp.oo
            if lo == -sp.oo
            else sp.simplify((lo / sp.pi - family.offset) / family.period)
        )
        right = (
            sp.oo
            if hi == sp.oo
            else sp.simplify((hi / sp.pi - family.offset) / family.period)
        )
        html += line(sp.latex(left) + "<" + family.parameter + "<" + sp.latex(right))
        for value in (left, right):
            if value in (-sp.oo, sp.oo):
                continue
            n = exact_floor(value)
            html += line(
                str(n)
                + (r"=" if compare(value, sp.Integer(n)) == 0 else "<")
                + sp.latex(value)
                + "<"
                + str(n + 1)
            )
        allowed = windows(((lo, hi),), family.offset, family.period)
        if allowed:
            html += line(
                family.parameter
                + r"\in "
                + integer_set(replace(family, windows=allowed))
            )
        else:
            html += "<p>В этой части области определения целых индексов нет.</p>"
    if len(family.intervals) != 1:
        html += line(family.parameter + r"\in " + integer_set(family))
    if family.windows == ((None, 0),):
        html += "<p>В этой серии заменим целый неположительный параметр противоположным. Он пробегает все неотрицательные целые числа:</p>"
        html += line(
            family_formula(family)
            + r",\quad "
            + family.parameter
            + r"\in\mathbb N\cup\{0\}"
        )
    return html


def selection(a):
    data = a.global_radical
    html = (
        "<p>Отберём корни, принадлежащие промежутку "
        + inline(a.interval)
        + ". Сохраняем все ограничения индексов, найденные в пункте а):</p>"
    )
    html += line(r"3{,}14<\pi<\frac{22}{7}")
    finite = "".join(isolated_check(point, a) for point in data.points)
    periodic = "".join(
        quotient_selection(family, a)
        if data.denominator
        else product_selection(family, a)
        for family in data.families
    )
    html += finite + periodic if data.case_order else periodic + finite
    return html


def isolated_check(point, a):
    lo, hi, lc, uc = a.bounds
    if point / sp.pi not in a.selected:
        return line(sp.latex(point) + r"\notin " + a.interval)
    return line(
        sp.latex(lo * sp.pi)
        + (r"\le " if lc else "<")
        + sp.latex(point)
        + (r"\le " if uc else "<")
        + sp.latex(hi * sp.pi)
    )


def product_selection(family, a):
    from .exam_trigonometric import select
    from .exam_trigonometric_proof import pi

    lo, hi, lc, uc = a.bounds
    html = line(
        family_formula(family, nominal=True)
        + r",\quad "
        + family.parameter
        + r"\in "
        + integer_set(family)
    )
    if not family.windows:
        return html + "<p>Эта серия не даёт корней исходного уравнения.</p>"
    values, trace = select(((family.offset, family.period),), a.bounds)
    start, end = trace[0][2:4]
    html += line(
        pi(family.offset + (start - 1) * family.period)
        + ("<" if lc else r"\le ")
        + pi(lo)
        + (r"\le " if lc else "<")
        + pi(family.offset + start * family.period)
    )
    html += line(
        pi(family.offset + end * family.period)
        + (r"\le " if uc else "<")
        + pi(hi)
        + ("<" if uc else r"\le ")
        + pi(family.offset + (end + 1) * family.period)
    )
    indices = tuple(k for k in range(start, end + 1) if family.accepts(k))
    if indices:
        html += line(family.parameter + r"\in\{" + ";".join(map(str, indices)) + r"\}")
        for q in selected(family, a.bounds):
            html += line("x=" + pi(q))
    else:
        html += "<p>После исходных ограничений подходящих целых индексов нет.</p>"
    for q in values:
        if q not in selected(family, a.bounds):
            html += line(
                "x=" + pi(q) + r"\quad\text{не входит в исходную область определения}"
            )
    return html


def quotient_selection(family, a):
    from .exam_trigonometric_proof import pi

    q, p = displayed(family)
    name = family.parameter
    lo, hi, lc, uc = a.bounds
    left, right = family.intervals[0]
    if left != -sp.oo and compare(left / sp.pi, lo) >= 0:
        lo, lc = left / sp.pi, False
    if right != sp.oo and compare(right / sp.pi, hi) <= 0:
        hi, uc = right / sp.pi, False
    html = line(family_formula(family) + r",\quad " + name + r"\in\mathbb N\cup\{0\}")
    html += line(
        pi(lo)
        + (r"\le " if lc else "<")
        + family_formula(family).removeprefix("x=")
        + (r"\le " if uc else "<")
        + pi(hi)
    )
    if p > 0:
        lower, upper = (lo - q) / p, (hi - q) / p
        lower_closed, upper_closed = lc, uc
    else:
        lower, upper = (hi - q) / p, (lo - q) / p
        lower_closed, upper_closed = uc, lc
    html += line(
        sp.latex(sp.simplify(lower))
        + (r"\le " if lower_closed else "<")
        + name
        + (r"\le " if upper_closed else "<")
        + sp.latex(sp.simplify(upper))
    )
    roots = selected(family, a.bounds)
    indices = tuple(int(sp.cancel((root - q) / p)) for root in roots)
    html += line(name + r"\in\{" + ";".join(map(str, indices)) + r"\}")
    for root in roots:
        html += line("x=" + pi(root))
    return html
