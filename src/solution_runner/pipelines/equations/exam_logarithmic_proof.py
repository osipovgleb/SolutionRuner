"""Preserve common-base reduction, logarithm substitution and exact selection."""

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline
from .exam_exponential import T, X
from .exam_exponential_proof import n, root_set
from .exam_radical import candidates
from .exam_rational_proof import roots_line
from .exam_scalar import compare


def logarithm(base, argument):
    return r"\log_{" + sp.latex(base) + "}(" + sp.latex(argument) + ")"


def atom_text(a):
    arg = r"\sqrt{" + sp.latex(a.argument) + "}" if a.root else sp.latex(a.argument)
    return r"\log_{" + sp.latex(a.base) + "}(" + arg + ")"


def domain(a):
    html = "<p>Логарифмы определены, когда основания положительны и отличны от единицы, а аргументы строго положительны. Для исходных аргументов получаем:</p>"
    for atom in a.atoms:
        html += line(sp.latex(atom.argument) + ">0")
    if all(
        sp.Poly(atom.argument, X).nth(0) > 0
        and all(
            c >= 0 and degree[0] % 2 == 0
            for degree, c in sp.Poly(atom.argument, X).terms()
        )
        for atom in a.atoms
    ):
        html += "<p>Все подкоренные выражения и аргументы положительны при любом действительном x, поэтому уравнение определено на всей числовой прямой.</p>"
    return html


def polynomial_steps(a):
    html = line(sp.latex(a.equation) + "=0") + line(
        sp.latex(sp.factor(a.equation)) + "=0"
    )
    _, factors = sp.factor_list(a.equation, X)
    if len(factors) > 1:
        for factor, _ in factors:
            html += line(sp.latex(factor) + "=0") + roots_line(candidates(factor))
    html += roots_line(a.candidates)
    for root in a.candidates:
        checks = [sp.simplify(atom.argument.subs(X, root)) for atom in a.atoms]
        html += line(
            "x="
            + n(root)
            + r":\quad "
            + r",\quad ".join(
                n(v) + (">0" if compare(v, sp.Integer(0)) > 0 else r"\le0")
                for v in checks
            )
        )
        html += (
            "<p>Кандидат "
            + ("удовлетворяет" if root in a.selection.roots else "не удовлетворяет")
            + " всем строгим ограничениям ОДЗ.</p>"
        )
    return html


def simple(a):
    atom = a.atoms[0]
    level, target = a.effective
    html = domain(a) + "<p>Из уравнения получаем по определению логарифма:</p>"
    html += line(logarithm(a.base, atom.argument) + "=" + n(level))
    html += line(
        sp.latex(atom.argument)
        + "="
        + sp.latex(a.base)
        + "^{"
        + sp.latex(level)
        + "}="
        + n(target)
    )
    return html + polynomial_steps(a)


def common_base(a):
    html = (
        domain(a)
        + "<p>Запишем исходное уравнение, приведя логарифмы к одному основанию:</p>"
    )
    left, right = a.effective[:2]
    if a.method == "base-square":
        atom = next(atom for atom in a.atoms if atom.base == a.base**2)
        html += line(
            atom_text(atom)
            + r"=\frac12"
            + logarithm(a.base, X**4)
            + "="
            + logarithm(a.base, X**2)
        )
        html += "<p>Здесь x не равен нулю, поэтому x² строго положителен; знак x не ограничивается.</p>"
    else:
        atom = next(atom for atom in a.atoms if atom.root)
        shift, original = a.effective[2:]
        html += line(atom_text(atom) + "=" + logarithm(a.base, original))
        html += line(n(shift) + "=" + logarithm(a.base, a.base**shift))
        html += line(
            logarithm(a.base, left)
            + "="
            + logarithm(a.base, original)
            + "-("
            + logarithm(a.base, a.base**shift)
            + ")"
        )
    html += line(logarithm(a.base, left) + "=" + logarithm(a.base, right))
    html += "<p>При выполнении ОДЗ логарифмическая функция взаимно однозначна, поэтому равенство логарифмов равносильно равенству аргументов:</p>"
    html += line(sp.latex(left) + "=" + sp.latex(right))
    return html + polynomial_steps(a)


def quadratic(a):
    html = (
        domain(a)
        + "<p>Положительный коэффициент и нечётная степень в одном из исходных аргументов требуют x &gt; 0. При этом все остальные мономиальные аргументы также положительны.</p>"
    )
    html += line("x>0")
    for atom, replacement in zip(a.atoms, a.replacements):
        if atom.argument == X:
            continue
        degree = sp.Poly(atom.argument, X).degree()
        coefficient = sp.Poly(atom.argument, X).LC()
        variable = (str(degree) if degree != 1 else "") + logarithm(a.base, X)
        rhs = (
            logarithm(a.base, coefficient) + "+" if coefficient != 1 else ""
        ) + variable
        html += line(atom_text(atom) + "=" + rhs)
        if coefficient != 1:
            html += line(
                atom_text(atom) + "=" + n(replacement.subs(T, 0)) + "+" + variable
            )
    html += "<p>Положим:</p>" + line("t=" + logarithm(a.base, X))
    converted = a.expression.xreplace(
        {
            atom.symbol: sp.UnevaluatedExpr(form)
            for atom, form in zip(a.atoms, a.replacements)
        }
    )
    html += line(sp.latex(converted) + "=0")
    html += line(sp.latex(a.equation) + "=0")
    A, B, C = sp.Poly(a.equation, T).all_coeffs()
    html += line(
        "D=("
        + n(B)
        + r")^2-4\cdot("
        + n(A)
        + r")\cdot("
        + n(C)
        + ")="
        + n(B * B - 4 * A * C)
    )
    if not a.back:
        html += "<p>Действительных значений t нет, поэтому исходное уравнение не имеет корней.</p>"
    for level, root in a.back:
        html += "<p>Вернёмся к исходной переменной:</p>" + line("t=" + sp.latex(level))
        html += line(logarithm(a.base, X) + "=" + sp.latex(level))
        html += line(
            "x=" + sp.latex(a.base) + "^{" + sp.latex(level) + "}=" + sp.latex(root)
        )
    return html


def render(a):
    selection = a.selection
    rendered = {r: n(r) for r in selection.roots}
    first = (
        quadratic(a)
        if a.method == "quadratic"
        else simple(a)
        if a.method == "simple"
        else common_base(a)
    )
    from .exam_log_selection import selection as exact_selection

    if r"\log_" in selection.interval:
        second = exact_selection(selection, rendered)
    else:
        second = exact_selection(
            selection,
            rendered,
            explanation="Радикалы сравним, возводя неотрицательные величины в квадрат:",
        )
    html = (
        '<ol data-layout="source-subparts" type="a"><li data-list-marker="а)">'
        + first
        + '</li><li data-list-marker="б)">'
        + second
        + "</li></ol>"
    )
    all_roots, chosen = (
        root_set(selection.roots, rendered),
        root_set(selection.selected, rendered),
    )
    return (
        "а) " + all_roots + "; б) " + chosen,
        "<p>а) " + inline(all_roots) + "; б) " + inline(chosen) + ".</p>",
        html,
    )
