"""Render the finite full solution set before the requested interval selection."""

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline
from .exam_scalar import compare
from .exam_trigonometric_bounded_log import L
from .exam_trigonometric_compile import S


def full_set(a):
    from .exam_trigonometric_proof import pi

    return r"\{" + r";\ ".join(pi(q) for q in a.finite_roots) + r"\}"


def proof(a):

    data = a.bounded_log
    name = r"\sin x" if data.variable == S else r"\cos x"
    logarithm = r"\log_{" + sp.latex(data.base) + r"}\left(" + name + r"\right)"
    lo, hi = data.bounds
    html = line(a.original)
    html += "<p>Сначала сохраним область определения логарифма и исходного корня:</p>"
    html += line("0<" + name + r"\le1")
    html += line(
        sp.latex(data.radicand)
        + r"\ge0\quad\Longleftrightarrow\quad "
        + sp.latex(lo)
        + r"\le x\le "
        + sp.latex(hi)
    )
    html += "<p>Только в этой области квадрат корня равен подкоренному выражению. Сократим одинаковые члены с x² и получим уравнение относительно логарифма:</p>"
    html += line(
        r"\left(\sqrt{"
        + sp.latex(data.radicand)
        + r"}\right)^2="
        + sp.latex(data.radicand)
    )
    symbols = {L: r"\left(" + logarithm + r"\right)"}
    html += line(sp.latex(data.polynomial, symbol_names=symbols) + "=0")
    html += line(sp.latex(sp.factor(data.polynomial), symbol_names=symbols) + "=0")
    for level, target in zip(data.levels, data.targets):
        html += line(
            logarithm
            + "="
            + sp.latex(level)
            + r"\quad\Longleftrightarrow\quad "
            + name
            + "="
            + sp.latex(target)
        )
        if compare(target, sp.S.Zero) <= 0 or compare(target, sp.S.One) > 0:
            html += "<p>Это значение не лежит в допустимом положительном диапазоне тригонометрической функции и исключается.</p>"
    html += "<p>Для оставшихся тригонометрических серий найдём все целые индексы в исходной области определения. Используем отдельный параметр для каждой серии:</p>"
    html += domain_series(a)
    html += "<p>Поэтому полное множество корней исходного уравнения конечно:</p>"
    html += line(full_set(a))
    return (
        "<p>Решим логарифмическое уравнение, сохраняя исходные ограничения:</p>",
        html,
    )


def domain_series(a):
    from .exam_trigonometric import select
    from .exam_trigonometric_proof import series_lines

    lo, hi = a.bounded_log.bounds
    html = ""
    for i, (q, p) in enumerate(a.series):
        name = "klmn"[i]
        _, rows = select(((q, p),), (lo / sp.pi, hi / sp.pi, True, True))
        _, _, start, end, _ = rows[0]
        family = series_lines(((q, p),))[0].replace("k", name)
        html += line(family + r",\quad " + name + r"\in\mathbb Z")
        html += line(
            sp.latex(lo) + r"\le " + family.removeprefix("x=") + r"\le " + sp.latex(hi)
        )
        html += line(
            sp.latex(sp.simplify((lo / sp.pi - q) / p))
            + r"\le "
            + name
            + r"\le "
            + sp.latex(sp.simplify((hi / sp.pi - q) / p))
        )
        if start > end:
            html += "<p>Подходящих целых индексов нет.</p>"
        else:
            html += line(
                name
                + r"\in\{"
                + ";".join(str(k) for k in range(start, end + 1))
                + r"\}"
            )
    return html


def selection(a):
    from .exam_trigonometric_proof import pi

    lo, hi, lc, uc = a.bounds
    html = (
        "<p>Из полного конечного множества корней выберем принадлежащие промежутку "
        + inline(a.interval)
        + ":</p>"
    )
    for root in a.finite_roots:
        if root in a.selected:
            html += line(
                pi(lo)
                + (r"\le " if lc else "<")
                + pi(root)
                + (r"\le " if uc else "<")
                + pi(hi)
            )
        elif compare(root, lo) < 0:
            html += line(pi(root) + "<" + pi(lo))
        elif compare(root, hi) > 0:
            html += line(pi(root) + ">" + pi(hi))
        else:
            html += line(pi(root) + r"\notin " + a.interval)
    if not a.selected:
        html += "<p>Ни один корень не принадлежит заданному промежутку.</p>"
    return html
