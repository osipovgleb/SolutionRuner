"""Keep Vieta's sum and product before the factored inequality and sign intervals."""

import sympy as sp

from ..probability.common import line
from .rational_inequality_methods import latex, prepare
from .rational_inequality_parser import polynomial


def vieta(a, image):
    from .rational_inequality_proof import RELATION, interval_proof

    _, steps = prepare(a, "vieta_quadratic")
    p = polynomial(a.left.value)
    first, second = a.zeros if len(a.zeros) == 2 else (a.zeros[0], a.zeros[0])
    total, product = sp.simplify(-p.nth(1)), sp.simplify(p.nth(0))
    html = "<p>По теореме Виета найдём сумму и произведение корней соответствующего квадратного уравнения:</p>"
    html += line(a.formula)
    html += line(r"x_1+x_2=" + latex(total))
    html += line(r"x_1x_2=" + latex(product))
    html += "<p>Этим условиям удовлетворяют следующие действительные числа:</p>"
    html += line("x_1=" + latex(first) + r",\quad x_2=" + latex(second))
    html += "<p>Разложим трёхчлен на множители и применим метод интервалов:</p>"
    html += line(steps[0].text + RELATION[a.operator] + "0")
    return html + interval_proof(a, image)
