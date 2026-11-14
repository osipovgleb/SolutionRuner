"""Keep the parent's original-domain product cancellation and quadratic comparison."""

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline
from .exponential_inequality_preimage_proof import alternatives
from .rational_inequality import FLIPPED, normalize
from .rational_inequality_methods import fraction
from .rational_inequality_proof import RELATION


def logarithm(base, text):
    return r"\log_{" + sp.latex(base) + r"}\left(" + text + r"\right)"


def render(a):
    A, B, C = a.arguments
    n, d = sp.fraction(B)
    factor = sp.cancel(A / d)
    product = sp.Mul(factor, n, evaluate=False)
    right = fraction(C, a.base**a.constant_offset)
    html = "<p>Запишем правую часть одним логарифмом:</p>"
    html += line(
        logarithm(a.base, a.argument_texts[0])
        + "+"
        + logarithm(a.base, a.argument_texts[1])
        + RELATION[a.operator]
        + logarithm(a.base, right)
    )
    html += "<p>Каждое решение исходного неравенства удовлетворяет условиям положительности всех трёх аргументов:</p>"
    html += line(
        r"\begin{cases}"
        + r"\\".join(text + ">0" for text in a.argument_texts)
        + r"\end{cases}"
    )
    html += line(alternatives("x", a.domain))
    html += (
        "<p>На этой области объединим сумму логарифмов и сократим общий множитель, сохраняя исходные ограничения. Основание "
        + ("больше" if a.base > 1 else "меньше")
        + " единицы, поэтому при сравнении аргументов знак "
        + ("сохраняется" if a.base > 1 else "меняется")
        + ":</p>"
    )
    html += line(
        fraction(sp.Mul(factor, d, n, evaluate=False), d) + "=" + sp.latex(product)
    )
    operator = a.operator if a.base > 1 else FLIPPED[a.operator]
    html += line(
        r"\begin{cases}"
        + sp.latex(product)
        + RELATION[operator]
        + right
        + r"\\"
        + alternatives("x", a.domain)
        + r"\end{cases}"
    )
    difference = sp.expand(sp.cancel(A * B) - a.base ** (-a.constant_offset) * C)
    normalized, op = normalize(difference, operator)
    scale = sp.cancel(normalized / difference)
    html += (
        "<p>Перенесём всё влево. Затем умножим обе части на "
        + inline(sp.latex(scale))
        + (", меняя знак неравенства" if scale < 0 else ", сохраняя знак неравенства")
        + ", разложим трёхчлен на множители и пересечём решение с исходной областью определения:</p>"
    )
    html += line(sp.latex(difference) + RELATION[operator] + "0")
    html += line(sp.latex(normalized) + RELATION[op] + "0")
    html += line(sp.latex(sp.factor(normalized)) + RELATION[op] + "0")
    return html + line(alternatives("x", a.solution))
