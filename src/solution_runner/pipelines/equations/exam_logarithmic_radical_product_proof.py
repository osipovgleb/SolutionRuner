"""Check candidates first; retain the original full-domain note after selection."""

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline
from .exam_exponential import X
from .exam_exponential_proof import n, root_set
from .exam_logarithmic_branches import allowed
from .exam_logarithmic_proof import atom_text
from .exam_rational_proof import roots_line


def candidates(a):
    data = a.radical_product
    html = ""
    for i, branch in enumerate(a.branches):
        if i == 0:
            html += "<p>Первый множитель обращается в нуль, если:</p>"
            html += line(r"\sqrt{" + sp.latex(data.radicand) + "}=" + n(data.level))
            html += line(sp.latex(data.radicand) + "=" + n(data.level**2))
        else:
            html += "<p>Второй множитель обращается в нуль, если:</p>"
            html += line(atom_text(a.atoms[0]) + "=0")
            html += line(sp.latex(a.atoms[0].argument) + "=1")
        html += line(sp.latex(branch.equation) + "=0")
        html += line(sp.latex(sp.factor(branch.equation)) + "=0")
        html += roots_line(branch.candidates)
        for root in branch.candidates:
            p = a.atoms[0].argument if i == 0 else data.radicand
            value = sp.simplify(p.subs(X, root))
            html += "<p>При " + inline("x=" + n(root))
            html += (
                " проверим аргумент логарифма:"
                if i == 0
                else " проверим подкоренное выражение:"
            ) + "</p>"
            html += line(
                r"\left.(" + sp.latex(p) + r")\right|_{x=" + n(root) + "}=" + n(value)
            )
            html += (
                "<p>Все исходные выражения определены; число является корнем.</p>"
                if allowed(root, a.constraints)
                else "<p>Исходная область определения нарушена; это посторонний корень.</p>"
            )
    return html


def note(a):
    data = a.radical_product
    html = "<p><b>Примечание.</b> Чтобы не проверять корни подстановкой, можно сначала найти область определения уравнения:</p>"
    html += line(
        r"\begin{cases}"
        + sp.latex(data.radicand)
        + r"\ge0\\"
        + sp.latex(a.atoms[0].argument)
        + r">0\end{cases}"
    )
    html += line(r"x\in" + sp.latex(data.domain))
    html += "<p>На этой области исходное уравнение равносильно совокупности уравнений для нулей множителей:</p>"
    html += line(
        r"\left[\begin{aligned}"
        + sp.latex(data.radicand)
        + "="
        + n(data.level**2)
        + r"\\"
        + sp.latex(a.atoms[0].argument)
        + r"=1\end{aligned}\right."
    )
    html += roots_line(
        tuple(dict.fromkeys(r for b in a.branches for r in b.candidates))
    )
    html += "<p>Оставляем только числа, лежащие в найденной области определения:</p>"
    return html + roots_line(a.selection.roots)


def render(a):
    from .exam_log_selection import selection

    rendered = {r: n(r) for r in a.selection.roots}
    second = "<p>Сравним границы по монотонности логарифма и показательной функции. Для положительного основания больше единицы порядок показателей сохраняется.</p>"
    second += selection(a.selection, rendered)
    second += note(a)
    html = (
        '<ol data-layout="source-subparts" type="a"><li data-list-marker="а)">'
        + candidates(a)
        + '</li><li data-list-marker="б)">'
        + second
        + "</li></ol>"
    )
    full, chosen = (
        root_set(v, rendered) for v in (a.selection.roots, a.selection.selected)
    )
    return (
        "а) " + full + "; б) " + chosen,
        "<p>а) " + inline(full) + "; б) " + inline(chosen) + ".</p>",
        html,
    )
