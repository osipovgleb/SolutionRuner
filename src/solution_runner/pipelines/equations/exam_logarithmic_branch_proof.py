"""Show logarithm factor branches, their domains and the parent's final note."""

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline
from .exam_exponential import X
from .exam_exponential_proof import n, root_set
from .exam_logarithmic_algebra import roots
from .exam_logarithmic_branches import allowed
from .exam_logarithmic_proof import atom_text, logarithm
from .exam_rational_proof import roots_line
from .exam_scalar import compare
from .logarithm_arithmetic import log_ratio


def display(expression, a):
    result = sp.latex(expression)
    for atom in a.canonical:
        result = result.replace(str(atom.symbol), "(" + atom_text(atom) + ")")
    return result


def domain(a):
    html = "<p>Сохраним ОДЗ исходного уравнения: каждый аргумент и каждое основание положительны, основания отличны от единицы.</p>"
    if any(atom.denominator for atom in a.atoms):
        html += "<p>Логарифм в знаменателе не должен равняться нулю, поэтому его аргумент отличен от единицы.</p>"
    for p, relation in a.constraints:
        if p.has(X):
            html += line(sp.latex(p) + (">0" if relation == "positive" else r"\ne0"))
    if a.method in ("reciprocal", "same-argument"):
        for p, relation in a.constraints:
            if relation == "nonzero" and p.has(X):
                excluded = roots(p)
                html += (
                    "<p>Условие "
                    + inline(sp.latex(p) + r"\ne0")
                    + " исключает значения:</p>"
                    + roots_line(excluded)
                )
    return html


def conversion(a):
    html = ""
    for atom in dict.fromkeys(a.atoms):
        found = next(
            (
                c
                for c in a.canonical
                if c.argument == atom.argument and c.root == atom.root
            ),
            None,
        )
        if found is not None and atom.base != found.base:
            ratio = log_ratio(atom.base, found.base)
            html += line(
                atom_text(atom) + "=" + sp.latex(ratio) + r"\cdot" + atom_text(found)
            )
    if len(a.canonical) == 3:
        for i, atom in enumerate(a.canonical):
            others = [c for j, c in enumerate(a.canonical) if i != j]
            ratio = sp.cancel(atom.argument / (others[0].argument * others[1].argument))
            if ratio.is_Rational and ratio > 0:
                shift = log_ratio(atom.base, ratio)
                html += "<p>Положительность отдельных аргументов на ОДЗ позволяет раскрыть логарифм произведения:</p>"
                html += line(
                    atom_text(atom)
                    + "="
                    + atom_text(others[0])
                    + "+"
                    + atom_text(others[1])
                    + "+("
                    + sp.latex(shift)
                    + ")"
                )
                break
    return html


def polynomial_prefix(branch):
    html = ""
    html += "<p>Рассмотрим нулевой многочленный множитель, сохраняя ОДЗ обоих логарифмов:</p>"
    return html


def level_prefix(branch):
    html = ""
    atom, level, target = branch.source
    html += "<p>Приравняем логарифмический множитель к нулю и применим определение логарифма:</p>"
    html += line(atom_text(atom) + "=" + sp.latex(level))
    html += line(
        sp.latex(atom.argument)
        + "="
        + sp.latex(atom.base)
        + "^{"
        + sp.latex(level)
        + "}="
        + sp.latex(target)
    )
    return html


def equal_arguments_prefix(branch):
    html = ""
    left, right = branch.source
    html += "<p>При одинаковом основании на ОДЗ приравняем аргументы:</p>"
    html += line(atom_text(left) + "=" + atom_text(right))
    html += line(sp.latex(left.argument) + "=" + sp.latex(right.argument))
    return html


def reciprocal_prefix(branch):
    html = ""
    left, right = branch.source
    html += "<p>При этих условиях перевернём логарифм по формуле перехода к новому основанию:</p>"
    html += line(
        "\\frac{1}{" + atom_text(right) + "}=" + logarithm(left.base, right.base)
    )
    html += line(atom_text(left) + "=" + logarithm(left.base, right.base))
    html += line(sp.latex(left.argument) + "=" + sp.latex(right.base))
    return html


def variable_prefix(branch):
    html = ""
    left, right = branch.source
    html += (
        "<p>Рассмотрим "
        + (
            "общий аргумент, равный единице"
            if branch.kind == "argument-one"
            else "равенство оснований"
        )
        + ":</p>"
    )
    html += line(
        sp.latex(left.argument) + "=1"
        if branch.kind == "argument-one"
        else sp.latex(left.base) + "=" + sp.latex(right.base)
    )
    return html


BRANCH_PREFIXES = {
    "polynomial": polynomial_prefix,
    "level": level_prefix,
    "equal-arguments": equal_arguments_prefix,
    "reciprocal": reciprocal_prefix,
    "argument-one": variable_prefix,
    "equal-bases": variable_prefix,
}


def branches(a):
    html = ""
    for branch in a.branches:
        html += BRANCH_PREFIXES[branch.kind](branch)
        html += line(sp.latex(branch.equation) + "=0")
        if sp.Poly(branch.equation, X).degree() > 1:
            html += line(sp.latex(sp.factor(branch.equation, extension=True)) + "=0")
        html += roots_line(branch.candidates)
        for root in branch.candidates:
            valid = allowed(root, a.constraints)
            if not valid:
                for p, relation in a.constraints:
                    value = sp.simplify(p.subs(X, root))
                    order = compare(value, sp.Integer(0))
                    if (relation == "positive" and order <= 0) or (
                        relation == "nonzero" and order == 0
                    ):
                        html += line(
                            r"\left.("
                            + sp.latex(p)
                            + r")\right|_{x="
                            + n(root)
                            + "}="
                            + n(value)
                            + r"\quad\text{не удовлетворяет ОДЗ}"
                        )
                        break
            html += (
                "<p>Кандидат "
                + inline("x=" + n(root))
                + (
                    " удовлетворяет всем условиям ОДЗ."
                    if valid
                    else " не входит в ОДЗ и отбрасывается."
                )
                + "</p>"
            )
    return html


def first(a):
    html = domain(a)
    if a.generic:
        html += "<p>Уравнение имеет вид:</p>"
        html += line(r"\log_b A\log_b B=\log_b\frac{AB}{b}")
        html += line(r"\log_b A\log_b B-\log_b A-\log_b B+1=0")
        html += line(r"(\log_b A-1)(\log_b B-1)=0")
    if a.method == "same-argument":
        html += "<p>На ОДЗ равенство логарифмов одного аргумента равносильно совокупности: аргумент равен единице или основания равны:</p>"
        html += line(r"\log_p q=\log_r q\iff(q=1\ \text{или}\ p=r)")
    elif a.method not in ("reciprocal",):
        html += conversion(a)
        html += "<p>Преобразуем уравнение и разложим на множители:</p>"
        html += line(display(a.converted, a) + "=0")
        if a.factored != a.converted:
            html += line(display(a.factored, a) + "=0")
        for factor in a.positive:
            symbol = next(s for s in factor.free_symbols if s != X)
            p = sp.Poly(factor, symbol)
            centre = -p.nth(1) / (2 * p.nth(2))
            remainder = sp.simplify(p.nth(0) - p.nth(1) ** 2 / (4 * p.nth(2)))
            square = p.nth(2) * (symbol - centre) ** 2 + remainder
            html += line(display(factor, a) + "=" + display(square, a) + ">0")
            html += "<p>Этот множитель не обращается в нуль при действительных значениях логарифма.</p>"
    return html + branches(a)


def render(a):
    from .exam_log_selection import selection as exact_selection

    rendered = {r: n(r) for r in a.selection.roots}
    explanation = (
        "Сравним логарифмы по монотонности, а радикалы — по квадратам неотрицательных величин:"
        if r"\log_" in a.selection.interval
        else "Радикалы сравним по квадратам неотрицательных величин:"
    )
    second = exact_selection(a.selection, rendered, explanation=explanation)
    if a.method == "equality-note":
        second += "<p><b>Примечание:</b> при допустимом основании справедлива равносильность:</p>"
        second += line(r"\log_b u=\log_b v\iff\begin{cases}u=v\\v>0\end{cases}")
        second += "<p>После равенства аргументов достаточно проверить положительность одного из них. Оставляют более простое условие.</p>"
    html = (
        '<ol data-layout="source-subparts" type="a"><li data-list-marker="а)">'
        + first(a)
        + '</li><li data-list-marker="б)">'
        + second
        + "</li></ol>"
    )
    all_roots, chosen = (
        root_set(a.selection.roots, rendered),
        root_set(a.selection.selected, rendered),
    )
    return (
        "а) " + all_roots + "; б) " + chosen,
        "<p>а) " + inline(all_roots) + "; б) " + inline(chosen) + ".</p>",
        html,
    )
