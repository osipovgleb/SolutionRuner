"""Keep the parent's square-root identity and both closed exponential sign cases."""

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline
from .exam_trigonometric_exponential_absolute import E


def equation(data, sign=None):
    from .exam_trigonometric_proof import formula

    variable = formula(data.variable)
    exponent = (
        r"\left|" + variable + r"\right|"
        if sign is None
        else formula(sign * data.variable)
    )
    base = sp.latex(data.base)
    a, b, c = data.coefficients
    left = sp.latex(a) + r"\cdot " + base + "^{" + exponent + "}"
    left += "+" if b > 0 else "-"
    left += sp.latex(abs(b)) + r"\cdot " if abs(b) != 1 else ""
    return left + base + "^{" + variable + "}=" + sp.latex(-c)


def case_proof(data, row):
    from .exam_trigonometric import table
    from .exam_trigonometric_proof import formula, series_lines
    from .exam_trigonometric_selection import periodic

    variable = formula(data.variable)
    exponential = sp.latex(data.base) + "^{" + variable + "}"
    relation = r"\ge0" if row.sign == 1 else r"\le0"
    html = "<p>Если " + inline(variable + relation) + ", то:</p>"
    html += line(equation(data, row.sign))
    if row.sign == -1:
        html += "<p>Умножим равенство на положительную показательную функцию и перенесём слагаемые:</p>"
        html += line(exponential + ">0")
    html += line(sp.latex(row.polynomial, symbol_names={E: exponential}) + "=0")
    for power, level in zip(row.powers, row.levels, strict=True):
        html += line(exponential + "=" + sp.latex(power))
        if level is None:
            html += (
                "<p>Это значение невозможно: показательная функция положительна.</p>"
            )
            continue
        html += line(variable + "=" + sp.latex(level))
        if not -1 <= level <= 1:
            html += "<p>Значение не входит в отрезок от −1 до 1.</p>"
        elif row.sign * level < 0:
            html += "<p>Значение не удовлетворяет условию рассматриваемого случая.</p>"
    if row.accepted:
        series = periodic(
            tuple(q for v in row.accepted for q in table(data.variable, v))
        )
        for text in series_lines(series):
            html += line(text + r",\quad k\in\mathbb Z")
    else:
        html += "<p>В этом случае корней нет.</p>"
    return html


def proof(a):
    from .exam_trigonometric_proof import formula, series_lines

    data = a.exponential_absolute
    variable = formula(data.variable)
    html = line(
        r"\sqrt{"
        + formula(data.radicand)
        + "}="
        + r"\sqrt{"
        + formula(data.variable**2)
        + "}="
        + r"\left|"
        + variable
        + r"\right|"
    )
    html += "<p>Подкоренное выражение неотрицательно при всех x. Получаем:</p>"
    html += line(equation(data))
    html += "<p>Разберём два случая.</p>"
    for row in data.cases:
        html += case_proof(data, row)
    html += "<p>Объединим решения обоих случаев. Совпадающие корни на границе учитываем один раз:</p>"
    for text in series_lines(a.series):
        html += line(text + r",\quad k\in\mathbb Z")
    return (
        "<p>Используя основное тригонометрическое тождество и извлекая квадратный корень, получаем:</p>",
        html,
    )
