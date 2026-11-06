"""Preserve substitution, factorization and rational inverse branches in source order."""

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline
from .exponential_inequality_common_base import vector, weight
from .exponential_inequality_proof import power
from .exponential_inequality_quadratic_proof import expression, membership
from .exponential_inequality_rational_exponents import analyze as exponential
from .logarithmic_inequality_substitution import LogarithmicSubstitution
from .logarithmic_inequality_substitution import analyze as logarithmic
from .rational_inequality import FLIPPED, set_latex
from .rational_inequality import analyze as rational
from .rational_inequality_factor_methods import positive_quadratics
from .rational_inequality_parser import X
from .rational_inequality_proof import RELATION, interval_signs_text, normalized


def model(formula):
    return logarithmic(formula) if r"\log_" in formula else exponential(formula)


def domain(a):
    html = "<p>Сохраним область определения исходного неравенства:</p>"
    if isinstance(a, LogarithmicSubstitution):
        html += line(sp.latex(a.base) + r">0,\quad " + sp.latex(a.base) + r"\ne 1")
        html += line(
            r",\quad ".join(sp.latex(atom.argument) + ">0" for atom in a.atoms)
        )
    if a.poles:
        html += line(r",\quad ".join("x\\ne " + sp.latex(p) for p in a.poles))
    return html + line(r"x\in " + set_latex(a.domain))


def quadratic(stage, *, positive):
    html = line(expression(stage.original, "y") + RELATION[stage.operator] + "0")
    if stage.original != stage.expression or stage.operator != stage.sign_operator:
        html += "<p>Приведём квадратное неравенство к стандартному виду, учитывая знак вынесенного множителя:</p>"
        html += line(
            expression(stage.expression, "y") + RELATION[stage.sign_operator] + "0"
        )
    html += line(
        expression(sp.factor(stage.expression), "y")
        + RELATION[stage.sign_operator]
        + "0"
    )
    values = (
        stage.solution.intersect(sp.Interval.open(0, sp.oo))
        if positive
        else stage.solution
    )
    if positive:
        html += "<p>Учитываем положительность замены:</p>"
    return html + line(membership("y", values))


def exponential_preparation(a):
    actual = power(a.base, a.exponent)
    html = (
        "<p>Сделаем замену "
        + inline("y=" + actual + ">0")
        + ". По свойству степеней перепишем каждое слагаемое:</p>"
    )
    for _, base, exponent in a.powers:
        effective = sp.cancel(weight(base, vector(a.base)) * exponent)
        degree = sp.cancel(sp.diff(effective, X) / sp.diff(a.exponent, X))
        offset = sp.cancel(effective - degree * a.exponent)
        y = sp.Symbol("y", positive=True)
        html += line(power(base, exponent) + "=" + sp.latex(a.base**offset * y**degree))
    if a.multiply_degree:
        html += "<p>Умножаем неравенство на положительную степень замены, сохраняя знак:</p>"
        html += line("y^{" + str(a.multiply_degree) + "}>0")
    return html + quadratic(a.stage, positive=True)


def logarithmic_preparation(a):
    actual = (
        r"\log_{" + sp.latex(a.base) + r"}\left(" + sp.latex(a.argument) + r"\right)"
    )
    other = a.atoms[1]
    html = (
        "<p>Сделаем замену "
        + inline("y=" + actual)
        + ". По свойству логарифма частного получаем:</p>"
    )
    html += line(
        r"\log_{"
        + sp.latex(a.base)
        + r"}\left("
        + sp.latex(other.argument)
        + r"\right)=y-"
        + str(a.shift)
    )
    return html + quadratic(a.stage, positive=False)


def inverse_branch(a, branch):
    html = (
        "<p>Сделаем обратную замену для "
        + inline(membership("y", branch.values))
        + ":</p>"
    )
    log = isinstance(a, LogarithmicSubstitution)
    grows = not log or branch.domain.is_subset(a.increasing_domain) is True
    if log:
        relation = ">1" if grows else "<1"
        html += (
            "<p>На рассматриваемой части ОДЗ "
            + inline(sp.latex(a.base) + relation)
            + ", поэтому логарифм "
            + ("возрастает" if grows else "убывает")
            + ":</p>"
        )
        html += line(r"x\in " + set_latex(branch.domain))
    for c in branch.conditions:
        op = "=" if c.operator == "=" else RELATION[c.operator]
        if log:
            back_op = c.operator if grows or c.operator == "=" else FLIPPED[c.operator]
            back_relation = "=" if back_op == "=" else RELATION[back_op]
            html += line(
                sp.latex(a.argument) + back_relation + " " + sp.latex(a.base**c.bound)
            )
            stage = rational(c.stage.formula)
        else:
            html += line(power(a.base, a.exponent) + op + sp.latex(c.bound))
            stage = c.stage
        html += line(stage.formula)
        html += normalized(stage)
        for factor, completed in positive_quadratics(stage):
            html += "<p>Квадратный множитель положителен при всех действительных x:</p>"
            html += line(sp.latex(factor) + "=" + sp.latex(completed) + ">0")
        html += "<p>По методу интервалов:</p>" + line(interval_signs_text(stage))
    if len(branch.conditions) > 1:
        html += "<p>Ограничения внутри этой ветви выполняются одновременно; пересекаем их решения с исходной ОДЗ:</p>"
    else:
        html += "<p>С учётом исходной ОДЗ получаем:</p>"
    return html + line(r"x\in " + set_latex(branch.solution))


def render(a, image=""):
    html = line(a.formula) + domain(a)
    html += (
        logarithmic_preparation(a)
        if isinstance(a, LogarithmicSubstitution)
        else exponential_preparation(a)
    )
    html += "".join(inverse_branch(a, branch) for branch in a.branches)
    html += image
    if len(a.branches) == 1:
        return html
    html += "<p>Объединяем полученные ветви с учётом исходной области определения:</p>"
    return html + line(r"x\in " + a.answer)
